# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from unittest import mock

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account_payment_batch_oca.models.account_payment_order import (
    AccountPaymentOrder,
)

from ..models.account_payment_order import L10N_PY_SIPAP_BATCH_CODE


@tagged("post_install", "-at_install", "l10n_py")
class TestBatchFileDispatch(AccountTestInvoicingCommon):
    """Tests for the pluggable SIPAP batch-file exporter framework.

    This module implements no concrete bank layout: it only resolves,
    from ``res.bank.l10n_py_sipap_export_code``, which
    ``_l10n_py_generate_batch_file_<code>`` method (registered by an
    exporter module, e.g. ``l10n_py_account_batch_payment_iso20022``)
    should generate the file. These tests exercise only that dispatch
    mechanism: they never fabricate a real bank file format.
    """

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
                "acc_number": "COMPANY-DISPATCH-0001",
                "partner_id": cls.company.partner_id.id,
                "bank_id": cls.company_bank.id,
                "company_id": cls.company.id,
            }
        )
        cls.bank_journal.bank_account_id = cls.company_bank_account.id
        cls.sipap_method = (
            cls.env["account.payment.method"]
            .sudo()
            .search([("code", "=", L10N_PY_SIPAP_BATCH_CODE)], limit=1)
        )
        cls.method_line = cls.env["account.payment.method.line"].create(
            {
                "name": "SIPAP Batch File - Test",
                "company_id": cls.company.id,
                "journal_id": cls.bank_journal.id,
                "payment_method_id": cls.sipap_method.id,
                "selectable": True,
            }
        )

    def _create_order(self):
        return self.env["account.payment.order"].create(
            {
                "payment_type": "outbound",
                "payment_method_line_id": self.method_line.id,
            }
        )

    def test_payment_method_is_registered(self):
        """The 'SIPAP Batch File' payment method is installed by data file."""
        self.assertTrue(self.sipap_method)
        self.assertEqual(self.sipap_method.payment_type, "outbound")
        self.assertTrue(self.sipap_method.payment_order_ok)
        self.assertTrue(self.sipap_method.bank_account_required)

    def test_payment_method_selectable_on_a_bank_journal(self):
        """Regression test: the data record alone is not enough to make
        'l10n_py_sipap_batch' selectable in the UI. Odoo's
        account.journal only considers, for ANY journal, payment methods
        whose code is a key of
        account.payment.method._get_payment_method_information() (see
        account.journal._get_journals_payment_method_information). A
        method missing from that registry never appears in
        available_payment_method_ids, and therefore never appears in the
        'Add a line' search on a journal's Outgoing Payments tab -- even
        though the method itself, and its `account.payment.method.line`
        domain, look perfectly valid. This must be verified via
        `available_payment_method_ids`, not by creating the method line
        directly through the ORM (as the other tests in this file do),
        since direct ORM creation bypasses the search domain entirely and
        would not have caught this bug."""
        # Force recomputation: available_payment_method_ids is cached on
        # the (outbound|inbound)_payment_method_line_ids dependency, and
        # setUpClass already attached a SIPAP method line to this journal.
        other_bank_journal = self.env["account.journal"].create(
            {
                "name": "SIPAP availability check journal",
                "type": "bank",
                "company_id": self.company.id,
            }
        )
        self.assertIn(
            self.sipap_method,
            other_bank_journal.available_payment_method_ids,
            "l10n_py_sipap_batch must be registered in "
            "account.payment.method._get_payment_method_information(), "
            "otherwise it never becomes selectable on any journal in the UI.",
        )

    def test_missing_bank_on_company_account_raises_clear_error(self):
        """No bank on the company bank account -> explicit UserError."""
        order = self._create_order()
        self.assertTrue(order.company_partner_bank_id)
        order.company_partner_bank_id.bank_id = False
        with self.assertRaises(UserError):
            order._l10n_py_generate_batch_file()

    def test_missing_export_code_raises_clear_error(self):
        """Bank without l10n_py_sipap_export_code configured -> UserError."""
        order = self._create_order()
        bank = order.company_partner_bank_id.bank_id
        self.assertTrue(bank)
        bank.l10n_py_sipap_export_code = False
        with self.assertRaises(UserError):
            order._l10n_py_generate_batch_file()

    def test_unregistered_export_code_raises_clear_error(self):
        """A configured export code with no matching handler -> UserError."""
        order = self._create_order()
        bank = order.company_partner_bank_id.bank_id
        bank.l10n_py_sipap_export_code = "no_such_exporter_installed"
        with self.assertRaises(UserError):
            order._l10n_py_generate_batch_file()

    def test_dispatches_to_the_registered_handler(self):
        """When a matching '_l10n_py_generate_batch_file_<code>' handler is
        registered on account.payment.order, the framework calls exactly
        that handler -- this is the mechanism a real exporter module (e.g.
        the ISO 20022 one) relies on, tested here without depending on
        any concrete exporter module being installed."""
        order = self._create_order()
        bank = order.company_partner_bank_id.bank_id
        bank.l10n_py_sipap_export_code = "dummy_test_format"

        sentinel = object()
        with mock.patch.object(
            AccountPaymentOrder,
            "_l10n_py_generate_batch_file_dummy_test_format",
            create=True,
            return_value=sentinel,
        ) as handler:
            result = order._l10n_py_generate_batch_file()
        handler.assert_called_once()
        self.assertIs(result, sentinel)

    def test_dispatches_to_api_handler_when_export_mode_is_api(self):
        """When a bank's export_mode is 'api', the framework calls
        '_l10n_py_dispatch_batch_api_<code>' instead of
        '_l10n_py_generate_batch_file_<code>' -- this is the hook a
        direct-API exporter module (e.g. the Banco Atlas one) relies on."""
        order = self._create_order()
        bank = order.company_partner_bank_id.bank_id
        bank.l10n_py_sipap_export_code = "dummy_api_format"
        bank.l10n_py_sipap_export_mode = "api"

        sentinel = object()
        with mock.patch.object(
            AccountPaymentOrder,
            "_l10n_py_dispatch_batch_api_dummy_api_format",
            create=True,
            return_value=sentinel,
        ) as handler:
            result = order._l10n_py_generate_batch_file()
        handler.assert_called_once()
        self.assertIs(result, sentinel)

    def test_file_mode_is_the_default_and_unaffected(self):
        """Existing behavior (export_mode defaults to 'file') must be
        unchanged by this task -- regression guard."""
        order = self._create_order()
        bank = order.company_partner_bank_id.bank_id
        self.assertEqual(bank.l10n_py_sipap_export_mode, "file")

    def test_generate_payment_file_dispatches_for_sipap_method(self):
        """generate_payment_file() delegates to the SIPAP framework only
        when the order's payment method is the SIPAP batch method."""
        order = self._create_order()
        bank = order.company_partner_bank_id.bank_id
        bank.l10n_py_sipap_export_code = "dummy_test_format"

        with mock.patch.object(
            AccountPaymentOrder,
            "_l10n_py_generate_batch_file_dummy_test_format",
            create=True,
            return_value=(False, False),
        ) as handler:
            order.generate_payment_file()
        handler.assert_called_once()
