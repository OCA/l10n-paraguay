from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "l10n_py")
class TestResPartnerBulkWrite(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_py = cls.env.ref("base.py")
        cls.it_ruc = cls.env.ref("l10n_py_base.it_ruc")
        cls.partner_a, cls.partner_b = cls.env["res.partner"].create(
            [
                {
                    "name": "Bulk A",
                    "country_id": cls.country_py.id,
                    "l10n_latam_identification_type_id": cls.it_ruc.id,
                    "vat": "80012345",
                },
                {
                    "name": "Bulk B",
                    "country_id": cls.country_py.id,
                    "l10n_latam_identification_type_id": cls.it_ruc.id,
                    "vat": "80028061",
                },
            ]
        )

    def test_bulk_write_keeps_each_vat(self):
        """Writing the country on several partners keeps each partner's own vat"""
        vat_a, vat_b = self.partner_a.vat, self.partner_b.vat
        self.assertNotEqual(vat_a, vat_b)
        (self.partner_a | self.partner_b).write({"country_id": self.country_py.id})
        self.assertEqual(self.partner_a.vat, vat_a)
        self.assertEqual(self.partner_b.vat, vat_b)
