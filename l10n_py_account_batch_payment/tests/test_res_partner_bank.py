# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "l10n_py")
class TestResPartnerBankCasAlias(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "SIPAP Test Partner"})
        cls.bank = cls.env["res.bank"].create({"name": "Test SIPAP Bank"})

    def test_cas_alias_type_and_value_together_is_valid(self):
        account = self.env["res.partner.bank"].create(
            {
                "acc_number": "0001-TEST-CAS-1",
                "partner_id": self.partner.id,
                "bank_id": self.bank.id,
                "l10n_py_cas_alias_type": "phone",
                "l10n_py_cas_alias_value": "+595981000000",
            }
        )
        self.assertEqual(account.l10n_py_cas_alias_type, "phone")
        self.assertEqual(account.l10n_py_cas_alias_value, "+595981000000")

    def test_cas_alias_type_without_value_raises(self):
        with self.assertRaises(ValidationError):
            self.env["res.partner.bank"].create(
                {
                    "acc_number": "0001-TEST-CAS-2",
                    "partner_id": self.partner.id,
                    "bank_id": self.bank.id,
                    "l10n_py_cas_alias_type": "email",
                }
            )

    def test_cas_alias_value_without_type_raises(self):
        with self.assertRaises(ValidationError):
            self.env["res.partner.bank"].create(
                {
                    "acc_number": "0001-TEST-CAS-3",
                    "partner_id": self.partner.id,
                    "bank_id": self.bank.id,
                    "l10n_py_cas_alias_value": "someone@example.com",
                }
            )

    def test_sipap_bank_code_comes_from_bank(self):
        self.bank.l10n_py_sipap_bank_code = "999"
        account = self.env["res.partner.bank"].create(
            {
                "acc_number": "0001-TEST-CAS-4",
                "partner_id": self.partner.id,
                "bank_id": self.bank.id,
            }
        )
        self.assertEqual(account.l10n_py_sipap_bank_code, "999")
