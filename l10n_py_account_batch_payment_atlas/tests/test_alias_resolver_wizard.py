# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from unittest import mock

from psycopg2.errors import UniqueViolation

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install", "l10n_py")
class TestAliasResolverWizard(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.write(
            {
                "groups_id": [
                    Command.link(cls.env.ref("account.group_account_manager").id)
                ]
            }
        )
        cls.company = cls.company_data["company"]
        cls.company_bank = cls.env["res.bank"].create({"name": "Test Company Bank"})
        cls.company_bank_account = cls.env["res.partner.bank"].create(
            {
                "acc_number": "ATLAS-RESOLVER-0001",
                "partner_id": cls.company.partner_id.id,
                "bank_id": cls.company_bank.id,
                "company_id": cls.company.id,
                "atlas_enabled": True,
                "atlas_numero_cuenta": "763797",
                "atlas_api_key": "test-key",
                "atlas_private_key_pem": "-----BEGIN PRIVATE KEY-----\n...",
            }
        )
        cls.supplier = cls.env["res.partner"].create({"name": "Proveedor Alias"})

    def _new_wizard(self, **overrides):
        vals = {
            "company_id": self.company.id,
            "company_bank_account_id": self.company_bank_account.id,
            "partner_id": self.supplier.id,
            "alias_tipo": "phone",
            "alias_valor": "0981123456",
        }
        vals.update(overrides)
        return self.env["l10n_py.atlas.alias.resolver"].create(vals)

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_action_buscar_success_fills_resolved_fields(self, mock_call):
        mock_call.return_value = {
            "nroCuenta": "0011223344",
            "denominacion": "Proveedor Alias S.A.",
        }
        wizard = self._new_wizard()
        wizard.action_buscar()
        self.assertEqual(wizard.state, "resolved")
        self.assertEqual(wizard.resolved_nro_cuenta, "0011223344")
        self.assertEqual(wizard.resolved_denominacion, "Proveedor Alias S.A.")
        # tipo mapping: "phone" -> "MOBILE" per the bank's own spec.
        args, kwargs = mock_call.call_args
        self.assertIn("tipo=MOBILE", args[1])

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_action_buscar_without_nro_cuenta_raises_and_stays_draft(self, mock_call):
        mock_call.return_value = {"denominacion": "Proveedor Alias S.A."}
        wizard = self._new_wizard()
        with self.assertRaises(UserError):
            wizard.action_buscar()
        self.assertEqual(wizard.state, "draft")
        self.assertFalse(wizard.resolved_nro_cuenta)

    def test_action_buscar_with_blank_alias_raises_without_calling_api(self):
        wizard = self._new_wizard(alias_valor="   ")
        with mock.patch(
            "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
            "AtlasApiClient.call"
        ) as mock_call:
            with self.assertRaises(UserError):
                wizard.action_buscar()
            mock_call.assert_not_called()

    def test_action_confirmar_before_resolved_raises(self):
        wizard = self._new_wizard()
        with self.assertRaises(UserError):
            wizard.action_confirmar()

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_action_confirmar_creates_partner_bank(self, mock_call):
        mock_call.return_value = {
            "nroCuenta": "0011223344",
            "denominacion": "Proveedor Alias S.A.",
        }
        wizard = self._new_wizard()
        wizard.action_buscar()
        result = wizard.action_confirmar()
        self.assertEqual(result["res_model"], "res.partner.bank")
        new_bank = self.env["res.partner.bank"].browse(result["res_id"])
        self.assertEqual(new_bank.acc_number, "0011223344")
        self.assertEqual(new_bank.partner_id, self.supplier)
        self.assertEqual(new_bank.l10n_py_cas_alias_type, "phone")
        self.assertEqual(new_bank.l10n_py_cas_alias_value, "0981123456")

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_action_confirmar_reuses_existing_account_instead_of_duplicating(
        self, mock_call
    ):
        """If a res.partner.bank with the same resolved account number
        already exists for this partner, confirming must open it
        instead of creating a duplicate (which would otherwise crash
        with a raw IntegrityError on the core's
        unique(sanitized_acc_number, partner_id) constraint)."""
        existing = self.env["res.partner.bank"].create(
            {
                "acc_number": "0011223344",
                "partner_id": self.supplier.id,
            }
        )
        mock_call.return_value = {
            "nroCuenta": "0011223344",
            "denominacion": "Proveedor Alias S.A.",
        }
        wizard = self._new_wizard()
        wizard.action_buscar()
        banks_before = self.env["res.partner.bank"].search_count(
            [("partner_id", "=", self.supplier.id)]
        )
        result = wizard.action_confirmar()
        banks_after = self.env["res.partner.bank"].search_count(
            [("partner_id", "=", self.supplier.id)]
        )
        self.assertEqual(banks_before, banks_after)
        self.assertEqual(result["res_id"], existing.id)

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_action_confirmar_persists_normalized_alias_not_raw_input(self, mock_call):
        """The value persisted to res.partner.bank must be the
        stripped/normalized alias that was actually validated against
        the bank in action_buscar, not the raw (possibly padded)
        ``alias_valor`` the user typed."""
        mock_call.return_value = {
            "nroCuenta": "0011223344",
            "denominacion": "Proveedor Alias S.A.",
        }
        wizard = self._new_wizard(alias_valor="  0981123456  ")
        wizard.action_buscar()
        self.assertEqual(wizard.resolved_alias_valor, "0981123456")
        result = wizard.action_confirmar()
        new_bank = self.env["res.partner.bank"].browse(result["res_id"])
        self.assertEqual(new_bank.l10n_py_cas_alias_value, "0981123456")

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_action_confirmar_handles_concurrent_create_race(self, mock_call):
        """A ``UniqueViolation`` raised by the core's own
        ``unique(sanitized_acc_number, partner_id)`` constraint --
        simulating a second, near-simultaneous confirmation winning the
        race to create() first -- must be handled the same way as
        finding the record via the up-front search: open it, never let
        a raw IntegrityError reach the user."""
        mock_call.return_value = {
            "nroCuenta": "0011223344",
            "denominacion": "Proveedor Alias S.A.",
        }
        wizard = self._new_wizard()
        wizard.action_buscar()

        # Simulate the "other" transaction that already committed its
        # own row for this same (partner_id, sanitized_acc_number) pair
        # in the race window between this wizard's up-front search and
        # its create() call.
        winner = self.env["res.partner.bank"].create(
            {"acc_number": "0011223344", "partner_id": self.supplier.id}
        )

        def _raise_unique_violation(*args, **kwargs):
            raise UniqueViolation("duplicate key value violates unique constraint")

        with mock.patch.object(
            type(self.env["res.partner.bank"]), "create", _raise_unique_violation
        ):
            result = wizard.action_confirmar()
        self.assertEqual(
            self.env["res.partner.bank"].search_count(
                [
                    ("partner_id", "=", self.supplier.id),
                    ("sanitized_acc_number", "=", "0011223344"),
                ]
            ),
            1,
        )
        self.assertEqual(result["res_id"], winner.id)


@tagged("post_install", "-at_install", "l10n_py")
class TestDispatchNoAliasRegression(AccountTestInvoicingCommon):
    """Non-regression: an earlier attempt at resolving a CAS alias
    inline during batch dispatch (``_l10n_py_resolver_alias_atlas``,
    called from ``_l10n_py_dispatch_batch_api_atlas``) was reverted
    because it was dead code -- ``res.partner.bank.acc_number`` is
    required in Odoo's own core, so a beneficiary bank account without
    an account number can never be persisted, and that branch could
    never be reached. Alias resolution now lives only in the
    ``l10n_py.atlas.alias.resolver`` wizard (see
    ``TestAliasResolverWizard`` above), never in the dispatch path."""

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
                "acc_number": "ATLAS-NOREG-0001",
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

    def test_dispatch_method_has_no_alias_resolution_helper(self):
        """The dead-code helper must be gone entirely, not just unused."""
        self.assertFalse(
            hasattr(self.env["account.payment.order"], "_l10n_py_resolver_alias_atlas")
        )

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_dispatch_uses_acc_number_directly_without_calling_consultar_alias(
        self, mock_call
    ):
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
            {"payment_mode_id": payment_mode.id}
        )
        partner_bank = self.env["res.partner.bank"].create(
            {
                "acc_number": "555666",
                "partner_id": self.env["res.partner"]
                .create({"name": "Proveedor Directo"})
                .id,
            }
        )
        self.env["account.payment.line"].create(
            {
                "order_id": order.id,
                "partner_id": partner_bank.partner_id.id,
                "partner_bank_id": partner_bank.id,
                "amount_currency": 12345,
                "currency_id": self.env.ref("base.PYG", raise_if_not_found=False).id
                or self.env["res.currency"].create({"name": "PYG_TEST"}).id,
            }
        )
        mock_call.return_value = {
            "transaccion": {"token": "abc123", "infoAdicional": {"beneficiarios": []}}
        }
        order._l10n_py_dispatch_batch_api_atlas()
        args, kwargs = mock_call.call_args
        sent_body = kwargs["body"]
        beneficiario = sent_body["beneficiarioProveedorList"][0]
        self.assertEqual(beneficiario["nroCuentaCredito"], "555666")
        # Only one call to AtlasApiClient.call ever happens: the batch
        # dispatch itself. No separate consultar_alias (also routed
        # through .call()) is ever triggered from this path.
        self.assertEqual(mock_call.call_count, 1)
        self.assertEqual(
            args[1],
            "/proveedores-atlas/v1.5.0/proveedores/763797/registrar-pago",
        )
