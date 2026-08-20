# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


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
