# Copyright 2026 Tiago Chaves
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "l10n_py")
class TestPaymentCondition(TransactionCase):
    """Payment condition must be built from the computed due dates.

    `account.payment.term.line.days` does not exist since 17.0, so reading it
    made every invoice with payment terms fail.
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
            {"name": "Cliente plazo", "country_id": cls.country_py.id}
        )
        cls.journal = cls.env["account.journal"].create(
            {"name": "Ventas plazo", "type": "sale", "code": "VPLZ"}
        )
        cls.term_one = cls.env["account.payment.term"].create(
            {
                "name": "30 días",
                "line_ids": [
                    (0, 0, {"value": "percent", "value_amount": 100.0, "nb_days": 30})
                ],
            }
        )
        cls.term_two = cls.env["account.payment.term"].create(
            {
                "name": "50/50 a 30 y 60 días",
                "line_ids": [
                    (0, 0, {"value": "percent", "value_amount": 50.0, "nb_days": 30}),
                    (0, 0, {"value": "percent", "value_amount": 50.0, "nb_days": 60}),
                ],
            }
        )

    def _make_invoice(self, term=None):
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "journal_id": self.journal.id,
                "invoice_date": fields.Date.to_date("2026-01-15"),
                "invoice_payment_term_id": term.id if term else False,
                "invoice_line_ids": [
                    (0, 0, {"name": "Servicio", "quantity": 1, "price_unit": 100.0})
                ],
            }
        )

    def test_cash_invoice(self):
        """Sin plazo, la condición es contado."""
        condition = self._make_invoice()._prepare_payment_condition()
        self.assertEqual(condition["tipo"], 1)
        self.assertIn("entregas", condition)
        self.assertNotIn("credito", condition)

    def test_single_instalment(self):
        """Un solo vencimiento: tipo 1 (plazo), plazo de 30 días."""
        condition = self._make_invoice(self.term_one)._prepare_payment_condition()
        self.assertEqual(condition["tipo"], 2)
        self.assertEqual(condition["credito"]["tipo"], 1)
        self.assertEqual(condition["credito"]["cuotas"], 1)
        self.assertEqual(condition["credito"]["plazo"], "30 días")
        self.assertEqual(
            condition["credito"]["infoCuotas"][0]["vencimiento"], "2026-02-14"
        )

    def test_foreign_currency_amount(self):
        """La cuota se declara en la moneda de la factura, no en la de la casa."""
        usd = self.env.ref("base.USD")
        if self.company.currency_id == usd:
            self.skipTest("La compañía ya opera en USD")
        self.env["res.currency.rate"].create(
            {"currency_id": usd.id, "name": "2026-01-01", "rate": 2.0}
        )
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "journal_id": self.journal.id,
                "currency_id": usd.id,
                "invoice_date": fields.Date.to_date("2026-01-15"),
                "invoice_payment_term_id": self.term_one.id,
                "invoice_line_ids": [
                    (0, 0, {"name": "Servicio", "quantity": 1, "price_unit": 100.0})
                ],
            }
        )
        condition = move._prepare_payment_condition()
        cuota = condition["credito"]["infoCuotas"][0]
        self.assertEqual(cuota["moneda"], "USD")
        # 100 USD, no los 200 PYG del balance
        self.assertAlmostEqual(cuota["monto"], move.amount_total, 2)

    def test_several_instalments(self):
        """Dos vencimientos: tipo 2 (cuotas) y un importe por cuota."""
        condition = self._make_invoice(self.term_two)._prepare_payment_condition()
        self.assertEqual(condition["credito"]["tipo"], 2)
        self.assertEqual(condition["credito"]["cuotas"], 2)
        self.assertEqual(
            [cuota["vencimiento"] for cuota in condition["credito"]["infoCuotas"]],
            ["2026-02-14", "2026-03-16"],
        )
        # 50 % / 50 % de 100
        self.assertEqual(
            [round(cuota["monto"], 2) for cuota in condition["credito"]["infoCuotas"]],
            [50.0, 50.0],
        )
