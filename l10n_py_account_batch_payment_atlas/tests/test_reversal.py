# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from unittest import mock

from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install", "l10n_py")
class TestAtlasReversal(AccountTestInvoicingCommon):
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
        cls.company_bank_account = cls.env["res.partner.bank"].create(
            {
                "acc_number": "ATLAS-REV-0001",
                "partner_id": cls.company_data["company"].partner_id.id,
                "atlas_enabled": True,
                "atlas_numero_cuenta": "763797",
                "atlas_api_key": "test-key",
                "atlas_private_key_pem": "-----BEGIN PRIVATE KEY-----\n...",
            }
        )
        cls.company_data[
            "default_journal_bank"
        ].bank_account_id = cls.company_bank_account

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_reversal_calls_the_reversar_pago_endpoint(self, mock_call):
        mock_call.return_value = {"numeroOperacion": "765313"}
        journal = self.company_data["default_journal_bank"]
        method_line = self.env["account.payment.method.line"].search(
            [
                ("journal_id", "=", journal.id),
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
                    "journal_id": journal.id,
                    "payment_method_id": payment_method.id,
                }
            )
        order = self.env["account.payment.order"].create(
            {
                "payment_type": "outbound",
                "payment_method_line_id": method_line.id,
                "journal_id": journal.id,
            }
        )
        line = self.env["account.payment.line"].create(
            {
                "order_id": order.id,
                "partner_id": self.env["res.partner"].create({"name": "P"}).id,
                "amount_currency": 1000,
                "currency_id": self.env.ref("base.PYG", raise_if_not_found=False).id
                or self.env["res.currency"].create({"name": "PYG_TEST"}).id,
                "atlas_nro_orden": 765313,
                "atlas_estado": "sent",
                "atlas_error_mensaje": "Aprobado",
            }
        )
        line.action_atlas_reversar_pago()
        mock_call.assert_called_once_with(
            "POST",
            "/proveedores-atlas/v1.5.0/proveedores/763797/reversar-pago",
            body={"nroFactura": "765313", "observacion": mock.ANY},
        )
        # I3: reversal moves the lifecycle state and records its own
        # confirmation reference, WITHOUT clobbering the original
        # dispatch message (audit trail of the bank's per-attempt
        # reason for THIS line).
        self.assertEqual(line.atlas_estado, "reversed")
        self.assertEqual(line.atlas_reversal_reference, "765313")
        self.assertEqual(line.atlas_error_mensaje, "Aprobado")

    def _line_for_bill(self, ref):
        journal = self.company_data["default_journal_bank"]
        method_line = self.env["account.payment.method.line"].search(
            [
                ("journal_id", "=", journal.id),
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
                    "journal_id": journal.id,
                    "payment_method_id": payment_method.id,
                }
            )
        order = self.env["account.payment.order"].create(
            {
                "payment_type": "outbound",
                "payment_method_line_id": method_line.id,
                "journal_id": journal.id,
            }
        )
        partner = self.env["res.partner"].create({"name": "Proveedor Factura"})
        move = self.init_invoice("in_invoice", partner=partner, amounts=[1000])
        if ref is not None:
            move.ref = ref
        move.action_post()
        payable_line = move.line_ids.filtered(
            lambda line_item: line_item.account_id.account_type == "liability_payable"
        )
        pyg = self.env.ref("base.PYG", raise_if_not_found=False) or self.env[
            "res.currency"
        ].create({"name": "PYG_TEST"})
        return self.env["account.payment.line"].create(
            {
                "order_id": order.id,
                "partner_id": partner.id,
                "amount_currency": 1000,
                "currency_id": pyg.id,
                "move_line_id": payable_line.id,
                "atlas_nro_orden": 999001,
            }
        ), move

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_reversal_uses_vendor_bill_reference_as_nro_factura(self, mock_call):
        mock_call.return_value = {"numeroOperacion": "999001"}
        line, move = self._line_for_bill(ref="FACT-PROV-4521")
        line.action_atlas_reversar_pago()
        _, kwargs = mock_call.call_args
        self.assertEqual(kwargs["body"]["nroFactura"], "FACT-PROV-4521")

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_reversal_falls_back_to_move_name_when_ref_is_empty(self, mock_call):
        mock_call.return_value = {"numeroOperacion": "999002"}
        line, move = self._line_for_bill(ref=None)
        line.action_atlas_reversar_pago()
        _, kwargs = mock_call.call_args
        self.assertEqual(kwargs["body"]["nroFactura"], move.name)
        self.assertNotEqual(move.name, "999001")
