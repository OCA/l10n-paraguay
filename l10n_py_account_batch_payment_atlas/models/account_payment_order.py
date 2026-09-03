# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client import (
    AtlasApiClient,
)

# Limit confirmed by Banco Atlas (2026-09-02, item 9 of the SIPAP
# clarification round): Gs. 10.000.000 for SPI (PYG-only), LBTR above
# that value or for any operation in a currency other than PYG. This
# supersedes the Gs. 5.000.000 figure previously assumed from BCP
# Resolución 1/2023 §50.01, which the bank's own confirmation
# overrides for this integration.
L10N_PY_ATLAS_SPI_LIMIT_PYG = 10_000_000


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    l10n_py_atlas_tipo_transferencia = fields.Selection(
        [
            ("SPI", "SPI - Instantáneo"),
            ("LBTR", "LBTR - Alto valor"),
            ("ACH", "ACH - Bajo valor, lote"),
            ("ATLAS", "Atlas - Interna"),
        ],
        string="Tipo de Transferencia Atlas",
        compute="_compute_l10n_py_atlas_tipo_transferencia",
        store=True,
        readonly=False,
        help="Sugerido automáticamente según el límite confirmado por "
        "Banco Atlas (Gs. 10.000.000 por transferencia individual, solo "
        "PYG -- confirmación 2026-09-02 aplica el límite POR TRANSFERENCIA, "
        "no por lote: un lote es elegible para SPI solo si TODAS sus "
        "líneas están, cada una individualmente, dentro del límite -- "
        "override manual permitido. 'ACH' nunca se sugiere "
        "automáticamente: la documentación del Banco Atlas no da un "
        "criterio de cuándo preferirlo sobre SPI. IMPORTANTE: este campo "
        "solo controla esta validación previa (pre-flight) antes de "
        "despachar el lote -- no determina qué riel/trilho el Banco "
        "Atlas usa realmente para la transferencia, porque la "
        "documentación de la API de Pago a Proveedores del banco no "
        "especifica un campo para comunicar esa elección (pendencia "
        "documentada, ver README).",
    )

    @api.depends("payment_line_ids.amount_currency", "payment_line_ids.currency_id")
    def _compute_l10n_py_atlas_tipo_transferencia(self):
        for order in self:
            currencies = order.payment_line_ids.currency_id
            if not currencies:
                order.l10n_py_atlas_tipo_transferencia = False
                continue
            is_pyg = len(currencies) == 1 and currencies.name == "PYG"
            # Banco Atlas confirmed (2026-09-02) the Gs. 10.000.000
            # limit is PER TRANSFER, not per batch total -- check every
            # line individually, never the sum (a batch of many small,
            # individually-legal SPI transfers must not be forced to
            # LBTR just because their sum exceeds the limit).
            all_lines_within_limit = all(
                amount <= L10N_PY_ATLAS_SPI_LIMIT_PYG
                for amount in order.payment_line_ids.mapped("amount_currency")
            )
            if is_pyg and all_lines_within_limit:
                order.l10n_py_atlas_tipo_transferencia = "SPI"
            else:
                order.l10n_py_atlas_tipo_transferencia = "LBTR"

    def _check_l10n_py_atlas_routing(self):
        """Raise instead of silently reclassifying when the chosen route
        is inconsistent with the batch's actual currency/amount -- called
        by the dispatch method (``_l10n_py_dispatch_batch_api_atlas``)
        before calling the bank."""
        for order in self:
            currencies = order.payment_line_ids.currency_id
            if len(currencies) > 1:
                raise UserError(
                    _(
                        "El lote '%(order)s' mezcla monedas (%(currencies)s). "
                        "Las APIs del Banco Atlas no aceptan un lote "
                        "multi-moneda -- divida el lote por moneda.",
                        order=order.display_name,
                        currencies=", ".join(currencies.mapped("name")),
                    )
                )
            is_pyg = len(currencies) == 1 and currencies.name == "PYG"
            # Per-line check (per Banco Atlas's 2026-09-02 confirmation:
            # the limit is per-transfer, not per-batch-total)
            amounts = order.payment_line_ids.mapped("amount_currency")
            over_limit = any(amount > L10N_PY_ATLAS_SPI_LIMIT_PYG for amount in amounts)
            if order.l10n_py_atlas_tipo_transferencia == "SPI" and (
                not is_pyg or over_limit
            ):
                raise UserError(
                    _(
                        "El lote '%(order)s' fue forzado a SPI pero al "
                        "menos una de sus líneas supera, individualmente, "
                        "el límite confirmado por Banco Atlas (Gs. "
                        "%(limit)s por transferencia, solo PYG -- "
                        "confirmación 2026-09-02) o el lote no está en "
                        "PYG. Use LBTR para este lote.",
                        order=order.display_name,
                        limit=f"{L10N_PY_ATLAS_SPI_LIMIT_PYG:,}".replace(",", "."),
                    )
                )

    def _l10n_py_dispatch_batch_api_atlas(self):
        """Dispatch this batch directly to Banco Atlas's Pago a
        Proveedores API (POST
        /proveedores-atlas/v1.5.0/proveedores/{cuenta}/registrar-pago),
        instead of generating a file for manual upload.

        Synchronous: the response already carries a per-line result
        (spec §4.3) -- final settlement confirmation for lines still
        pending after this call is handled by the polling cron
        (``_l10n_py_atlas_cron_poll_pending``), since this API exposes no
        webhook.

        Returns the same ``(False, False)`` "no file produced" tuple
        shape used elsewhere in this framework (see
        ``account_payment_order.generate_payment_file``) -- this is
        an API dispatch, not a file exporter, so there is never a file to
        attach.
        """
        self.ensure_one()
        if any(self.payment_line_ids.mapped("atlas_nro_orden")):
            raise UserError(
                _(
                    "El lote '%(order)s' ya fue despachado al Banco Atlas "
                    "anteriormente (al menos una línea ya tiene un número "
                    "de orden Atlas asignado). Volver a despacharlo "
                    "arriesga un pago duplicado -- verifique el estado "
                    "real en el banco antes de continuar.",
                    order=self.display_name,
                )
            )
        self._check_l10n_py_atlas_routing()
        company_bank_account = self.company_partner_bank_id
        client = AtlasApiClient.from_bank_account(company_bank_account)

        beneficiarios = []
        for index, line in enumerate(self.payment_line_ids, start=1):
            beneficiarios.append(
                {
                    "nombreBeneficiario": line.partner_id.display_name,
                    "formaPago": "C",
                    "monto": line.amount_currency,
                    "nroCuentaCredito": line.partner_bank_id.acc_number,
                    "nroRegistro": index,
                }
            )

        response = client.call(
            "POST",
            f"/proveedores-atlas/v1.5.0/proveedores/"
            f"{company_bank_account.atlas_numero_cuenta}/registrar-pago",
            body={"tipoDestino": "P", "beneficiarioProveedorList": beneficiarios},
        )

        resultados = (
            response.get("transaccion", {})
            .get("infoAdicional", {})
            .get("beneficiarios", [])
        )
        resultados_by_registro = {r.get("nroRegistro"): r for r in resultados}
        for index, line in enumerate(self.payment_line_ids, start=1):
            resultado = resultados_by_registro.get(index, {})
            error = resultado.get("error", {})
            codigo = error.get("codigo")
            estado = "rejected" if codigo not in (None, "0") else "sent"
            line.write(
                {
                    "atlas_nro_registro": index,
                    "atlas_nro_orden": resultado.get("nroOrden"),
                    "atlas_error_codigo": codigo,
                    "atlas_error_mensaje": error.get("mensaje"),
                    "atlas_estado": estado,
                }
            )
        return (False, False)

    @api.model
    def _l10n_py_atlas_cron_poll_pending(self):
        """Scheduled action: poll Pago a Proveedores' consultar-pago for
        every line dispatched to Atlas that has a nroOrden but is not yet
        in a terminal lifecycle state (``atlas_estado``). No webhook
        exists on this API (spec §4.4) -- "not appearing in the response"
        means "still pending", not an error (the bank's own doc:
        consultar-pago only returns already-processed-and-confirmed
        payments).

        Uses ``atlas_estado`` (lifecycle state), not ``atlas_error_mensaje``
        (the bank's raw per-attempt message), to decide what is still
        pending: every line dispatched by
        ``_l10n_py_dispatch_batch_api_atlas`` already has a non-empty
        ``atlas_error_mensaje`` right after dispatch (e.g. "Aprobado"),
        so a domain keyed on that field would never match any real
        dispatched line.
        """
        pending_lines = self.env["account.payment.line"].search(
            [
                ("atlas_nro_orden", "!=", False),
                ("atlas_estado", "not in", ["confirmed", "rejected", "reversed"]),
            ]
        )
        by_bank_account = {}
        for line in pending_lines:
            bank_account = line.order_id.company_partner_bank_id
            by_bank_account.setdefault(bank_account, []).append(line)

        for bank_account, lines in by_bank_account.items():
            client = AtlasApiClient.from_bank_account(bank_account)
            response = client.call(
                "GET",
                f"/proveedores-atlas/v1.5.0/proveedores/"
                f"{bank_account.atlas_numero_cuenta}/consultar-pago",
            )
            by_nro_orden = {item.get("nroOrden"): item for item in response}
            for line in lines:
                result = by_nro_orden.get(line.atlas_nro_orden)
                if result:
                    line.write(
                        {
                            "atlas_estado": "confirmed",
                            "atlas_error_mensaje": result.get("estado"),
                        }
                    )
