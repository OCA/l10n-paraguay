# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import date, timedelta
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "l10n_py")
class TestNumberInutilizationWizard(TransactionCase):
    """Testes do gap 3: wizard de inutilização a partir do timbrado (design 2026-08-18)."""

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

        today = date.today()
        cls.authorization = cls.env["account.authorization"].create(
            {
                "name": "33445566",
                "date_from": today - timedelta(days=30),
                "date_to": today + timedelta(days=335),
                "invoice_number_from": 1,
                "invoice_number_to": 10000,
                "establishment": "002",
                "expedition_point": "003",
                "l10n_latam_document_type_id": cls.doc_type_invoice.id,
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
                        "name": "Conector Test Inutilizacion",
                        "company_id": cls.company.id,
                        "provider_type": "sifen",
                        "environment": "test",
                    }
                )
            )

    def _make_wizard(self, number_from=9990, number_to=9999, motive="Test wizard"):
        return self.env["l10n_py.number.inutilization.wizard"].create(
            {
                "authorization_id": self.authorization.id,
                "number_from": number_from,
                "number_to": number_to,
                "motive": motive,
            }
        )

    def test_action_inutilize_creates_persistent_record(self):
        wizard = self._make_wizard()
        with patch.object(
            type(self.connector),
            "inutilize_range",
            return_value={"success": True},
        ):
            wizard.action_inutilize()
        inut = self.env["l10n_py.number.inutilization"].search(
            [("authorization_id", "=", self.authorization.id)]
        )
        self.assertEqual(len(inut), 1)
        self.assertEqual(inut.number_from, 9990)
        self.assertEqual(inut.number_to, 9999)
        self.assertEqual(inut.motive, "Test wizard")

    def test_action_inutilize_calls_action_send(self):
        wizard = self._make_wizard()
        with patch(
            "odoo.addons.l10n_py_edi_base.models.l10n_py_number_inutilization"
            ".NumberInutilization.action_send",
            autospec=True,
        ) as mocked_send:
            wizard.action_inutilize()
        mocked_send.assert_called_once()

    def test_wizard_range_validation_from_greater_than_to(self):
        with self.assertRaises(ValidationError):
            self._make_wizard(number_from=100, number_to=50)

    def test_wizard_inherits_within_authorization_range_constraint(self):
        wizard = self._make_wizard(number_from=1, number_to=5)
        # 1-5 pasa la validación básica del wizard; forzamos un rango fuera
        # del timbrado (autorización va de 1 a 10000) para que sea la
        # constraint del modelo persistente la que dispare al crear.
        wizard.write({"number_from": 10001, "number_to": 10005})
        with self.assertRaises(ValidationError):
            wizard.action_inutilize()

    def test_default_get_pulls_active_id_from_authorization(self):
        wizard = (
            self.env["l10n_py.number.inutilization.wizard"]
            .with_context(
                active_model="account.authorization", active_id=self.authorization.id
            )
            .create({"number_from": 1, "number_to": 2, "motive": "x"})
        )
        self.assertEqual(wizard.authorization_id, self.authorization)

    def test_action_send_uses_correct_authorization_fields(self):
        """Regresión del bug l10n_py_establishment/l10n_py_point (no existen)."""
        wizard = self._make_wizard()
        captured = {}

        def _fake_inutilize_range(self, data):
            captured.update(data)
            return {"success": True}

        with patch.object(
            type(self.connector), "inutilize_range", _fake_inutilize_range
        ):
            wizard.action_inutilize()

        self.assertEqual(captured.get("establecimiento"), "002")
        self.assertEqual(captured.get("punto"), "003")
