# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from unittest import mock

from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install", "l10n_py")
class TestAtlasDispatch(AccountTestInvoicingCommon):
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
        cls.bank_journal = cls.company_data["default_journal_bank"]
        cls.company_bank = cls.env["res.bank"].create({"name": "Test Company Bank"})
        cls.company_bank_account = cls.env["res.partner.bank"].create(
            {
                "acc_number": "ATLAS-DISPATCH-0001",
                "partner_id": cls.company.partner_id.id,
                "bank_id": cls.company_bank.id,
                "company_id": cls.company.id,
                "atlas_enabled": True,
                "atlas_numero_cuenta": "763797",
                "atlas_api_key": "test-key",
                "atlas_private_key_pem": "-----BEGIN PRIVATE KEY-----\n...",
            }
        )
        cls.bank_journal.bank_account_id = cls.company_bank_account.id

    def _order_with_one_line(self, amount=81000):
        method_line = self.env["account.payment.method.line"].search(
            [
                ("journal_id", "=", self.bank_journal.id),
                ("payment_method_id.payment_type", "=", "outbound"),
            ],
            limit=1,
        )
        if not method_line:
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
                    "journal_id": self.bank_journal.id,
                    "payment_method_id": payment_method.id,
                }
            )
        order = self.env["account.payment.order"].create(
            {
                "payment_type": "outbound",
                "payment_method_line_id": method_line.id,
                "journal_id": self.bank_journal.id,
            }
        )
        partner_bank = self.env["res.partner.bank"].create(
            {
                "acc_number": "987654",
                "partner_id": self.env["res.partner"]
                .create({"name": "Proveedor Atlas"})
                .id,
            }
        )
        self.env["account.payment.line"].create(
            {
                "order_id": order.id,
                "partner_id": partner_bank.partner_id.id,
                "partner_bank_id": partner_bank.id,
                "amount_currency": amount,
                "currency_id": self.env.ref("base.PYG", raise_if_not_found=False).id
                or self.env["res.currency"].create({"name": "PYG_TEST"}).id,
            }
        )
        return order

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_dispatch_marks_all_lines_sent_on_full_approval(self, mock_call):
        order = self._order_with_one_line()
        mock_call.return_value = {
            "transaccion": {
                "token": "abc123",
                "infoAdicional": {
                    "beneficiarios": [
                        {
                            "nroRegistro": 1,
                            "nroOrden": 767348,
                            "error": {"codigo": "0", "mensaje": "Aprobado"},
                        }
                    ]
                },
            }
        }
        order._l10n_py_dispatch_batch_api_atlas()
        line = order.payment_line_ids[0]
        self.assertEqual(line.atlas_error_codigo, "0")
        self.assertEqual(line.atlas_nro_orden, 767348)

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_dispatch_sends_the_batch_payload_shape(self, mock_call):
        order = self._order_with_one_line(amount=81000)
        mock_call.return_value = {
            "transaccion": {"token": "abc123", "infoAdicional": {"beneficiarios": []}}
        }
        order._l10n_py_dispatch_batch_api_atlas()
        # AtlasApiClient.call() is always invoked as call(method, path,
        # body=...) -- body is a keyword arg, never positional.
        _, kwargs = mock_call.call_args
        sent_body = kwargs["body"]
        self.assertIn("beneficiarioProveedorList", sent_body)
        self.assertEqual(len(sent_body["beneficiarioProveedorList"]), 1)
        self.assertEqual(sent_body["beneficiarioProveedorList"][0]["monto"], 81000)
