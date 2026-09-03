# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from unittest import mock

from odoo.tests import TransactionCase, tagged

from odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client import (
    AtlasApiClient,
)


@tagged("post_install", "-at_install", "l10n_py")
class TestConsultarBancoExterior(TransactionCase):
    def setUp(self):
        super().setUp()
        # account_payment_order overrides base's res.partner.bank access
        # rule to require this group instead of group_partner_manager.
        self.env.user.groups_id |= self.env.ref(
            "account_payment_order.group_account_payment"
        )
        self.bank_account = self.env["res.partner.bank"].create(
            {
                "acc_number": "ATLAS-EXT-SWIFT-0001",
                "partner_id": self.env.company.partner_id.id,
                "atlas_enabled": True,
                "atlas_numero_cuenta": "1285242",
                "atlas_api_key": "test-key",
                "atlas_private_key_pem": "-----BEGIN PRIVATE KEY-----\n...",
            }
        )

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_consultar_banco_exterior_calls_the_documented_endpoint(self, mock_call):
        mock_call.return_value = {"nombreBanco": "VISION BANCO S.A.E.C.A."}
        client = AtlasApiClient.from_bank_account(self.bank_account)
        result = client.consultar_banco_exterior("VISCPYPA")
        mock_call.assert_called_once_with(
            "GET", "/datos-generales-atlas/v1.5.0/exterior/bancos/VISCPYPA"
        )
        self.assertEqual(result["nombreBanco"], "VISION BANCO S.A.E.C.A.")
