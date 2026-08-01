# l10n_py_base/models/res_city.py

from odoo import fields, models


class City(models.Model):
    """Extension of res.city for Paraguay with SET code.

    This object extends res.city to include the SET code
    (SET - Paraguay Tax Authority) required for
    tax documents in Paraguay.
    """

    _inherit = "res.city"

    l10n_py_code = fields.Char(
        string="SET Code",
        size=4,
        help=("City code according to SET - Paraguay Tax Authority"),
    )

    _l10n_py_code_unique = models.Constraint(
        "unique(l10n_py_code, country_id)",
        "The SET code of the city must be unique per country",
    )
