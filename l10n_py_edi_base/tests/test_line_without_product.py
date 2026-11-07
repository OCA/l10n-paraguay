# Copyright 2026 Tiago Chaves
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "l10n_py")
class TestLineWithoutProduct(TransactionCase):
    """A free-text line is a valid invoice line and must not break the DE.

    `l10n_py_ncm_code` is defined on `product.template`, so `hasattr` was true
    even on an empty recordset and the message read "El producto False no
    tiene código NCM".
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
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Cliente servicio",
                "country_id": cls.country_py.id,
                "street": "Calle Test 123",
            }
        )
        cls.journal = cls.env["account.journal"].create(
            {"name": "Ventas servicio", "type": "sale", "code": "VSER"}
        )
        cls.tax = cls.env["account.tax"].search(
            [
                ("type_tax_use", "=", "sale"),
                ("amount_type", "=", "percent"),
                ("amount", "=", 10.0),
                ("l10n_py_iva_affectation", "=", "1"),
            ],
            limit=1,
        )
        if not cls.tax:
            tax_group = cls.env["account.tax.group"].search(
                [("country_id", "=", cls.country_py.id)], limit=1
            ) or cls.env["account.tax.group"].create(
                {"name": "IVA", "country_id": cls.country_py.id}
            )
            cls.tax = cls.env["account.tax"].create(
                {
                    "name": "IVA 10% gravado",
                    "amount": 10.0,
                    "amount_type": "percent",
                    "type_tax_use": "sale",
                    "tax_group_id": tax_group.id,
                    "l10n_py_iva_affectation": "1",
                }
            )

    def _invoice(self):
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "journal_id": self.journal.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Servicio de consultoría",
                            "quantity": 1,
                            "price_unit": 100.0,
                            "tax_ids": [(6, 0, self.tax.ids)],
                        },
                    )
                ],
            }
        )

    def test_no_ncm_error_without_product(self):
        """Una línea sin producto no dispara el error de NCM."""
        with self.assertRaises(UserError) as ctx:
            self._invoice()._validate_edi_data()
        self.assertNotIn("NCM", str(ctx.exception))

    def test_item_code_without_product(self):
        """El código interno no puede ser 'PROD-False'."""
        item = self._invoice()._prepare_invoice_lines()[0]
        self.assertNotIn("False", item["codigo"])
        self.assertTrue(item["codigo"].startswith("SERV-"))

    def test_message_uses_line_label(self):
        """El mensaje de NCM muestra la etiqueta de la línea."""
        product = self.env["product.product"].create({"name": "Producto sin NCM"})
        move = self._invoice()
        move.invoice_line_ids.write({"product_id": product.id})
        with self.assertRaises(UserError) as ctx:
            move._validate_edi_data()
        self.assertIn("NCM", str(ctx.exception))
        self.assertIn("Servicio de consultoría", str(ctx.exception))
