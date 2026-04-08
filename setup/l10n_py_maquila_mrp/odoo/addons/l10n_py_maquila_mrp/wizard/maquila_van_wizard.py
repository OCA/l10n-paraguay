# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MaquilaVanWizard(models.TransientModel):
    _name = "l10n_py.maquila.van.wizard"
    _description = "VAN (National Added Value) Calculation Wizard"

    program_id = fields.Many2one(
        "l10n_py.maquila.program",
        required=True,
        domain="[('state', '=', 'active')]",
    )
    period_start = fields.Date(required=True)
    period_end = fields.Date(required=True)
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.ref("base.USD"),
    )
    total_cost = fields.Monetary(
        readonly=True,
    )
    national_cost = fields.Monetary(
        string="National Cost (PY)",
        readonly=True,
    )
    mercosul_cost = fields.Monetary(
        readonly=True,
    )
    imported_cost = fields.Monetary(
        readonly=True,
    )
    van_amount = fields.Monetary(
        string="VAN Amount",
        compute="_compute_van",
    )
    van_percentage = fields.Float(
        string="VAN %",
        compute="_compute_van",
    )
    mercosul_content = fields.Float(
        string="Mercosul Content %",
        compute="_compute_van",
    )

    @api.depends("total_cost", "national_cost", "mercosul_cost")
    def _compute_van(self):
        for wiz in self:
            wiz.van_amount = wiz.national_cost
            if wiz.total_cost:
                wiz.van_percentage = (wiz.national_cost / wiz.total_cost) * 100
                wiz.mercosul_content = (
                    (wiz.national_cost + wiz.mercosul_cost) / wiz.total_cost
                ) * 100
            else:
                wiz.van_percentage = 0.0
                wiz.mercosul_content = 0.0

    def action_compute(self):
        """Compute costs from analytic lines for the period."""
        self.ensure_one()
        if not self.program_id.analytic_account_id:
            raise UserError(
                _(
                    "Program %(program)s has no analytic account configured.",
                    program=self.program_id.code,
                )
            )

        analytic = self.program_id.analytic_account_id
        # Get analytic lines for the period
        domain = [
            ("account_id", "=", analytic.id),
            ("date", ">=", self.period_start),
            ("date", "<=", self.period_end),
        ]
        lines = self.env["account.analytic.line"].search(domain)

        # Total cost = sum of all analytic lines (absolute values of amounts)
        self.total_cost = sum(abs(line.amount) for line in lines)

        # Categorize by origin type from BOM lines
        # This is a simplified computation - in production would cross-reference
        # with mrp.production raw material moves and their origin types
        self.national_cost = 0.0
        self.mercosul_cost = 0.0
        self.imported_cost = 0.0

        # Get productions for this program in the period
        productions = self.env["mrp.production"].search(
            [
                ("l10n_py_maquila_program_id", "=", self.program_id.id),
                ("date_planned_start", ">=", self.period_start),
                ("date_planned_start", "<=", self.period_end),
                ("state", "=", "done"),
            ]
        )

        for production in productions:
            for move in production.move_raw_ids.filtered(lambda m: m.state == "done"):
                # Find origin type from BOM line
                bom_line = production.bom_id.bom_line_ids.filtered(
                    lambda bl, p=move.product_id: bl.product_id == p
                )[:1]
                origin = bom_line.l10n_py_origin_type if bom_line else "imported"
                cost = abs(sum(move.stock_valuation_layer_ids.mapped("value")))
                if origin == "national_py":
                    self.national_cost += cost
                elif origin == "national_mercosul":
                    self.mercosul_cost += cost
                else:
                    self.imported_cost += cost

        # If no production data, use total from analytic as a fallback
        if not productions and self.total_cost:
            self.imported_cost = self.total_cost

        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
