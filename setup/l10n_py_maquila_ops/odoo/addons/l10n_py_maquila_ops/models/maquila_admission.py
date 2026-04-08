# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MaquilaAdmission(models.Model):
    _name = "l10n_py.maquila.admission"
    _description = "Maquila Temporary Admission"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_admission desc"

    name = fields.Char(
        string="Dispatch Number",
        required=True,
        tracking=True,
        help="Dispatch number (e.g. DI-2026-00123)",
    )
    program_id = fields.Many2one(
        "l10n_py.maquila.program",
        required=True,
        tracking=True,
        domain="[('state', '=', 'active')]",
    )
    cnime_certificate = fields.Char(
        string="CNIME Certificate",
        tracking=True,
    )
    date_admission = fields.Date(
        required=True,
        default=fields.Date.today,
        tracking=True,
    )
    date_deadline = fields.Date(
        string="Deadline",
        compute="_compute_date_deadline",
        store=True,
        help="12 months from admission date",
    )
    date_extended = fields.Date(
        string="Extended Deadline",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("admitted", "Admitted"),
            ("in_production", "In Production"),
            ("closed", "Closed"),
            ("expired", "Expired"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    guarantee_id = fields.Many2one(
        "l10n_py.maquila.guarantee",
        string="Customs Guarantee",
        tracking=True,
    )
    supplier_id = fields.Many2one(
        "res.partner",
        string="Supplier",
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.ref("base.USD"),
    )
    amount_cif = fields.Monetary(
        string="CIF Amount",
    )
    line_ids = fields.One2many(
        "l10n_py.maquila.admission.line",
        "admission_id",
        string="Lines",
    )
    picking_ids = fields.One2many(
        "stock.picking",
        "l10n_py_maquila_admission_id",
        string="Pickings",
    )
    company_id = fields.Many2one(
        related="program_id.company_id",
        store=True,
    )

    @api.depends("date_admission")
    def _compute_date_deadline(self):
        for rec in self:
            if rec.date_admission:
                rec.date_deadline = rec.date_admission + relativedelta(months=12)
            else:
                rec.date_deadline = False

    def action_admit(self):
        for rec in self:
            if not rec.cnime_certificate:
                raise UserError(_("CNIME certificate is required for admission."))
            if rec.guarantee_id and rec.guarantee_id.amount_available < rec.amount_cif:
                raise UserError(
                    _(
                        "Insufficient guarantee. Available: %(available)s,"
                        " Required: %(required)s",
                        available=rec.guarantee_id.amount_available,
                        required=rec.amount_cif,
                    )
                )
        self.write({"state": "admitted"})

    def action_in_production(self):
        self.write({"state": "in_production"})

    def action_close(self):
        self.write({"state": "closed"})

    def action_draft(self):
        self.write({"state": "draft"})


class MaquilaAdmissionLine(models.Model):
    _name = "l10n_py.maquila.admission.line"
    _description = "Maquila Admission Line"

    admission_id = fields.Many2one(
        "l10n_py.maquila.admission",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        "product.product",
        required=True,
    )
    lot_id = fields.Many2one(
        "stock.lot",
        string="Lot/Serial",
    )
    quantity = fields.Float(
        required=True,
        digits="Product Unit of Measure",
    )
    uom_id = fields.Many2one(
        "uom.uom",
        string="Unit of Measure",
    )
    ncm_code = fields.Char(
        string="NCM Code",
    )
    currency_id = fields.Many2one(
        related="admission_id.currency_id",
    )
    fob_value = fields.Monetary(
        string="FOB Value",
    )
    qty_consumed = fields.Float(
        compute="_compute_qty_remaining",
        digits="Product Unit of Measure",
    )
    qty_remaining = fields.Float(
        compute="_compute_qty_remaining",
        digits="Product Unit of Measure",
    )

    @api.depends("quantity")
    def _compute_qty_remaining(self):
        # Placeholder: in full implementation would compute from stock moves
        for line in self:
            line.qty_consumed = 0.0
            line.qty_remaining = line.quantity
