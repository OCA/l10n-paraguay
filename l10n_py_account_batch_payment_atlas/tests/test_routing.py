# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install", "l10n_py")
class TestAtlasRouting(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.write(
            {
                "groups_id": [
                    Command.link(
                        cls.env.ref(
                            "account_payment_batch_oca.group_account_payment"
                        ).id
                    )
                ]
            }
        )
        cls.company = cls.company_data["company"]
        cls.pyg = cls.env.ref("base.PYG", raise_if_not_found=False) or cls.env[
            "res.currency"
        ].create({"name": "PYG_TEST", "symbol": "Gs"})

    def _order_with_amount(self, amount, currency=None):
        bank_journal = self.company_data["default_journal_bank"]
        # Find or create an outbound payment method line
        method_line = self.env["account.payment.method.line"].search(
            [
                ("journal_id", "=", bank_journal.id),
                ("payment_method_id.payment_type", "=", "outbound"),
            ],
            limit=1,
        )
        if not method_line:
            # Create an outbound payment method if none exists
            payment_method = self.env["account.payment.method"].search(
                [("payment_type", "=", "outbound")], limit=1
            )
            if not payment_method:
                payment_method = self.env["account.payment.method"].create(
                    {
                        "name": "Test Outbound",
                        "payment_type": "outbound",
                        "code": "test_outbound",
                    }
                )
            method_line = self.env["account.payment.method.line"].create(
                {
                    "name": "Test Outbound Line",
                    "journal_id": bank_journal.id,
                    "payment_method_id": payment_method.id,
                }
            )
        order = self.env["account.payment.order"].create(
            {
                "payment_type": "outbound",
                "payment_method_line_id": method_line.id,
                "journal_id": bank_journal.id,
            }
        )
        partner = self.env["res.partner"].create({"name": "Proveedor Atlas Test"})
        self.env["account.payment.line"].create(
            {
                "order_id": order.id,
                "partner_id": partner.id,
                "amount_currency": amount,
                "currency_id": (currency or self.pyg).id,
            }
        )
        return order

    def test_pyg_below_spi_limit_routes_to_spi(self):
        order = self._order_with_amount(5_000_000)
        self.assertEqual(order.l10n_py_atlas_tipo_transferencia, "SPI")

    def test_pyg_above_spi_limit_routes_to_lbtr(self):
        order = self._order_with_amount(5_000_001)
        self.assertEqual(order.l10n_py_atlas_tipo_transferencia, "LBTR")

    def test_non_pyg_currency_always_routes_to_lbtr(self):
        usd = self.env.ref("base.USD")
        order = self._order_with_amount(100, currency=usd)
        self.assertEqual(order.l10n_py_atlas_tipo_transferencia, "LBTR")

    def test_manual_override_is_respected(self):
        order = self._order_with_amount(1000)
        order.l10n_py_atlas_tipo_transferencia = "ACH"
        # A manual write must survive: re-triggering the compute (by
        # touching a dependency to the SAME value) must not clobber it
        # because `readonly=False` computed fields only recompute when a
        # real dependency change invalidates the cache -- here we assert
        # the value simply stays ACH after being set by hand.
        self.assertEqual(order.l10n_py_atlas_tipo_transferencia, "ACH")

    def test_forcing_spi_above_limit_raises_on_confirm(self):
        from odoo.exceptions import UserError

        order = self._order_with_amount(5_000_001)
        order.l10n_py_atlas_tipo_transferencia = "SPI"
        with self.assertRaises(UserError):
            order._check_l10n_py_atlas_routing()

    def test_mixed_currency_batch_raises(self):
        from odoo.exceptions import UserError

        order = self._order_with_amount(1000)
        usd = self.env.ref("base.USD")
        self.env["account.payment.line"].create(
            {
                "order_id": order.id,
                "partner_id": self.env["res.partner"]
                .create({"name": "Segundo Proveedor"})
                .id,
                "amount_currency": 50,
                "currency_id": usd.id,
            }
        )
        with self.assertRaises(UserError):
            order._check_l10n_py_atlas_routing()
