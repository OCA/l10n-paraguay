# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestMaquilaMrp(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.matriz = cls.env["res.partner"].create({"name": "MRP Matriz"})
        cls.program = cls.env["l10n_py.maquila.program"].create(
            {
                "name": "MRP Program",
                "code": "RES-BIM-MRP-001",
                "maquila_type": "pura",
                "matriz_partner_id": cls.matriz.id,
                "company_id": cls.company.id,
                "state": "active",
            }
        )
        cls.plan = cls.env["account.analytic.plan"].search([], limit=1) or cls.env[
            "account.analytic.plan"
        ].create({"name": "MRP plan"})
        cls.analytic = cls.env["account.analytic.account"].create(
            {"name": "MRP analytic", "plan_id": cls.plan.id}
        )
        # Standard-cost category so stock valuation layers are deterministic.
        cls.categ = cls.env["product.category"].create(
            {"name": "MRP Std", "property_cost_method": "standard"}
        )
        cls.finished = cls.env["product.product"].create(
            {"name": "MRP Finished", "is_storable": True, "categ_id": cls.categ.id}
        )
        cls.raw_ta = cls.env["product.product"].create(
            {
                "name": "MRP Raw TA",
                "is_storable": True,
                "standard_price": 10,
                "categ_id": cls.categ.id,
            }
        )
        cls.raw_nat = cls.env["product.product"].create(
            {
                "name": "MRP Raw National",
                "is_storable": True,
                "standard_price": 20,
                "categ_id": cls.categ.id,
            }
        )
        cls.bom = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.finished.product_tmpl_id.id,
                "product_qty": 1,
                "l10n_py_maquila_program_id": cls.program.id,
                "l10n_py_intn_certified": True,
                "l10n_py_intn_certificate": "INTN-MRP-1",
                "bom_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.raw_ta.id,
                            "product_qty": 2,
                            "l10n_py_origin_type": "temporary_admission",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": cls.raw_nat.id,
                            "product_qty": 3,
                            "l10n_py_origin_type": "national_py",
                        },
                    ),
                ],
            }
        )

    def _make_done_production(self):
        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = self.finished
        mo_form.bom_id = self.bom
        mo_form.product_qty = 1.0
        mo = mo_form.save()
        mo.action_confirm()
        mo_form = Form(mo)
        mo_form.qty_producing = 1.0
        mo = mo_form.save()
        mo.with_context(skip_consumption=True, skip_backorder=True).button_mark_done()
        return mo

    def test_bom_fields(self):
        self.assertEqual(self.bom.l10n_py_maquila_program_id, self.program)
        self.assertTrue(self.bom.l10n_py_intn_certified)
        origins = self.bom.bom_line_ids.mapped("l10n_py_origin_type")
        self.assertIn("temporary_admission", origins)
        self.assertIn("national_py", origins)

    def test_production_program_compute(self):
        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = self.finished
        mo_form.bom_id = self.bom
        mo = mo_form.save()
        self.assertEqual(mo.l10n_py_maquila_program_id, self.program)

    def test_program_counts_and_actions(self):
        self.assertEqual(self.program.bom_count, 1)
        waste = self.env["l10n_py.maquila.waste"].create(
            {
                "program_id": self.program.id,
                "product_id": self.raw_nat.id,
                "quantity": 5,
                "waste_type": "scrap",
                "destination": "destruction",
            }
        )
        self.assertEqual(self.program.waste_count, 1)
        self.assertIn(waste, self.program.waste_ids)
        self.assertEqual(self.program.action_view_boms()["res_model"], "mrp.bom")
        self.assertEqual(
            self.program.action_view_productions()["res_model"], "mrp.production"
        )
        self.assertEqual(
            self.program.action_view_waste()["res_model"], "l10n_py.maquila.waste"
        )

    def test_waste_destruction_creates_scrap(self):
        waste = self.env["l10n_py.maquila.waste"].create(
            {
                "program_id": self.program.id,
                "product_id": self.raw_nat.id,
                "quantity": 3,
                "waste_type": "scrap",
                "destination": "destruction",
            }
        )
        self.assertTrue(waste.name)  # _rec_name populated
        waste.action_complete()
        self.assertEqual(waste.state, "completed")
        self.assertTrue(waste.scrap_id)
        self.assertEqual(waste.scrap_id.product_id, self.raw_nat)

    def test_waste_state_transitions(self):
        waste = self.env["l10n_py.maquila.waste"].create(
            {
                "program_id": self.program.id,
                "product_id": self.raw_nat.id,
                "quantity": 2,
                "waste_type": "defective",
                "destination": "reexport",
            }
        )
        self.assertEqual(waste.state, "pending")
        waste.action_process()
        self.assertEqual(waste.state, "in_process")
        waste.action_complete()
        self.assertEqual(waste.state, "completed")
        waste.action_pending()
        self.assertEqual(waste.state, "pending")

    def test_van_compute_logic(self):
        wiz = self.env["l10n_py.maquila.van.wizard"].create(
            {
                "program_id": self.program.id,
                "period_start": "2026-01-01",
                "period_end": "2026-12-31",
                "total_cost": 8000,
                "imported_cost": 3000,
            }
        )
        self.assertEqual(wiz.van_amount, 5000)
        self.assertEqual(wiz.van_percentage, 62.5)

    def test_van_compute_zero_total(self):
        wiz = self.env["l10n_py.maquila.van.wizard"].create(
            {
                "program_id": self.program.id,
                "period_start": "2026-01-01",
                "period_end": "2026-12-31",
            }
        )
        self.assertEqual(wiz.van_amount, 0)
        self.assertEqual(wiz.van_percentage, 0.0)
        self.assertEqual(wiz.mercosul_content, 0.0)

    def test_van_action_compute_requires_analytic(self):
        wiz = self.env["l10n_py.maquila.van.wizard"].create(
            {
                "program_id": self.program.id,
                "period_start": "2026-01-01",
                "period_end": "2026-12-31",
            }
        )
        with self.assertRaises(UserError):
            wiz.action_compute()

    def test_van_action_compute_no_production_fails(self):
        # No completed production: the origin split is unknown, so computing
        # the VAN must fail instead of silently reporting 100%.
        self.program.analytic_account_id = self.analytic.id
        self.env["account.analytic.line"].create(
            {
                "name": "labor",
                "account_id": self.analytic.id,
                "amount": -8000,
                "date": "2026-06-01",
            }
        )
        wiz = self.env["l10n_py.maquila.van.wizard"].create(
            {
                "program_id": self.program.id,
                "period_start": "2026-01-01",
                "period_end": "2026-12-31",
            }
        )
        with self.assertRaises(UserError):
            wiz.action_compute()

    def test_van_action_compute_with_production(self):
        self.program.analytic_account_id = self.analytic.id
        # Total cost booked to the program's analytic account for the period.
        self.env["account.analytic.line"].create(
            {
                "name": "total cost",
                "account_id": self.analytic.id,
                "amount": -8000,
                "date": "2026-06-01",
            }
        )
        mo = self._make_done_production()
        self.assertEqual(mo.state, "done")
        wiz = self.env["l10n_py.maquila.van.wizard"].create(
            {
                "program_id": self.program.id,
                "period_start": "2026-01-01",
                "period_end": "2026-12-31",
            }
        )
        wiz.action_compute()
        # 2 units of the temporary-admission raw @ 10 -> imported (foreign);
        # 3 units of the national raw @ 20 -> national.
        self.assertEqual(wiz.total_cost, 8000)
        self.assertEqual(wiz.imported_cost, 20)
        self.assertEqual(wiz.national_cost, 60)
        # VAN = total cost - foreign inputs (imported + mercosul).
        self.assertEqual(wiz.van_amount, 7980)
