# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client import (
    AtlasApiClient,
)


@tagged("post_install", "-at_install", "l10n_py")
class TestAtlasApiClientFromBankAccount(TransactionCase):
    """I5: from_bank_account() must raise a clear UserError for every
    misconfiguration, instead of an opaque KeyError/MissingSchema deep
    inside call()."""

    def test_not_atlas_enabled_raises_clear_user_error(self):
        partner = self.env["res.partner"].create({"name": "Not Atlas Partner"})
        bank_account = self.env["res.partner.bank"].create(
            {"acc_number": "NOT-ATLAS-0001", "partner_id": partner.id}
        )
        with self.assertRaises(UserError):
            AtlasApiClient.from_bank_account(bank_account)

    def test_empty_recordset_raises_clear_user_error(self):
        empty = self.env["res.partner.bank"].browse()
        with self.assertRaises(UserError):
            AtlasApiClient.from_bank_account(empty)

    def test_missing_environment_raises_clear_user_error(self):
        partner = self.env["res.partner"].create({"name": "No Env Partner"})
        bank_account = self.env["res.partner.bank"].create(
            {
                "acc_number": "NO-ENV-0001",
                "partner_id": partner.id,
                "atlas_enabled": True,
                "atlas_numero_cuenta": "123456",
                "atlas_api_key": "test-key",
                "atlas_private_key_pem": "-----BEGIN PRIVATE KEY-----\n...",
            }
        )
        bank_account.atlas_environment = False
        with self.assertRaises(UserError):
            AtlasApiClient.from_bank_account(bank_account)

    def test_production_without_url_raises_clear_user_error(self):
        partner = self.env["res.partner"].create({"name": "Prod No URL Partner"})
        bank_account = self.env["res.partner.bank"].create(
            {
                "acc_number": "PROD-NO-URL-0001",
                "partner_id": partner.id,
                "atlas_enabled": True,
                "atlas_environment": "production",
                "atlas_production_url": False,
                "atlas_numero_cuenta": "123456",
                "atlas_api_key": "test-key",
                "atlas_private_key_pem": "-----BEGIN PRIVATE KEY-----\n...",
            }
        )
        with self.assertRaises(UserError):
            AtlasApiClient.from_bank_account(bank_account)
