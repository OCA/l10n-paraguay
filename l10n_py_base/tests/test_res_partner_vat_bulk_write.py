from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "l10n_py")
class TestResPartnerVatBulkWrite(TransactionCase):
    """Bulk write must not leak one partner's VAT to another."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.country_py = cls.env.ref("base.py")

    def _create(self, name, vat):
        return self.Partner.create(
            {
                "name": name,
                "country_id": self.country_py.id,
                "vat": vat,
            }
        )

    def test_bulk_country_write_keeps_each_vat(self):
        """Changing the country on several partners keeps each own VAT."""
        partner_a = self._create("VAT bulk A", "80012345-0")
        partner_b = self._create("VAT bulk B", "80028061-0")
        vat_a, vat_b = partner_a.vat, partner_b.vat
        self.assertNotEqual(vat_a, vat_b)

        (partner_a + partner_b).write({"country_id": self.country_py.id})

        self.assertEqual(partner_a.vat, vat_a)
        self.assertEqual(partner_b.vat, vat_b)
        self.assertNotEqual(partner_a.vat, partner_b.vat)

    def test_bulk_vat_write_applies_same_vat(self):
        """A vat passed in values is formatted once and applied to all records."""
        partner_a = self._create("VAT bulk C", "80012345-0")
        partner_b = self._create("VAT bulk D", "80028061-0")

        (partner_a + partner_b).write({"vat": "80012345-0"})

        self.assertEqual(partner_a.vat, partner_b.vat)
