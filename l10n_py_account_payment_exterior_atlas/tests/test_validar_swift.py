# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from unittest import mock

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client import (
    AtlasApiError,
)


@tagged("post_install", "-at_install", "l10n_py")
class TestValidarSwift(AccountTestInvoicingCommon):
    def setUp(self):
        super().setUp()
        # account_payment_order overrides base's res.partner.bank access
        # rule to require this group instead of group_partner_manager.
        self.env.user.groups_id |= self.env.ref(
            "account_payment_order.group_account_payment"
        )
        self.company_bank_account = self.env["res.partner.bank"].create(
            {
                "acc_number": "ATLAS-EXT-SWIFT-0002",
                "partner_id": self.company_data["company"].partner_id.id,
                "atlas_enabled": True,
                "atlas_numero_cuenta": "1285242",
                "atlas_api_key": "test-key",
                "atlas_private_key_pem": "-----BEGIN PRIVATE KEY-----\n...",
            }
        )
        self.transfer = self.env["l10n_py.atlas.exterior.transfer"].create(
            {
                "company_bank_account_id": self.company_bank_account.id,
                "moneda": "USD",
                "monto_transferencia": 101,
                "codigo_motivo": "5",
                "tipo_cargo": "OUR",
                "plazo": "24",
                "beneficiario_nombre": "Javier Meza",
                "beneficiario_cuenta": "3973099",
                "beneficiario_swift": "VISCPYPA",
                "beneficiario_pais": 1,
                "beneficiario_ciudad": 1,
                "beneficiario_direccion": "Some street 123",
            }
        )

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_validar_swift_success_fills_bank_name(self, mock_call):
        mock_call.return_value = {"nombreBanco": "VISION BANCO S.A.E.C.A."}
        self.transfer.action_validar_swift()
        self.assertEqual(
            self.transfer.beneficiario_banco_nombre, "VISION BANCO S.A.E.C.A."
        )
        mock_call.assert_called_once_with(
            "GET", "/datos-generales-atlas/v1.5.0/exterior/bancos/VISCPYPA"
        )

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_validar_swift_unknown_code_raises_user_error(self, mock_call):
        mock_call.side_effect = AtlasApiError(
            code=404, message="Not found", error_type="NOT_FOUND"
        )
        with self.assertRaisesRegex(UserError, "no reconoce el código SWIFT"):
            self.transfer.action_validar_swift()
        self.assertFalse(self.transfer.beneficiario_banco_nombre)

    def test_validar_swift_without_code_raises_user_error(self):
        # beneficiario_swift is required=True on the persisted model, so
        # writing False to a saved record would hit the DB's NOT NULL
        # constraint before action_validar_swift()'s own guard even
        # runs. Use an unsaved .new() record instead -- in-memory only,
        # no SQL constraint -- so the Python-level guard is what's
        # actually exercised.
        transfer = self.transfer.new({"beneficiario_swift": False})
        with self.assertRaises(UserError):
            transfer.action_validar_swift()

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_validar_swift_no_bank_name_in_response_raises_user_error(self, mock_call):
        mock_call.return_value = {}
        with self.assertRaisesRegex(UserError, "no devolvió un nombre de banco"):
            self.transfer.action_validar_swift()
        self.assertFalse(self.transfer.beneficiario_banco_nombre)

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_write_new_swift_clears_cached_bank_name(self, mock_call):
        mock_call.return_value = {"nombreBanco": "VISION BANCO S.A.E.C.A."}
        self.transfer.action_validar_swift()
        self.assertEqual(
            self.transfer.beneficiario_banco_nombre, "VISION BANCO S.A.E.C.A."
        )
        self.transfer.write({"beneficiario_swift": "BBVAPYAS"})
        self.assertFalse(self.transfer.beneficiario_banco_nombre)

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_payload_uses_validated_bank_name(self, mock_call):
        mock_call.return_value = {"nombreBanco": "VISION BANCO S.A.E.C.A."}
        self.transfer.action_validar_swift()
        payload = self.transfer._l10n_py_atlas_exterior_payload("V")
        self.assertEqual(
            payload["beneficiario"]["nombreBancoBeneficiario"],
            "VISION BANCO S.A.E.C.A.",
        )
