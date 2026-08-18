from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "l10n_py")
class TestCronCheckEdiStatus(TransactionCase):
    """Tests for _cron_check_edi_status polling: it must apply the SIFEN
    check_status response to the document instead of discarding it."""

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
                "name": "Cliente Polling Test",
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
                    "code": "400097",
                    "account_type": "income",
                    "company_ids": [Command.link(cls.company.id)],
                }
            )

        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Ventas Polling",
                "type": "sale",
                "code": "VPL",
                "company_id": cls.company.id,
                "l10n_latam_use_documents": True,
            }
        )

        today = date.today()
        cls.authorization = cls.env["account.authorization"].create(
            {
                "name": "11223344",
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

    def _create_pending_doc(self, batch_id="LOTE-1"):
        """Helper: create an invoice already sent to SIFEN, awaiting status."""
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
        move.write(
            {
                "l10n_py_edi_status": "sent",
                "l10n_py_edi_batch_id": batch_id,
            }
        )
        return move

    def test_check_status_success_marks_accepted_and_generates_kude(self):
        """success=True must write status=accepted and trigger KuDE, not be
        silently discarded (bug: previous code had `pass` here)."""
        move = self._create_pending_doc()

        fake_connector = MagicMock()
        fake_connector.check_status.return_value = {
            "success": True,
            "result": {"status": "Aprobado", "cdc": move.l10n_py_cdc or "0" * 43},
        }

        with (
            patch.object(
                type(self.env["l10n_py.edi.connector"]),
                "search",
                return_value=fake_connector,
            ),
            patch.object(type(move), "_generate_kude") as mock_generate_kude,
        ):
            self.env["account.move"]._cron_check_edi_status()

        move.invalidate_recordset()
        self.assertEqual(move.l10n_py_edi_status, "accepted")
        self.assertEqual(move.l10n_py_edi_message, "Documento aceptado exitosamente")
        mock_generate_kude.assert_called_once()

    def test_check_status_rejected_marks_rejected(self):
        """success=False WITH a concrete estado (e.g. Rechazado) must write
        status=rejected, not be silently ignored."""
        move = self._create_pending_doc()

        fake_connector = MagicMock()
        fake_connector.check_status.return_value = {
            "success": False,
            "result": {"status": "Rechazado"},
        }

        with patch.object(
            type(self.env["l10n_py.edi.connector"]),
            "search",
            return_value=fake_connector,
        ):
            self.env["account.move"]._cron_check_edi_status()

        move.invalidate_recordset()
        self.assertEqual(move.l10n_py_edi_status, "rejected")
        self.assertIn("Rechazado", move.l10n_py_edi_message)

    def test_check_status_no_response_does_not_change_status(self):
        """success=False WITHOUT `result` (SIFEN still processing / timeout)
        must NOT change the document status, leaving it for the next cron
        run to retry."""
        move = self._create_pending_doc()

        fake_connector = MagicMock()
        fake_connector.check_status.return_value = {
            "success": False,
            "error": "Sin respuesta del SIFEN",
        }

        with patch.object(
            type(self.env["l10n_py.edi.connector"]),
            "search",
            return_value=fake_connector,
        ):
            self.env["account.move"]._cron_check_edi_status()

        move.invalidate_recordset()
        self.assertEqual(move.l10n_py_edi_status, "sent")
