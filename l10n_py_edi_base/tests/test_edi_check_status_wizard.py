# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import date, timedelta
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "l10n_py")
class TestEdiCheckStatusWizard(TransactionCase):
    """Testes do gap 2: wizard de consulta manual de status EDI (design 2026-08-18)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.country_py = cls.env.ref("base.py")
        cls.company.write(
            {
                "country_id": cls.country_py.id,
                "account_fiscal_country_id": cls.country_py.id,
            }
        )

        cls.doc_type_invoice = cls.env["l10n_latam.document.type"].search(
            [("country_id", "=", cls.country_py.id), ("code", "=", "1")],
            limit=1,
        )
        if not cls.doc_type_invoice:
            cls.doc_type_invoice = cls.env["l10n_latam.document.type"].create(
                {
                    "name": "Factura",
                    "code": "1",
                    "country_id": cls.country_py.id,
                    "internal_type": "invoice",
                }
            )

        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Cliente Test Check Status",
                "country_id": cls.country_py.id,
            }
        )

        cls.account_income = cls.env["account.account"].search(
            [
                ("company_ids", "in", cls.company.id),
                ("account_type", "=", "income"),
            ],
            limit=1,
        )
        if not cls.account_income:
            cls.account_income = cls.env["account.account"].create(
                {
                    "name": "Ingresos",
                    "code": "400098",
                    "account_type": "income",
                    "company_ids": [Command.link(cls.company.id)],
                }
            )

        cls.account_receivable = cls.env["account.account"].search(
            [
                ("company_ids", "in", cls.company.id),
                ("account_type", "=", "asset_receivable"),
            ],
            limit=1,
        )
        if not cls.account_receivable:
            cls.account_receivable = cls.env["account.account"].create(
                {
                    "name": "Cuentas por Cobrar",
                    "code": "110098",
                    "account_type": "asset_receivable",
                    "reconcile": True,
                    "company_ids": [Command.link(cls.company.id)],
                }
            )

        cls.partner.property_account_receivable_id = cls.account_receivable

        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Ventas Check Status Test",
                "type": "sale",
                "code": "VCS",
                "company_id": cls.company.id,
                "l10n_latam_use_documents": True,
            }
        )

        today = date.today()
        cls.authorization = cls.env["account.authorization"].create(
            {
                "name": "44556677",
                "date_from": today - timedelta(days=30),
                "date_to": today + timedelta(days=335),
                "invoice_number_from": 1,
                "invoice_number_to": 10000,
                "establishment": "001",
                "expedition_point": "001",
                "l10n_latam_document_type_id": cls.doc_type_invoice.id,
                "company_id": cls.company.id,
            }
        )

        cls.tax_exempt = cls.env["account.tax"].search(
            [
                ("name", "=", "Exento"),
                ("type_tax_use", "=", "sale"),
                ("company_id", "=", cls.company.id),
            ],
            limit=1,
        )
        if not cls.tax_exempt:
            cls.tax_exempt = cls.env["account.tax"].create(
                {
                    "name": "Exento",
                    "amount": 0.0,
                    "amount_type": "percent",
                    "type_tax_use": "sale",
                    "company_id": cls.company.id,
                }
            )

        cls.connector = (
            cls.env["l10n_py.edi.connector"]
            .sudo()
            .search([("company_id", "=", cls.company.id)], limit=1)
        )
        if not cls.connector:
            cls.connector = (
                cls.env["l10n_py.edi.connector"]
                .sudo()
                .create(
                    {
                        "name": "Conector Test Check Status",
                        "company_id": cls.company.id,
                        "provider_type": "sifen",
                        "environment": "test",
                    }
                )
            )

    def _create_and_post_invoice(self, cdc=False, edi_status="sent"):
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "journal_id": self.journal.id,
                "l10n_py_authorization_id": self.authorization.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Producto Test",
                            "quantity": 1,
                            "price_unit": 50000.0,
                            "tax_ids": [(6, 0, [self.tax_exempt.id])],
                            "account_id": self.account_income.id,
                        },
                    )
                ],
            }
        )
        move.action_post()
        move.write({"l10n_py_cdc": cdc, "l10n_py_edi_status": edi_status})
        return move

    def test_action_check_status_requires_cdc(self):
        move = self._create_and_post_invoice(cdc=False, edi_status="to_send")
        wizard = self.env["l10n_py.edi.check.status.wizard"].create(
            {"invoice_id": move.id}
        )
        with self.assertRaises(UserError):
            wizard.action_check_status()

    def test_action_check_status_calls_connector_with_cdc_not_batch_id(self):
        move = self._create_and_post_invoice(
            cdc="01234567890123456789012345678901234567890", edi_status="sent"
        )
        move.l10n_py_edi_batch_id = "batch-999"
        wizard = self.env["l10n_py.edi.check.status.wizard"].create(
            {"invoice_id": move.id}
        )
        with patch.object(
            type(self.connector),
            "check_status",
            return_value={"success": True, "result": {"status": "Aprobado"}},
        ) as mocked_check_status:
            wizard.action_check_status()
        mocked_check_status.assert_called_once()
        called_args = mocked_check_status.call_args.args
        self.assertIn(move.l10n_py_cdc, called_args)
        self.assertNotIn(move.l10n_py_edi_batch_id, called_args)

    def test_action_check_status_persists_result_on_invoice(self):
        move = self._create_and_post_invoice(
            cdc="09876543210987654321098765432109876543210", edi_status="sent"
        )
        wizard = self.env["l10n_py.edi.check.status.wizard"].create(
            {"invoice_id": move.id}
        )
        with patch.object(
            type(self.connector),
            "check_status",
            return_value={"success": True, "result": {"status": "Aprobado"}},
        ):
            wizard.action_check_status()
        self.assertEqual(move.l10n_py_edi_status, "accepted")
        self.assertEqual(wizard.status, "accepted")

    def test_action_check_status_persists_rejected_not_error(self):
        """success=False con result.status='Rechazado' es rechazo real del
        SIFEN, no un error técnico: debe persistir 'rejected', nunca 'error'.

        Reproduce la respuesta real de `_sifen_check_status`, que calcula
        `success = (estado == "Aprobado")` y siempre adjunta `result.status`
        con el estado crudo devuelto por el SIFEN, incluso cuando ese estado
        es "Rechazado".
        """
        move = self._create_and_post_invoice(
            cdc="33333333333333333333333333333333333333333", edi_status="sent"
        )
        wizard = self.env["l10n_py.edi.check.status.wizard"].create(
            {"invoice_id": move.id}
        )
        with patch.object(
            type(self.connector),
            "check_status",
            return_value={
                "success": False,
                "result": {"status": "Rechazado", "cdc": move.l10n_py_cdc},
            },
        ):
            wizard.action_check_status()
        self.assertEqual(move.l10n_py_edi_status, "rejected")
        self.assertEqual(wizard.status, "rejected")

    def test_action_check_status_persists_error_without_result_status(self):
        """success=False sin result.status (error técnico/timeout) sigue
        mapeando a 'error', para no confundirlo con un rechazo de negocio."""
        move = self._create_and_post_invoice(
            cdc="44444444444444444444444444444444444444444", edi_status="sent"
        )
        wizard = self.env["l10n_py.edi.check.status.wizard"].create(
            {"invoice_id": move.id}
        )
        with patch.object(
            type(self.connector),
            "check_status",
            return_value={"success": False, "error": "Sin respuesta del SIFEN"},
        ):
            wizard.action_check_status()
        self.assertEqual(move.l10n_py_edi_status, "error")
        self.assertEqual(wizard.status, "error")

    def test_wizard_default_get_pulls_active_id(self):
        move = self._create_and_post_invoice(
            cdc="11111111111111111111111111111111111111111"
        )
        wizard = (
            self.env["l10n_py.edi.check.status.wizard"]
            .with_context(active_model="account.move", active_id=move.id)
            .create({})
        )
        self.assertEqual(wizard.invoice_id, move)

    def test_button_invisible_without_cdc(self):
        """El botón sólo debe declarar invisible="not l10n_py_cdc" en el arch."""
        view = self.env.ref("l10n_py_edi_base.view_move_form_edi")
        arch = view.arch_db
        button_snippet = arch[
            arch.index('name="action_open_check_status_wizard"') : arch.index(
                'name="action_open_check_status_wizard"'
            )
            + 200
        ]
        self.assertIn('invisible="not l10n_py_cdc"', button_snippet)

    def test_cron_check_edi_status_uses_cdc_and_persists(self):
        move = self._create_and_post_invoice(
            cdc="22222222222222222222222222222222222222222", edi_status="sent"
        )
        with patch.object(
            type(self.connector),
            "check_status",
            return_value={"success": True, "result": {"status": "Aprobado"}},
        ) as mocked_check_status:
            self.env["account.move"]._cron_check_edi_status()
        mocked_check_status.assert_called_with(move.l10n_py_cdc)
        self.assertEqual(move.l10n_py_edi_status, "accepted")
