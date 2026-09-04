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
    atlas_error_mensaje = fields.Char(
        string="Mensaje de Resultado Atlas",
        help="Mensaje/motivo crudo devuelto por el banco en el último "
        "intento (envío, consulta de status) -- para auditoría/display. "
        "Separado de atlas_estado, que es el estado de ciclo de vida "
        "usado por el cron de polling para decidir qué sigue pendiente.",
    )
    atlas_estado = fields.Char(
        string="Estado Atlas",
        help="Estado de liquidación/ciclo de vida de esta línea en Banco "
        "Atlas (por ejemplo 'sent', 'confirmed', 'rejected', "
        "'reversed') -- separado de atlas_error_mensaje, que guarda el "
        "mensaje crudo del banco. El cron de polling usa este campo "
        "(no atlas_error_mensaje) para decidir qué líneas siguen "
        "pendientes de confirmación.",
    )
    atlas_reversal_reference = fields.Char(
        string="Referencia de Reversión Atlas",
        help="Número de operación de reversión devuelto por el banco "
        "(campo 'numeroOperacion' de reversar-pago).",
    )

    def action_atlas_reversar_pago(self):
        """Request a reversal from Banco Atlas via POST
        /proveedores-atlas/v1.5.0/proveedores/{cuenta}/reversar-pago.

        'nroFactura' is the vendor's own invoice reference, confirmed by
        the bank (2026-09-02, cross-referencing item 5 with the Home
        Banking layout in item 12): NRO_ORDEN and NRO_FACTURA are
        distinct fields, the latter being the supplier's invoice number,
        never the bank's/Odoo's own order number. Falls back to the
        move's internal sequence name when no vendor reference was
        entered, and to the Atlas order number only when the line has no
        linked bill at all (e.g. manually created payment lines).
        """
        for line in self:
            bank_account = line.order_id.company_partner_bank_id
            client = AtlasApiClient.from_bank_account(bank_account)
            move = line.move_line_id.move_id
            nro_factura = move.ref or move.name or str(line.atlas_nro_orden)
            result = client.call(
                "POST",
                f"/proveedores-atlas/v1.5.0/proveedores/"
                f"{bank_account.atlas_numero_cuenta}/reversar-pago",
                body={
                    "nroFactura": nro_factura,
                    "observacion": _("Reversión solicitada desde Odoo"),
                },
            )
            # atlas_error_mensaje keeps the ORIGINAL dispatch message
            # intact (audit trail of the bank's per-attempt reason) --
            # the reversal moves the lifecycle state instead, and its own
            # confirmation reference goes to a dedicated field.
            line.write(
                {
                    "atlas_estado": "reversed",
                    "atlas_reversal_reference": result.get("numeroOperacion"),
                }
            )
