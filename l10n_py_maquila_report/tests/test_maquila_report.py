# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestMaquilaReport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.matriz = cls.env["res.partner"].create({"name": "Rep Matriz"})
        cls.program = cls.env["l10n_py.maquila.program"].create(
            {
                "name": "Rep Program",
                "code": "RES-BIM-REP-001",
                "maquila_type": "pura",
                "matriz_partner_id": cls.matriz.id,
                "company_id": cls.company.id,
                "state": "active",
            }
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Rep Product", "is_storable": True}
        )
        # one admission and one export in the period
        cls.admission = cls.env["l10n_py.maquila.admission"].create(
            {
                "name": "DI-REP-1",
                "program_id": cls.program.id,
                "cnime_certificate": "CN-REP",
                "amount_cif": 10000,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "quantity": 100,
                            "fob_value": 10000,
                        },
                    )
                ],
            }
        )
        cls.export = cls.env["l10n_py.maquila.export"].create(
            {
                "name": "EXP-REP-1",
                "program_id": cls.program.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "quantity": 80,
                            "fob_value": 15000,
                        },
                    )
                ],
            }
        )
        cls.report = cls.env["l10n_py.maquila.cnime.report"].create(
            {
                "program_id": cls.program.id,
                "period_start": fields.Date.to_date("2026-01-01"),
                "period_end": fields.Date.to_date("2026-12-31"),
                "employment_count": 25,
            }
        )

    def test_report_data_populated(self):
        # Data is compiled by action_generate(), not by a compute.
        self.report.action_generate()
        self.assertTrue(self.report.import_data)
        self.assertIn("DI-REP-1", self.report.import_data)
        self.assertTrue(self.report.export_data)
        self.assertIn("EXP-REP-1", self.report.export_data)

    def test_report_state_flow(self):
        self.assertEqual(self.report.state, "draft")
        self.report.action_generate()
        self.assertEqual(self.report.state, "generated")
        self.report.action_validate()
        self.assertEqual(self.report.state, "validated")
        self.report.action_submit()
        self.assertEqual(self.report.state, "submitted")
        self.assertTrue(self.report.submission_date)

    def test_submitted_report_is_frozen(self):
        self.report.action_generate()
        self.report.action_validate()
        self.report.action_submit()
        # A submitted report cannot be reset to draft nor regenerated.
        with self.assertRaises(UserError):
            self.report.action_draft()
        with self.assertRaises(UserError):
            self.report.action_generate()

    def test_simex_payload(self):
        self.report.action_generate()
        result = self.report.action_generate_simex_payload()
        self.assertEqual(result["type"], "ir.actions.client")

    def test_account_move_legend(self):
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.matriz.id,
                "l10n_py_maquila_program_id": self.program.id,
            }
        )
        self.assertTrue(move.l10n_py_is_maquila_export)
        # The SIFEN legend method must inject the maquila legend.
        data = move._prepare_edi_document_data()
        self.assertIn("Ley 7547/2025", data.get("observacion") or "")
