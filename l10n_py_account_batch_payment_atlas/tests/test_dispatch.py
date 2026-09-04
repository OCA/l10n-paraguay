# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from unittest import mock

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_py_account_batch_payment.models.account_payment_order import (
    L10N_PY_SIPAP_BATCH_CODE,
)


@tagged("post_install", "-at_install", "l10n_py")
class TestAtlasDispatch(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.write(
            {
                "groups_id": [
                    Command.link(
                        cls.env.ref("account_payment_order.group_account_payment").id
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
        payment_mode = self.env["account.payment.mode"].create(
            {
                "name": "Test Outbound Mode",
                "company_id": self.bank_journal.company_id.id,
                "bank_account_link": "fixed",
                "fixed_journal_id": self.bank_journal.id,
                "payment_method_id": payment_method.id,
            }
        )
        order = self.env["account.payment.order"].create(
            {
                "payment_mode_id": payment_mode.id,
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
        self.assertEqual(line.atlas_estado, "sent")

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
        args, kwargs = mock_call.call_args
        sent_body = kwargs["body"]
        self.assertIn("beneficiarioProveedorList", sent_body)
        self.assertEqual(len(sent_body["beneficiarioProveedorList"]), 1)
        self.assertEqual(sent_body["beneficiarioProveedorList"][0]["monto"], 81000)
        # C3: the Pago a Proveedores product prefix must be present, like
        # every other Atlas API call in this codebase (e.g. "cuentas-atlas
        # /v1.5.0" for saldo/alias) -- a bare "/proveedores/..." path 404s
        # against the real bank.
        self.assertEqual(
            args[1],
            "/proveedores-atlas/v1.5.0/proveedores/763797/registrar-pago",
        )

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_dispatch_returns_the_no_file_produced_tuple_shape(self, mock_call):
        """C1: the dispatch method must return the same (False, False)
        'no file produced' tuple the base framework's generate_payment_file()
        expects everywhere else -- returning True broke the unpack in
        account_payment_order.open2generated() AFTER the real HTTP
        POST to the bank had already succeeded."""
        order = self._order_with_one_line()
        mock_call.return_value = {
            "transaccion": {"token": "abc123", "infoAdicional": {"beneficiarios": []}}
        }
        result = order._l10n_py_dispatch_batch_api_atlas()
        self.assertEqual(result, (False, False))

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_dispatch_refuses_to_redispatch_an_already_sent_order(self, mock_call):
        """Idempotency guard: once a line carries an atlas_nro_orden, this
        batch has already been sent to the bank once -- redispatching
        risks a duplicate payment."""
        order = self._order_with_one_line()
        mock_call.return_value = {
            "transaccion": {
                "infoAdicional": {
                    "beneficiarios": [
                        {
                            "nroRegistro": 1,
                            "nroOrden": 767348,
                            "error": {"codigo": "0", "mensaje": "Aprobado"},
                        }
                    ]
                }
            }
        }
        order._l10n_py_dispatch_batch_api_atlas()
        self.assertEqual(mock_call.call_count, 1)
        with self.assertRaises(UserError):
            order._l10n_py_dispatch_batch_api_atlas()
        # The bank must NOT be called a second time.
        self.assertEqual(mock_call.call_count, 1)

    def _order_with_sipap_atlas_method(self, amount=81000):
        """Build an order through the REAL production wiring: SIPAP Batch
        File payment method + res.bank configured for API/atlas export --
        this is what account_payment_order.open2generated() actually
        sees, unlike the other tests in this file which call
        _l10n_py_dispatch_batch_api_atlas() directly and never exercise
        the generate_payment_file()/open2generated() unpack."""
        bank = self.company_bank
        bank.l10n_py_sipap_export_code = "atlas"
        bank.l10n_py_sipap_export_mode = "api"
        sipap_method = (
            self.env["account.payment.method"]
            .sudo()
            .search([("code", "=", L10N_PY_SIPAP_BATCH_CODE)], limit=1)
        )
        payment_mode = self.env["account.payment.mode"].create(
            {
                "name": "SIPAP Batch File - Atlas Test Mode",
                "company_id": self.company.id,
                "bank_account_link": "fixed",
                "fixed_journal_id": self.bank_journal.id,
                "payment_method_id": sipap_method.id,
            }
        )
        order = self.env["account.payment.order"].create(
            {
                "payment_mode_id": payment_mode.id,
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
    def test_open2generated_completes_without_typeerror_through_real_dispatch(
        self, mock_call
    ):
        """C1 regression: the REAL caller is
        account_payment_order.open2generated(), which unpacks
        generate_payment_file() as (payment_file_bytes, filename_ext).
        Before this fix, _l10n_py_dispatch_batch_api_atlas() returned
        True, so this unpack raised a TypeError AFTER the (mocked) HTTP
        POST to the bank had already 'succeeded' -- and the transaction
        then rolled back, discarding the bank's response and leaving the
        order looking unsent while the bank had already processed it."""
        order = self._order_with_sipap_atlas_method()
        mock_call.return_value = {
            "transaccion": {
                "infoAdicional": {
                    "beneficiarios": [
                        {
                            "nroRegistro": 1,
                            "nroOrden": 767999,
                            "error": {"codigo": "0", "mensaje": "Aprobado"},
                        }
                    ]
                }
            }
        }
        # Must not raise TypeError.
        order.open2generated()
        self.assertEqual(order.state, "generated")
        line = order.payment_line_ids[0]
        self.assertEqual(line.atlas_nro_orden, 767999)
        self.assertEqual(line.atlas_estado, "sent")
