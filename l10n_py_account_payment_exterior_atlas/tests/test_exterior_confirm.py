# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from unittest import mock

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install", "l10n_py")
class TestExteriorConfirm(AccountTestInvoicingCommon):
    def setUp(self):
        super().setUp()
        # account_payment_order overrides base's res.partner.bank access
        # rule to require this group instead of group_partner_manager.
        self.env.user.groups_id |= self.env.ref(
            "account_payment_order.group_account_payment"
        )
        self.company_bank_account = self.env["res.partner.bank"].create(
            {
                "acc_number": "ATLAS-EXT-0002",
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

    def test_cannot_confirm_before_quoting(self):
        with self.assertRaises(UserError):
            self.transfer.action_atlas_confirmar()

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_confirm_sends_the_reference_from_the_quote(self, mock_call):
        self.transfer.write({"numero_referencia": 1911217, "state": "quoted"})
        mock_call.return_value = {
            "datosOperacion": {"numeroReferencia": 1911217},
            "respuesta": {"estado": "OK", "mensaje": None},
        }
        self.transfer.action_atlas_confirmar()
        _, kwargs = mock_call.call_args
        sent_body = kwargs["body"]
        self.assertEqual(sent_body["modo"], "C")
        self.assertEqual(sent_body["numeroReferencia"], 1911217)
        self.assertEqual(self.transfer.state, "confirmed")
