# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from odoo import _, api, fields, models


class MaquilaCnimeReport(models.Model):
    _name = "l10n_py.maquila.cnime.report"
    _description = "CNIME Periodic Report"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "period_start desc"

    program_id = fields.Many2one(
        "l10n_py.maquila.program",
        required=True,
        tracking=True,
    )
    period_start = fields.Date(required=True, tracking=True)
    period_end = fields.Date(required=True, tracking=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("generated", "Generated"),
            ("validated", "Validated"),
            ("submitted", "Submitted"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    import_data = fields.Text(
        compute="_compute_report_data",
        store=True,
    )
    export_data = fields.Text(
        compute="_compute_report_data",
        store=True,
    )
    production_data = fields.Text(
        compute="_compute_report_data",
        store=True,
    )
    waste_data = fields.Text(
        compute="_compute_report_data",
        store=True,
    )
    stock_balance = fields.Text(
        compute="_compute_report_data",
        store=True,
    )
    employment_count = fields.Integer()
    van_total = fields.Monetary(
        string="VAN Total",
        compute="_compute_report_data",
        store=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.ref("base.USD"),
    )
    submission_date = fields.Datetime(tracking=True)
    submission_protocol = fields.Char(tracking=True)
    company_id = fields.Many2one(
        related="program_id.company_id",
        store=True,
    )

    @api.depends("program_id", "period_start", "period_end")
    def _compute_report_data(self):
        for report in self:
            if not (report.program_id and report.period_start and report.period_end):
                report.import_data = False
                report.export_data = False
                report.production_data = False
                report.waste_data = False
                report.stock_balance = False
                report.van_total = 0
                continue

            program = report.program_id

            # Import data - admissions in period
            admissions = self.env["l10n_py.maquila.admission"].search(
                [
                    ("program_id", "=", program.id),
                    ("date_admission", ">=", report.period_start),
                    ("date_admission", "<=", report.period_end),
                ]
            )
            import_lines = []
            for adm in admissions:
                for line in adm.line_ids:
                    import_lines.append(
                        {
                            "dispatch": adm.name,
                            "product": line.product_id.name,
                            "quantity": line.quantity,
                            "fob_value": line.fob_value,
                        }
                    )
            report.import_data = (
                json.dumps(import_lines, indent=2) if import_lines else False
            )

            # Export data - exports in period
            exports = self.env["l10n_py.maquila.export"].search(
                [
                    ("program_id", "=", program.id),
                    ("date_export", ">=", report.period_start),
                    ("date_export", "<=", report.period_end),
                ]
            )
            export_lines = []
            for exp in exports:
                for line in exp.line_ids:
                    export_lines.append(
                        {
                            "dispatch": exp.name,
                            "product": line.product_id.name,
                            "quantity": line.quantity,
                            "fob_value": line.fob_value,
                        }
                    )
            report.export_data = (
                json.dumps(export_lines, indent=2) if export_lines else False
            )

            # Production data
            productions = self.env["mrp.production"].search(
                [
                    ("l10n_py_maquila_program_id", "=", program.id),
                    ("date_planned_start", ">=", report.period_start),
                    ("date_planned_start", "<=", report.period_end),
                    ("state", "=", "done"),
                ]
            )
            prod_lines = []
            for prod in productions:
                prod_lines.append(
                    {
                        "reference": prod.name,
                        "product": prod.product_id.name,
                        "quantity": prod.product_qty,
                    }
                )
            report.production_data = (
                json.dumps(prod_lines, indent=2) if prod_lines else False
            )

            # Waste data
            wastes = self.env["l10n_py.maquila.waste"].search(
                [
                    ("program_id", "=", program.id),
                    ("date", ">=", report.period_start),
                    ("date", "<=", report.period_end),
                ]
            )
            waste_lines = []
            for w in wastes:
                waste_lines.append(
                    {
                        "product": w.product_id.name,
                        "quantity": w.quantity,
                        "type": w.waste_type,
                        "destination": w.destination,
                    }
                )
            report.waste_data = (
                json.dumps(waste_lines, indent=2) if waste_lines else False
            )

            # Stock balance - simplified
            report.stock_balance = False

            # VAN total from analytic
            if program.analytic_account_id:
                analytic_lines = self.env["account.analytic.line"].search(
                    [
                        ("account_id", "=", program.analytic_account_id.id),
                        ("date", ">=", report.period_start),
                        ("date", "<=", report.period_end),
                    ]
                )
                report.van_total = sum(abs(line.amount) for line in analytic_lines)
            else:
                report.van_total = 0

    def action_generate(self):
        """Force recomputation and move to generated state."""
        self.write({"state": "generated"})

    def action_validate(self):
        self.write({"state": "validated"})

    def action_submit(self):
        self.write(
            {
                "state": "submitted",
                "submission_date": fields.Datetime.now(),
            }
        )

    def action_draft(self):
        self.write({"state": "draft"})

    def action_generate_simex_payload(self):
        """Generate SIMEX payload (stub for future integration)."""
        self.ensure_one()
        # SIMEX integration stub - offline payload generation
        payload = {
            "programa": self.program_id.code,
            "periodo_inicio": str(self.period_start),
            "periodo_fin": str(self.period_end),
            "importaciones": json.loads(self.import_data or "[]"),
            "exportaciones": json.loads(self.export_data or "[]"),
            "produccion": json.loads(self.production_data or "[]"),
            "residuos": json.loads(self.waste_data or "[]"),
            "van_total": self.van_total,
            "empleo": self.employment_count,
        }
        # Log payload for debugging
        self.message_post(
            body=_("SIMEX payload generated (offline mode):\n%s")
            % json.dumps(payload, indent=2, default=str),
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("SIMEX Payload Generated"),
                "message": _("SIMEX payload generated successfully (offline mode)."),
                "sticky": False,
                "type": "success",
            },
        }
