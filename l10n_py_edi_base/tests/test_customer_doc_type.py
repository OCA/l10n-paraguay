# Copyright 2026 Tiago Chaves
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "l10n_py")
class TestCustomerDocType(TransactionCase):
    """SIFEN `iTipIDRec` must not reuse the module's internal keys.

    The partner selection is 1 Cédula, 2 Pasaporte, 3 Carnet de residencia,
    4 Innominado; SIFEN is 1 Cédula, 2 Pasaporte, 3 Cédula extranjera,
    4 Carnet de residencia, 5 Innominado.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_py = cls.env.ref("base.py")
        cls.company = cls.env.ref("base.main_company")
        cls.company.write(
            {
                "country_id": cls.country_py.id,
                "account_fiscal_country_id": cls.country_py.id,
            }
        )
        cls.journal = cls.env["account.journal"].create(
            {"name": "Ventas doc", "type": "sale", "code": "VDOC"}
        )

    def _move_for(self, doc_type):
        partner = self.env["res.partner"].create(
            {
                "name": "Cliente sin nombre",
                "country_id": self.country_py.id,
                "l10n_py_taxpayer_type": "2",
                "l10n_py_doc_type": doc_type,
                "l10n_py_doc_number": "0",
            }
        )
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": partner.id,
                "journal_id": self.journal.id,
                "invoice_line_ids": [
                    (0, 0, {"name": "Servicio", "quantity": 1, "price_unit": 100.0})
                ],
            }
        )

    def test_cedula(self):
        self.assertEqual(
            self._move_for("1")._prepare_customer_data()["documentoTipo"], 1
        )

    def test_pasaporte(self):
        self.assertEqual(
            self._move_for("2")._prepare_customer_data()["documentoTipo"], 2
        )

    def test_carnet_residencia(self):
        """El carnet es 4, no 3 (que en SIFEN es cédula extranjera)."""
        self.assertEqual(
            self._move_for("3")._prepare_customer_data()["documentoTipo"], 4
        )

    def test_innominado(self):
        """El innominado es 5, no 4 (que en SIFEN es carnet)."""
        self.assertEqual(
            self._move_for("4")._prepare_customer_data()["documentoTipo"], 5
        )
