# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestMaquilaOps(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.py = cls.env.ref("base.py")
        cls.matriz = cls.env["res.partner"].create({"name": "Ops Matriz"})
        cls.program = cls.env["l10n_py.maquila.program"].create(
            {
                "name": "Ops Program",
                "code": "RES-BIM-OPS-001",
                "maquila_type": "pura",
                "matriz_partner_id": cls.matriz.id,
                "company_id": cls.company.id,
                "state": "active",
                "internal_sale_pct": 10.0,
            }
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Ops Product", "is_storable": True, "list_price": 100.0}
        )

    # ---------- admission ----------
    def _admission(self, cif=40000, guarantee=None, cert="CN-1"):
        return self.env["l10n_py.maquila.admission"].create(
            {
                "name": f"DI-OPS-{cert}",
                "program_id": self.program.id,
                "guarantee_id": guarantee and guarantee.id,
                "cnime_certificate": cert,
                "amount_cif": cif,
                "line_ids": [(0, 0, {"product_id": self.product.id, "quantity": 100})],
            }
        )

    def test_admission_deadline(self):
        adm = self._admission()
        expected = adm.date_admission + relativedelta(months=12)
        self.assertEqual(adm.date_deadline, expected)

    def test_admission_qty_remaining_no_outflow(self):
        adm = self._admission()
        line = adm.line_ids
        # No stock has left the admission location yet.
        self.assertEqual(line.qty_consumed, 0.0)
        self.assertEqual(line.qty_remaining, line.quantity)

    def test_admission_requires_cnime(self):
        adm = self._admission(cert="")
        adm.cnime_certificate = False
        with self.assertRaises(UserError):
            adm.action_admit()

    def test_admission_extend_once(self):
        adm = self._admission()
        adm.action_admit()
        adm.action_extend()
        self.assertEqual(
            adm.date_extended, adm.date_deadline + relativedelta(months=12)
        )
        with self.assertRaises(UserError):
            adm.action_extend()

    # ---------- guarantee ----------
    def test_guarantee_amounts(self):
        guar = self.env["l10n_py.maquila.guarantee"].create(
            {
                "name": "Ops Guar",
                "program_id": self.program.id,
                "guarantee_type": "bank",
                "amount": 100000,
                "date_start": fields.Date.today(),
                "date_end": fields.Date.today() + relativedelta(years=1),
            }
        )
        self.assertEqual(guar.amount_available, 100000)
        adm = self._admission(cif=40000, guarantee=guar)
        adm.action_admit()
        self.assertEqual(guar.amount_available, 60000)

    def test_admission_guarantee_insufficient(self):
        guar = self.env["l10n_py.maquila.guarantee"].create(
            {
                "name": "Ops Guar2",
                "program_id": self.program.id,
                "guarantee_type": "bank",
                "amount": 30000,
                "date_start": fields.Date.today(),
                "date_end": fields.Date.today() + relativedelta(years=1),
            }
        )
        adm = self._admission(cif=90000, guarantee=guar, cert="CN-X")
        with self.assertRaises(UserError):
            adm.action_admit()

    # ---------- export ----------
    def test_export_traceability(self):
        exp = self.env["l10n_py.maquila.export"].create(
            {"name": "EXP-OPS-1", "program_id": self.program.id}
        )
        with self.assertRaises(UserError):
            exp.action_confirm()
        adm = self._admission(cert="CN-EXP")
        exp.admission_ids = [(6, 0, [adm.id])]
        exp.action_confirm()
        self.assertEqual(exp.state, "confirmed")

    # ---------- TUM wizard ----------
    def _accounts(self):
        journal = self.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", self.company.id)], limit=1
        )
        if not journal:
            journal = self.env["account.journal"].create(
                {"name": "Misc", "code": "MISC", "type": "general"}
            )
        exp_acc = self.env["account.account"].search(
            [("account_type", "=", "expense")], limit=1
        ) or self.env["account.account"].create(
            {"name": "Exp", "code": "EXP1", "account_type": "expense"}
        )
        pay_acc = self.env["account.account"].search(
            [("account_type", "=", "liability_current")], limit=1
        ) or self.env["account.account"].create(
            {"name": "Pay", "code": "PAY1", "account_type": "liability_current"}
        )
        return journal, exp_acc, pay_acc

    def test_tum_wizard(self):
        _j, exp_acc, pay_acc = self._accounts()
        wiz = self.env["l10n_py.maquila.tum.wizard"].create(
            {
                "program_id": self.program.id,
                "period_start": "2026-01-01",
                "period_end": "2026-12-31",
                "van_amount": 30000,
                "export_invoice_amount": 50000,
                "tum_rate": 1.0,
                "debit_account_id": exp_acc.id,
                "credit_account_id": pay_acc.id,
            }
        )
        self.assertEqual(wiz.tum_base, 50000)
        self.assertEqual(wiz.tum_amount, 500)
        res = wiz.action_generate_move()
        move = self.env["account.move"].browse(res["res_id"])
        self.assertEqual(move.l10n_py_maquila_program_id, self.program)
        self.assertEqual(len(move.line_ids), 2)

    def test_tax_credit_wizard(self):
        _j, exp_acc, pay_acc = self._accounts()
        wiz = self.env["l10n_py.maquila.tax.credit.wizard"].create(
            {
                "program_id": self.program.id,
                "action_type": "compensate",
                "amount": 1000,
                "debit_account_id": exp_acc.id,
                "credit_account_id": pay_acc.id,
            }
        )
        res = wiz.action_execute()
        move = self.env["account.move"].browse(res["res_id"])
        self.assertEqual(move.l10n_py_maquila_program_id, self.program)

    # ---------- domestic sales cap (Ley 7547/2025 Art. 18) ----------
    def _prior_year_export(self, fob, program=None):
        year = fields.Date.today().year - 1
        self.env["l10n_py.maquila.export"].create(
            {
                "name": "EXP-PRIOR",
                "program_id": (program or self.program).id,
                "currency_id": self.company.currency_id.id,
                "date_export": f"{year}-06-01",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "quantity": 1,
                            "fob_value": fob,
                        },
                    )
                ],
            }
        )

    def _domestic_sale(self, qty, program=None):
        customer = self.env["res.partner"].create(
            {"name": "PY Customer", "country_id": self.py.id}
        )
        return self.env["sale.order"].create(
            {
                "partner_id": customer.id,
                "l10n_py_maquila_program_id": (program or self.program).id,
                "order_line": [
                    (0, 0, {"product_id": self.product.id, "product_uom_qty": qty})
                ],
            }
        )

    def test_domestic_sale_within_cap(self):
        self._prior_year_export(100000)  # cap = 10% = 10000
        order = self._domestic_sale(50)  # 50 * 100 = 5000
        order.action_confirm()
        self.assertEqual(order.state, "sale")

    def test_domestic_sale_exceeds_cap(self):
        self._prior_year_export(100000)  # cap = 10000
        order = self._domestic_sale(200)  # 200 * 100 = 20000 > 10000
        with self.assertRaises(UserError):
            order.action_confirm()

    def test_domestic_sale_no_prior_export_allowed(self):
        # New maquiladora with no prior-year exports: no cap to enforce.
        order = self._domestic_sale(200)
        order.action_confirm()
        self.assertEqual(order.state, "sale")

    def test_domestic_cap_skipped_for_non_pura(self):
        # A separate program so it does not affect the shared "pura" one.
        prog = self.env["l10n_py.maquila.program"].create(
            {
                "name": "Ops Ociosidad",
                "code": "RES-BIM-OPS-OCI",
                "maquila_type": "ociosidad",
                "matriz_partner_id": self.matriz.id,
                "company_id": self.company.id,
                "state": "active",
            }
        )
        self._prior_year_export(100000, program=prog)  # cap would be 10000 if pura
        order = self._domestic_sale(500, program=prog)  # 50000, over — but not pura
        order.action_confirm()
        self.assertEqual(order.state, "sale")
