from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "l10n_py")
class TestExportInvoiceLines(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.company.country_id = cls.env.ref("base.py")
        cls.tax_exonerado = cls.env["account.tax"].create({
            "name": "IVA Exonerado", "amount": 0, "amount_type": "percent",
            "type_tax_use": "sale", "l10n_py_iva_affectation": "2",
        })
        cls.tax_exento = cls.env["account.tax"].create({
            "name": "IVA Exento", "amount": 0, "amount_type": "percent",
            "type_tax_use": "sale", "l10n_py_iva_affectation": "3",
        })
        cls.product = cls.env["product.product"].create({"name": "Prod export"})

    def _invoice_with_tax(self, tax):
        return self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.env["res.partner"].create({"name": "X"}).id,
            "invoice_line_ids": [Command.create({
                "product_id": self.product.id, "quantity": 1, "price_unit": 100,
                "tax_ids": [Command.set(tax.ids)],
            })],
        })

    def test_exonerado_line_emits_ivatipo_2(self):
        inv = self._invoice_with_tax(self.tax_exonerado)
        items = inv._prepare_invoice_lines()
        self.assertEqual(items[0]["ivaTipo"], 2)
        self.assertEqual(items[0]["iva"], 0)
        self.assertEqual(items[0]["ivaBase"], 0)

    def test_exento_still_3(self):
        inv = self._invoice_with_tax(self.tax_exento)
        items = inv._prepare_invoice_lines()
        self.assertEqual(items[0]["ivaTipo"], 3)

    def test_fallback_no_field(self):
        # Retrocompat: força o campo vazio (False) p/ exercitar de verdade o
        # helper _l10n_py_infer_affectation — impostos legados sem afetação.
        tax5 = self.env["account.tax"].create({
            "name": "IVA 5 legacy", "amount": 5, "amount_type": "percent",
            "type_tax_use": "sale"})
        tax5.l10n_py_iva_affectation = False  # simula legado sem o campo
        inv = self._invoice_with_tax(tax5)
        items = inv._prepare_invoice_lines()
        self.assertEqual(items[0]["ivaTipo"], 1)  # fallback: amount 5 -> '1'
        self.assertEqual(items[0]["iva"], 5)

    def test_fallback_no_field_amount_zero(self):
        # Retrocompat: campo vazio + amount 0 cai no fallback -> Exento '3'.
        tax0 = self.env["account.tax"].create({
            "name": "IVA 0 legacy", "amount": 0, "amount_type": "percent",
            "type_tax_use": "sale"})
        tax0.l10n_py_iva_affectation = False  # simula legado sem o campo
        inv = self._invoice_with_tax(tax0)
        items = inv._prepare_invoice_lines()
        self.assertEqual(items[0]["ivaTipo"], 3)  # fallback: amount 0 -> '3'
        self.assertEqual(items[0]["iva"], 0)
