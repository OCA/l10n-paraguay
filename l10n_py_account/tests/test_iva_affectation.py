from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "l10n_py")
class TestIvaAffectation(TransactionCase):
    def test_field_exists_and_default(self):
        tax = self.env["account.tax"].create(
            {
                "name": "IVA test",
                "amount": 10,
                "amount_type": "percent",
                "type_tax_use": "sale",
            }
        )
        # campo existe e default '1' (Gravado)
        self.assertEqual(tax.l10n_py_iva_affectation, "1")

    def test_affectation_settable(self):
        tax = self.env["account.tax"].create(
            {
                "name": "IVA exonerado",
                "amount": 0,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "l10n_py_iva_affectation": "2",
            }
        )
        self.assertEqual(tax.l10n_py_iva_affectation, "2")
