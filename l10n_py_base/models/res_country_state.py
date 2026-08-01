# l10n_py_base/models/res_country_state.py

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class CountryState(models.Model):
    """Extension of res.country.state for Paraguay (Departments).

    This object extends res.country.state to include the SET code
    (SET - Paraguay Tax Authority) required for
    tax documents in Paraguay.
    """

    _inherit = "res.country.state"

    l10n_py_code = fields.Integer(
        string="SET Code",
        help=("Department code according to SET - Paraguay Tax Authority"),
    )

    @api.constrains("l10n_py_code", "country_id")
    def _check_unique_code_per_country(self):
        for rec in self:
            if rec.l10n_py_code:
                existing = self.search(
                    [
                        ("l10n_py_code", "=", rec.l10n_py_code),
                        ("country_id", "=", rec.country_id.id),
                        ("id", "!=", rec.id),
                    ],
                    limit=1,
                )
                if existing:
                    raise ValidationError(
                        self.env._("The SET code is already used in this country")
                    )
