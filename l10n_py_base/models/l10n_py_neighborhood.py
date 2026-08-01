# l10n_py_base/models/l10n_py_neighborhood.py

from odoo import fields, models


class Neighborhood(models.Model):
    """Neighborhood model for Paraguay"""

    _name = "l10n_py.neighborhood"
    _description = "Neighborhood"
    _order = "name"

    name = fields.Char(
        required=True,
        help="Neighborhood name",
    )

    code = fields.Char(
        help="Neighborhood code",
    )

    city_id = fields.Many2one(
        "res.city",
        string="City",
        required=True,
        ondelete="cascade",
        help="City the neighborhood belongs to",
    )

    state_id = fields.Many2one(
        "res.country.state",
        string="Department",
        related="city_id.state_id",
        store=True,
        readonly=True,
        help="Department the neighborhood belongs to",
    )

    country_id = fields.Many2one(
        "res.country",
        string="Country",
        related="city_id.country_id",
        store=True,
        readonly=True,
        help="Country the neighborhood belongs to",
    )

    zipcode = fields.Char(
        string="Zip Code",
        help="Neighborhood zip code",
    )
