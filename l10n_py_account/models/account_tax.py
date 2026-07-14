from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_py_iva_affectation = fields.Selection(
        selection=[
            ("1", "Gravado IVA"),
            ("2", "Exonerado (Art. 100 Ley 6380/2019)"),
            ("3", "Exento"),
            ("4", "Gravado parcial"),
        ],
        string="Afectación IVA (SIFEN)",
        default="1",
        help="Forma de afectación del IVA (iAfecIVA) para el DE SIFEN. "
        "Exportación usa Exonerado (2).",
    )
