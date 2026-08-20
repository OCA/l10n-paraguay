# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "l10n_py")
class TestResPartnerBankAtlas(TransactionCase):
    def test_atlas_fields_exist_and_default_to_disabled(self):
        partner = self.env["res.partner"].create({"name": "Test Partner"})
        partner_bank = self.env["res.partner.bank"].create(
            {
                "acc_number": "ATLAS-TEST-0001",
                "partner_id": partner.id,
            }
        )
        self.assertFalse(partner_bank.atlas_enabled)
        self.assertEqual(partner_bank.atlas_environment, "testing")

    def test_atlas_credentials_can_be_set(self):
        partner = self.env["res.partner"].create({"name": "Test Partner 2"})
        partner_bank = self.env["res.partner.bank"].create(
            {
                "acc_number": "ATLAS-TEST-0002",
                "partner_id": partner.id,
                "atlas_enabled": True,
                "atlas_numero_cuenta": "123456",
                "atlas_api_key": "test-key",
                "atlas_private_key_pem": "-----BEGIN PRIVATE KEY-----\n...",
            }
        )
        self.assertTrue(partner_bank.atlas_enabled)
        self.assertEqual(partner_bank.atlas_numero_cuenta, "123456")
