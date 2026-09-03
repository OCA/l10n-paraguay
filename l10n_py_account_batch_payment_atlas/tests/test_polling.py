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
                        cls.env.ref("account_payment_order.group_account_payment").id
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

        # account_payment_order (the OCA batch-payment framework this
        # module runs on) groups orders under an account.payment.mode,
        # not a payment_method_line_id on the order itself.
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
        cls.payment_mode = cls.env["account.payment.mode"].create(
            {
                "name": "Test Outbound Mode",
                "company_id": cls.company_data["company"].id,
                "bank_account_link": "fixed",
                "fixed_journal_id": cls.bank_journal.id,
                "payment_method_id": payment_method.id,
            }
        )

    def _pending_line(self, nro_orden=888853, atlas_estado=False):
        order = self.env["account.payment.order"].create(
            {
                "payment_mode_id": self.payment_mode.id,
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
                "atlas_estado": atlas_estado,
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
        self.assertEqual(line.atlas_estado, "confirmed")
        self.assertEqual(line.atlas_error_mensaje, "CONCRETADA")
        # C3: same product prefix as every other Atlas API call.
        args, _kwargs = mock_call.call_args
        self.assertEqual(
            args[1], "/proveedores-atlas/v1.5.0/proveedores/763797/consultar-pago"
        )

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
        self.assertFalse(line.atlas_estado)
        self.assertFalse(line.atlas_error_mensaje)

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_poll_finds_a_line_already_dispatched_with_sent_status(self, mock_call):
        """I3 regression: a real post-dispatch line already carries a
        non-empty atlas_error_mensaje (e.g. 'Aprobado') right after
        _l10n_py_dispatch_batch_api_atlas() -- the OLD domain
        ("atlas_error_mensaje", "=", False) would never match it, making
        the cron permanently inert. The new domain keys on atlas_estado
        instead, so a line dispatched with atlas_estado='sent' (and
        atlas_error_mensaje already set to 'Aprobado') must still be
        picked up."""
        line = self._pending_line(nro_orden=767348, atlas_estado="sent")
        line.atlas_error_mensaje = "Aprobado"
        mock_call.return_value = [
            {"nroOrden": 767348, "estado": "CONCRETADA"},
        ]
        self.env["account.payment.order"]._l10n_py_atlas_cron_poll_pending()
        self.assertEqual(line.atlas_estado, "confirmed")

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_poll_skips_lines_already_in_a_terminal_state(self, mock_call):
        """A line already 'confirmed'/'rejected'/'reversed' must not be
        included in the search at all -- regression guard for the new
        domain."""
        self._pending_line(nro_orden=555555, atlas_estado="confirmed")
        mock_call.return_value = []
        self.env["account.payment.order"]._l10n_py_atlas_cron_poll_pending()
        mock_call.assert_not_called()
