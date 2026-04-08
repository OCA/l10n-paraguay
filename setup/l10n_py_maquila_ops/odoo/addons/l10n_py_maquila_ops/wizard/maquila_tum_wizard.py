# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MaquilaTumWizard(models.TransientModel):
    _name = "l10n_py.maquila.tum.wizard"
    _description = "TUM 1% Calculation Wizard"

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
    van_amount = fields.Monetary(
        string="VAN Amount",
        readonly=True,
    )
    export_invoice_amount = fields.Monetary(
        readonly=True,
    )
    tum_base = fields.Monetary(
        string="TUM Base",
        compute="_compute_tum",
    )
    tum_rate = fields.Float(
        string="TUM Rate %",
        default=1.0,
    )
    tum_amount = fields.Monetary(
        string="TUM Amount",
        compute="_compute_tum",
    )
    debit_account_id = fields.Many2one(
        "account.account",
        string="TUM Expense Account",
        help="Account to debit for TUM expense",
    )
    credit_account_id = fields.Many2one(
        "account.account",
        string="TUM Payable Account",
        help="Account to credit for TUM liability",
    )

    @api.depends("van_amount", "export_invoice_amount", "tum_rate")
    def _compute_tum(self):
        for wiz in self:
            wiz.tum_base = max(wiz.van_amount, wiz.export_invoice_amount)
            wiz.tum_amount = wiz.tum_base * wiz.tum_rate / 100

    def action_compute(self):
        """Compute VAN and export invoice amounts for the period."""
        self.ensure_one()
        # Export invoices for the period
        invoices = self.env["account.move"].search(
            [
                ("l10n_py_maquila_program_id", "=", self.program_id.id),
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("invoice_date", ">=", self.period_start),
                ("invoice_date", "<=", self.period_end),
            ]
        )
        self.export_invoice_amount = sum(invoices.mapped("amount_total"))
        # VAN would come from maquila_mrp module if installed
        # For now, keep the manually entered value
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_generate_move(self):
        """Generate the TUM accounting entry."""
        self.ensure_one()
        if not self.tum_amount:
            raise UserError(_("TUM amount is zero. Nothing to generate."))
        journal = self.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", self.env.company.id)],
            limit=1,
        )
        if not journal:
            raise UserError(_("No miscellaneous journal found."))
        if not self.debit_account_id or not self.credit_account_id:
            raise UserError(_("Please select both debit and credit accounts."))
        ref = _(
            "TUM 1%% - %(program)s - %(period_end)s",
            program=self.program_id.code,
            period_end=self.period_end,
        )
        move_vals = {
            "move_type": "entry",
            "date": self.period_end,
            "ref": ref,
            "l10n_py_maquila_program_id": self.program_id.id,
            "journal_id": journal.id,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "name": ref,
                        "debit": self.tum_amount,
                        "credit": 0,
                        "account_id": self.debit_account_id.id,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "name": ref,
                        "debit": 0,
                        "credit": self.tum_amount,
                        "account_id": self.credit_account_id.id,
                    },
                ),
            ],
        }
        move = self.env["account.move"].create(move_vals)
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": move.id,
            "view_mode": "form",
        }
