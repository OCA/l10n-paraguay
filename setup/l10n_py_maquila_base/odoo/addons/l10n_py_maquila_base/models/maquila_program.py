# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models


class MaquilaProgram(models.Model):
    _name = "l10n_py.maquila.program"
    _description = "Maquila Program"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "code"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(
        string="Biministerial Resolution",
        required=True,
        tracking=True,
        help="Resolucion biministerial (e.g. RES-BIM-2026-001)",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("suspended", "Suspended"),
            ("closed", "Closed"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    maquila_type = fields.Selection(
        [
            ("pura", "Maquila Pura"),
            ("ociosidad", "Capacidad Ociosa"),
            ("abrigo", "Maquila de Abrigo"),
            ("servicio", "Maquila de Servicio"),
        ],
        required=True,
        tracking=True,
    )
    matriz_partner_id = fields.Many2one(
        "res.partner",
        string="Foreign Matrix",
        required=True,
        tracking=True,
        help="Foreign parent company (owner of temporary goods)",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Maquiladora",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )
    agreement_id = fields.Many2one(
        "agreement",
        string="CNIME Contract",
        tracking=True,
        help="OCA Agreement linked to CNIME contract",
    )
    contract_id = fields.Many2one(
        "contract.contract",
        string="Recurring Invoice Contract",
        tracking=True,
        help="OCA Contract for recurring maquila service billing",
    )
    cnime_resolution_date = fields.Date(
        string="CNIME Resolution Date",
        tracking=True,
    )
    cnime_resolution_expiry = fields.Date(
        string="CNIME Resolution Expiry",
        tracking=True,
    )
    internal_sale_pct = fields.Float(
        string="Internal Market %",
        help="Percentage allowed for domestic sale (capacidad ociosa type)",
    )
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        tracking=True,
        help="Analytic account for accounting segregation of this program",
    )
    resolution_attachment = fields.Binary(
        string="Resolution PDF",
        attachment=True,
    )
    resolution_attachment_name = fields.Char()
    product_line_ids = fields.One2many(
        "l10n_py.maquila.program.product",
        "program_id",
        string="Product Lines",
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "The resolution code must be unique per company.",
        ),
    ]

    def action_activate(self):
        self.write({"state": "active"})

    def action_suspend(self):
        self.write({"state": "suspended"})

    def action_close(self):
        self.write({"state": "closed"})

    def action_draft(self):
        self.write({"state": "draft"})

    @api.model
    def _cron_check_expiry(self):
        """Check for programs, contracts, and INTN certificates nearing expiry."""
        today = fields.Date.today()

        # Programs expiring in 90 days
        limit_program = today + relativedelta(days=90)
        expiring_programs = self.search(
            [
                ("state", "=", "active"),
                ("cnime_resolution_expiry", "<=", limit_program),
                ("cnime_resolution_expiry", ">=", today),
            ]
        )
        for program in expiring_programs:
            program.activity_schedule(
                "mail.mail_activity_data_warning",
                date_deadline=program.cnime_resolution_expiry,
                summary=_(
                    "Program %(code)s expires on %(date)s",
                    code=program.code,
                    date=program.cnime_resolution_expiry,
                ),
            )

        # Contracts expiring in 120 days
        limit_contract = today + relativedelta(days=120)
        programs_contract = self.search(
            [
                ("state", "=", "active"),
                ("agreement_id.end_date", "<=", limit_contract),
                ("agreement_id.end_date", ">=", today),
            ]
        )
        for program in programs_contract:
            program.activity_schedule(
                "mail.mail_activity_data_warning",
                date_deadline=program.agreement_id.end_date,
                summary=_(
                    "Contract for program %(code)s expires on %(date)s",
                    code=program.code,
                    date=program.agreement_id.end_date,
                ),
            )

        # INTN certificates expiring in 60 days
        limit_intn = today + relativedelta(days=60)
        expiring_intn = self.env["l10n_py.maquila.program.product"].search(
            [
                ("program_id.state", "=", "active"),
                ("intn_expiry_date", "<=", limit_intn),
                ("intn_expiry_date", ">=", today),
            ]
        )
        for line in expiring_intn:
            line.program_id.activity_schedule(
                "mail.mail_activity_data_warning",
                date_deadline=line.intn_expiry_date,
                summary=_(
                    "INTN certificate for %(product)s expires on %(date)s",
                    product=line.product_id.name,
                    date=line.intn_expiry_date,
                ),
            )


class MaquilaProgramProduct(models.Model):
    _name = "l10n_py.maquila.program.product"
    _description = "Maquila Program Product"

    program_id = fields.Many2one(
        "l10n_py.maquila.program",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        "product.product",
        required=True,
    )
    intn_certificate = fields.Char(
        string="INTN Certificate",
    )
    intn_certificate_date = fields.Date(
        string="INTN Certificate Date",
    )
    intn_expiry_date = fields.Date(
        string="INTN Expiry Date",
        help="INTN certificate validity (typically 2 years)",
    )
