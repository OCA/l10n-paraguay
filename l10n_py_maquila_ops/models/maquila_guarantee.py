# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MaquilaGuarantee(models.Model):
    _name = "l10n_py.maquila.guarantee"
    _description = "Maquila Customs Guarantee"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    program_id = fields.Many2one(
        "l10n_py.maquila.program",
        required=True,
        tracking=True,
    )
    guarantee_type = fields.Selection(
        [
            ("bank", "Bank Guarantee"),
            ("insurance", "Insurance Bond"),
            ("deposit", "Cash Deposit"),
            ("mortgage", "Mortgage"),
        ],
        required=True,
        tracking=True,
    )
    issuer = fields.Char(
        help="Bank or insurance company",
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.ref("base.USD"),
    )
    amount = fields.Monetary(required=True)
    date_start = fields.Date(required=True)
    date_end = fields.Date(required=True)
    state = fields.Selection(
        [
            ("active", "Active"),
            ("expired", "Expired"),
            ("released", "Released"),
        ],
        default="active",
        required=True,
        tracking=True,
    )
    admission_ids = fields.One2many(
        "l10n_py.maquila.admission",
        "guarantee_id",
        string="Admissions",
    )
    amount_used = fields.Monetary(
        compute="_compute_amounts",
    )
    amount_available = fields.Monetary(
        compute="_compute_amounts",
    )
    company_id = fields.Many2one(
        related="program_id.company_id",
        store=True,
    )

    @api.depends("amount", "admission_ids.state", "admission_ids.amount_cif")
    def _compute_amounts(self):
        for rec in self:
            # Sum CIF amounts of active admissions linked to this guarantee
            active = rec.admission_ids.filtered(
                lambda a: a.state in ("admitted", "in_production")
            )
            rec.amount_used = sum(active.mapped("amount_cif"))
            rec.amount_available = rec.amount - rec.amount_used
