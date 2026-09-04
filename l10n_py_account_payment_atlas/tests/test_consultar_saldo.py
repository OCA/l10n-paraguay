# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from unittest import mock

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "l10n_py")
class TestConsultarSaldo(TransactionCase):
    def setUp(self):
        super().setUp()
        # account_payment_order overrides base's res.partner.bank access
        # rule to require this group instead of group_partner_manager.
        self.env.user.groups_id |= self.env.ref(
            "account_payment_order.group_account_payment"
        )
        partner = self.env["res.partner"].create({"name": "Test Partner"})
        self.bank_account = self.env["res.partner.bank"].create(
            {
                "acc_number": "ATLAS-SALDO-0001",
                "partner_id": partner.id,
                "atlas_enabled": True,
                "atlas_numero_cuenta": "123456",
                "atlas_api_key": "test-key",
                "atlas_private_key_pem": "-----BEGIN PRIVATE KEY-----\n...",
            }
        )

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_consultar_saldo_stores_the_response(self, mock_call):
        mock_call.return_value = {
            "nroCuenta": "123456",
            "saldo": 5000000,
            "saldoDisponible": 4800000,
        }
        self.bank_account.action_atlas_consultar_saldo()
        self.assertEqual(self.bank_account.atlas_saldo, 5000000)
        self.assertEqual(self.bank_account.atlas_saldo_disponible, 4800000)
        self.assertTrue(self.bank_account.atlas_saldo_consulta_fecha)
        mock_call.assert_called_once_with(
            "GET", "/cuentas-atlas/v1.5.0/cuentas/123456/saldo"
        )
