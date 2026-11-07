# Copyright 2026 Tiago Chaves
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "l10n_py")
class TestUnitPrice(TransactionCase):
    """`dPUniProSer` must be tax-included and before the discount.

    Odoo stores the tax-excluded price, so the item dict has to gross it up and
    send the discount separately, otherwise `dTotOpeItem` disagrees with
    `dBasGravIVA` on every taxed line.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.country_py = cls.env.ref("base.py")
        cls.company.write(
            {
                "country_id": cls.country_py.id,
                "account_fiscal_country_id": cls.country_py.id,
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "Cliente IVA", "country_id": cls.country_py.id}
        )
        cls.journal = cls.env["account.journal"].create(
            {"name": "Ventas IVA", "type": "sale", "code": "VIVA"}
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
            # El plan de cuentas de prueba puede no traer el 10 % gravado;
            # se crea para que el test no se salte en silencio.
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

    def _make_invoice(self, price_unit, discount, quantity=1.0):
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "journal_id": self.journal.id,
                "invoice_date": fields.Date.to_date("2026-01-15"),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Servicio",
                            "quantity": quantity,
                            "price_unit": price_unit,
                            "discount": discount,
                            "tax_ids": [(6, 0, self.tax.ids)],
                        },
                    )
                ],
            }
        )

    def test_tax_included_and_discount(self):
        """100 + 10 % IVA, 10 % descuento: 110 por unidad, 11 de descuento."""
        move = self._make_invoice(100.0, 10.0)
        item = move._prepare_invoice_lines()[0]
        self.assertAlmostEqual(item["precioUnitario"], 110.0, 2)
        self.assertAlmostEqual(item["descuento"], 11.0, 2)
        # Invariante SIFEN: (precio - descuento) * cantidad == total de línea
        self.assertAlmostEqual(
            (item["precioUnitario"] - item["descuento"]) * item["cantidad"],
            move.amount_total,
            2,
        )

    def test_no_discount(self):
        """Sin descuento el importe por unidad no cambia."""
        move = self._make_invoice(250.0, 0.0, quantity=2.0)
        item = move._prepare_invoice_lines()[0]
        self.assertAlmostEqual(item["precioUnitario"], 275.0, 2)
        self.assertAlmostEqual(item["descuento"], 0.0, 2)
        self.assertAlmostEqual(
            (item["precioUnitario"] - item["descuento"]) * item["cantidad"],
            move.amount_total,
            2,
        )

    def test_rounding_keeps_invariant(self):
        """Precio con decimales y moneda de 0: el invariante sigue cerrando."""
        move = self._make_invoice(33.33, 0.0, quantity=3.0)
        item = move._prepare_invoice_lines()[0]
        self.assertAlmostEqual(
            (item["precioUnitario"] - item["descuento"]) * item["cantidad"],
            move.amount_total,
            places=1,
        )

    def test_unit_code_from_product(self):
        """La unidad de medida sale del producto, no de un 77 fijo."""
        product = self.env["product.product"].create(
            {"name": "Harina", "l10n_py_unit_code": 83}
        )
        move = self._make_invoice(100.0, 0.0)
        move.invoice_line_ids.write({"product_id": product.id})
        item = move._prepare_invoice_lines()[0]
        self.assertEqual(item["unidadMedida"], 83)
