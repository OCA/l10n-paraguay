# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from unittest import mock

from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install", "l10n_py")
class TestAtlasPolling(AccountTestInvoicingCommon):
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
        cls.bank_journal = cls.company_data["default_journal_bank"]
        cls.company_bank_account = cls.env["res.partner.bank"].create(
            {
                "acc_number": "ATLAS-POLL-0001",
                "partner_id": cls.company_data["company"].partner_id.id,
                "atlas_enabled": True,
                "atlas_numero_cuenta": "763797",
                "atlas_api_key": "test-key",
                "atlas_private_key_pem": "-----BEGIN PRIVATE KEY-----\n...",
            }
        )
        cls.bank_journal.bank_account_id = cls.company_bank_account.id

        # NOTE: searching account.payment.method.line by journal_id alone
        # can pick up an *inbound* method line (this bit tasks 9-11 in
        # this same plan) -- account_payment_batch_oca's own
        # ValidationError then fires when creating the order. Filter for
        # an outbound method line explicitly, creating one if none exists
        # (mirrors the fix already applied in tests/test_dispatch.py).
        method_line = cls.env["account.payment.method.line"].search(
            [
                ("journal_id", "=", cls.bank_journal.id),
                ("payment_method_id.payment_type", "=", "outbound"),
            ],
            limit=1,
        )
        if not method_line:
            payment_method = cls.env["account.payment.method"].search(
                [("payment_type", "=", "outbound")], limit=1
            )
            if not payment_method:
                payment_method = cls.env["account.payment.method"].create(
                    {
                        "name": "Test Outbound",
                        "payment_type": "outbound",
                        "code": "test_outbound",
                    }
                )
            method_line = cls.env["account.payment.method.line"].create(
                {
                    "name": "Test Outbound Line",
                    "journal_id": cls.bank_journal.id,
                    "payment_method_id": payment_method.id,
                }
            )
        cls.method_line = method_line

    def _pending_line(self, nro_orden=888853):
        order = self.env["account.payment.order"].create(
            {
                "payment_type": "outbound",
                "payment_method_line_id": self.method_line.id,
                "journal_id": self.bank_journal.id,
            }
        )
        currency = self.env.ref("base.PYG", raise_if_not_found=False) or self.env[
            "res.currency"
        ].create({"name": "PYG_TEST"})
        return self.env["account.payment.line"].create(
            {
                "order_id": order.id,
                "partner_id": self.env["res.partner"].create({"name": "P"}).id,
                "amount_currency": 1000,
                "currency_id": currency.id,
                "atlas_nro_orden": nro_orden,
            }
        )

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_poll_marks_line_confirmed_when_it_appears_in_the_response(self, mock_call):
        line = self._pending_line(nro_orden=888853)
        mock_call.return_value = [
            {"nroOrden": 888853, "estado": "CONCRETADA"},
        ]
        self.env["account.payment.order"]._l10n_py_atlas_cron_poll_pending()
        self.assertEqual(line.atlas_error_mensaje, "CONCRETADA")

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_poll_leaves_line_pending_when_absent_from_the_response(self, mock_call):
        """consultar-pago only lists already-confirmed payments (bank's
        own documented behavior) -- a nroOrden missing from the response
        must stay pending, not be treated as an error."""
        line = self._pending_line(nro_orden=999999)
        mock_call.return_value = [
            {"nroOrden": 111111, "estado": "CONCRETADA"},
        ]
        self.env["account.payment.order"]._l10n_py_atlas_cron_poll_pending()
        self.assertFalse(line.atlas_error_mensaje)
