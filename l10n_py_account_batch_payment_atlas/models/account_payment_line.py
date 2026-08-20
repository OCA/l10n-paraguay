# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import _, fields, models

from odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client import (
    AtlasApiClient,
)


class AccountPaymentLine(models.Model):
    _inherit = "account.payment.line"

    atlas_nro_registro = fields.Integer(
        string="N.º de Registro Atlas",
        help="Índice de esta línea dentro del lote enviado al Banco "
        "Atlas -- usado para volver a asociar el resultado por-línea "
        "de la respuesta con esta línea de Odoo.",
    )
    atlas_nro_orden = fields.Integer(string="N.º de Orden Atlas")
    atlas_error_codigo = fields.Char(string="Código de Resultado Atlas")
    atlas_error_mensaje = fields.Char(string="Mensaje de Resultado Atlas")

    def action_atlas_reversar_pago(self):
        """Request a reversal from Banco Atlas via
        POST /proveedores/{cuenta}/reversar-pago.

        Open question the bank has not answered yet (spec §4.5): whether
        'nroFactura' in this endpoint means the bank's own nroOrden or
        the Odoo invoice number. This implementation sends atlas_nro_orden
        under that key, matching the only concrete example in the bank's
        own documentation -- revisit if the bank clarifies otherwise.
        """
        for line in self:
            bank_account = line.order_id.company_partner_bank_id
            client = AtlasApiClient.from_bank_account(bank_account)
            result = client.call(
                "POST",
                f"/proveedores/{bank_account.atlas_numero_cuenta}/reversar-pago",
                body={
                    "nroFactura": str(line.atlas_nro_orden),
                    "observacion": _("Reversión solicitada desde Odoo"),
                },
            )
            line.atlas_error_mensaje = _(
                "Reversión solicitada: %(op)s", op=result.get("numeroOperacion")
            )
