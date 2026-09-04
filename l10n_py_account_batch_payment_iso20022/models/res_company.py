# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_py_sipap_spi_lbtr_threshold = fields.Monetary(
        string="Umbral SPI/LBTR SIPAP",
        currency_field="currency_id",
        help="Monto a partir del cual una transacción SIPAP se clasifica "
        "como LBTR (Liquidación Bruta en Tiempo Real) en lugar de SPI "
        "(Sistema de Pagos Inmediatos). NO se asume ningún valor por "
        "defecto: el valor oficial debe confirmarse con el Banco Central "
        "del Paraguay (BCP) antes de generar archivos en producción. "
        "Mientras este campo esté vacío, la generación del archivo ISO "
        "20022 fallará con un error explícito en lugar de asumir un "
        "umbral no confirmado.",
    )
