# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client import (
    AtlasApiClient,
)

# Official SPI limit per BCP Resolución 1/2023 §50.01: "Límite de pago:
# Las transferencias enviadas por el SPI tendrán un límite de
# Gs. 5.000.000 (guaraníes cinco millones)." PYG-only, no queueing.
L10N_PY_ATLAS_SPI_LIMIT_PYG = 5_000_000


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
        help="Sugerido automáticamente según el límite oficial del BCP "
        "para SPI (Gs. 5.000.000, solo PYG) -- override manual permitido. "
        "'ACH' nunca se sugiere automáticamente: la documentación del "
        "Banco Atlas no da un criterio de cuándo preferirlo sobre SPI.",
    )

    @api.depends("payment_line_ids.amount_currency", "payment_line_ids.currency_id")
    def _compute_l10n_py_atlas_tipo_transferencia(self):
        for order in self:
            currencies = order.payment_line_ids.currency_id
            if not currencies:
                order.l10n_py_atlas_tipo_transferencia = False
                continue
            total = sum(order.payment_line_ids.mapped("amount_currency"))
            is_pyg = len(currencies) == 1 and currencies.name == "PYG"
            if is_pyg and total <= L10N_PY_ATLAS_SPI_LIMIT_PYG:
                order.l10n_py_atlas_tipo_transferencia = "SPI"
            else:
                order.l10n_py_atlas_tipo_transferencia = "LBTR"

    def _check_l10n_py_atlas_routing(self):
        """Raise instead of silently reclassifying when the chosen route
        is inconsistent with the batch's actual currency/amount -- called
        by Task 11's dispatch method before calling the bank."""
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
            total = sum(order.payment_line_ids.mapped("amount_currency"))
            is_pyg = len(currencies) == 1 and currencies.name == "PYG"
            if order.l10n_py_atlas_tipo_transferencia == "SPI" and (
                not is_pyg or total > L10N_PY_ATLAS_SPI_LIMIT_PYG
            ):
                raise UserError(
                    _(
                        "El lote '%(order)s' fue forzado a SPI pero supera "
                        "el límite oficial del BCP (Gs. %(limit)s, solo "
                        "PYG -- Resolución 1/2023 §50.01) o no está en "
                        "PYG. Use LBTR para este lote.",
                        order=order.display_name,
                        limit=f"{L10N_PY_ATLAS_SPI_LIMIT_PYG:,}".replace(",", "."),
                    )
                )

    def _l10n_py_dispatch_batch_api_atlas(self):
        """Dispatch this batch directly to Banco Atlas's Pago a
        Proveedores API (POST /proveedores/{cuenta}/registrar-pago),
        instead of generating a file for manual upload.

        Synchronous: the response already carries a per-line result
        (spec §4.3) -- final settlement confirmation for lines still
        pending after this call is handled by the polling cron (Task 12),
        since this API exposes no webhook.
        """
        self.ensure_one()
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
            f"/proveedores/{company_bank_account.atlas_numero_cuenta}"
            "/registrar-pago",
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
            line.write(
                {
                    "atlas_nro_registro": index,
                    "atlas_nro_orden": resultado.get("nroOrden"),
                    "atlas_error_codigo": error.get("codigo"),
                    "atlas_error_mensaje": error.get("mensaje"),
                }
            )
        return True
