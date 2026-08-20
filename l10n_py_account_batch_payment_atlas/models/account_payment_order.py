# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

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
