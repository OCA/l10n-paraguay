# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from datetime import datetime, timedelta

from lxml import etree

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_py_account_batch_payment.models.account_payment_order import (
    L10N_PY_SIPAP_BATCH_CODE,
)

PAIN_NS = {"p": "urn:iso:std:iso:20022:tech:xsd:pain.001.001.09"}


@tagged("post_install", "-at_install", "l10n_py")
class TestIso20022Export(AccountTestInvoicingCommon):
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
        cls.company.l10n_py_sipap_spi_lbtr_threshold = 5_000_000

        cls.company_bank = cls.env["res.bank"].create(
            {"name": "Banco de la Empresa", "bic": "COMPPYPY"}
        )
        cls.company_bank.l10n_py_sipap_bank_code = "001"
        cls.company_bank.l10n_py_sipap_export_code = "iso20022"
        cls.company_bank_account = cls.env["res.partner.bank"].create(
            {
                "acc_number": "COMPANY-ACC-0001",
                "partner_id": cls.company.partner_id.id,
                "bank_id": cls.company_bank.id,
                "company_id": cls.company.id,
            }
        )
        cls.bank_journal = cls.company_data["default_journal_bank"]
        cls.bank_journal.bank_account_id = cls.company_bank_account.id

        cls.beneficiary_bank = cls.env["res.bank"].create(
            {"name": "Banco del Proveedor", "bic": "PROVPYPY"}
        )
        cls.beneficiary_bank.l10n_py_sipap_bank_code = "002"
        cls.partner = cls.env["res.partner"].create({"name": "Proveedor SIPAP"})
        cls.partner_bank = cls.env["res.partner.bank"].create(
            {
                "acc_number": "SUPPLIER-ACC-0001",
                "partner_id": cls.partner.id,
                "bank_id": cls.beneficiary_bank.id,
                "allow_out_payment": True,
            }
        )

        cls.sipap_method = (
            cls.env["account.payment.method"]
            .sudo()
            .search([("code", "=", L10N_PY_SIPAP_BATCH_CODE)], limit=1)
        )
        # account_payment_order (the OCA batch-payment framework this
        # module runs on) groups orders under an account.payment.mode,
        # not a payment_method_line_id on the order/invoice.
        cls.payment_mode = cls.env["account.payment.mode"].create(
            {
                "name": "SIPAP Batch File - Test Mode",
                "company_id": cls.company.id,
                "bank_account_link": "fixed",
                "fixed_journal_id": cls.bank_journal.id,
                "payment_method_id": cls.sipap_method.id,
                "group_lines": False,
            }
        )

        # This module tests SIPAP/ISO20022 batch dispatch only -- it has
        # no dependency on l10n_py_account/l10n_py_edi_base and no
        # opinion on LATAM document-type numbering. But when this module
        # is installed alongside l10n_py_account in the same database
        # (as OCA CI does for the whole repo), the ambient test
        # company's chart template is guessed from its country_id, and
        # if that resolves to Paraguay, l10n_py_account's own
        # _localization_use_documents() override turns
        # "l10n_latam_use_documents" on for this company's purchase
        # journal -- which then requires a document type/number this
        # test never sets, breaking action_post() with an unrelated
        # ValidationError. Force it off explicitly so this test's result
        # never depends on which other l10n_py_* modules happen to be
        # installed in the same database.
        cls.company_data["default_journal_purchase"].l10n_latam_use_documents = False
        cls.invoice = cls.env["account.move"].create(
            {
                "partner_id": cls.partner.id,
                "move_type": "in_invoice",
                "ref": "SIPAP-INV-001",
                "invoice_date": fields.Date.today(),
                "payment_mode_id": cls.payment_mode.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "quantity": 1.0,
                            "price_unit": 1_000_000.0,
                            "name": "Servicio SIPAP",
                            "account_id": cls.company_data[
                                "default_account_expense"
                            ].id,
                        },
                    )
                ],
            }
        )
        cls.invoice.action_post()
        cls.invoice.partner_bank_id = cls.partner_bank

    def _build_and_confirm_order(self):
        order = self.env["account.payment.order"].create(
            {
                "payment_mode_id": self.payment_mode.id,
            }
        )
        line_create = (
            self.env["account.payment.line.create"]
            .with_context(active_model="account.payment.order", active_id=order.id)
            .create(
                {"date_type": "move", "filter_date": datetime.now() + timedelta(days=1)}
            )
        )
        line_create.payment_mode = "any"
        line_create.populate()
        line_create.create_payment_lines()
        order.draft2open()
        return order

    def test_missing_threshold_raises_clear_error(self):
        self.company.l10n_py_sipap_spi_lbtr_threshold = 0
        order = self._build_and_confirm_order()
        with self.assertRaises(UserError):
            order.generate_payment_file()

    def test_generates_valid_pain_001_001_09_structure(self):
        order = self._build_and_confirm_order()
        xml_bytes, filename = order.generate_payment_file()
        # account_payment_order's own contract is (file, FULL filename),
        # not a bare extension -- a literal "xml" attachment name was the
        # bug this test used to reinforce instead of catch.
        self.assertEqual(filename, f"{order.name}.xml")
        root = etree.fromstring(xml_bytes)
        self.assertEqual(etree.QName(root).localname, "Document")
        self.assertEqual(root.tag, "{{{}}}Document".format(PAIN_NS["p"]))

        grp_hdr = root.find("p:CstmrCdtTrfInitn/p:GrpHdr", PAIN_NS)
        self.assertIsNotNone(grp_hdr)
        self.assertEqual(grp_hdr.findtext("p:NbOfTxs", namespaces=PAIN_NS), "1")
        self.assertEqual(
            grp_hdr.findtext("p:CtrlSum", namespaces=PAIN_NS), "1000000.00"
        )

        pmt_inf_list = root.findall("p:CstmrCdtTrfInitn/p:PmtInf", PAIN_NS)
        self.assertEqual(len(pmt_inf_list), 1)
        pmt_inf = pmt_inf_list[0]
        self.assertEqual(pmt_inf.findtext("p:PmtMtd", namespaces=PAIN_NS), "TRF")

        tx = pmt_inf.find("p:CdtTrfTxInf", PAIN_NS)
        self.assertIsNotNone(tx)
        amt = tx.find("p:Amt/p:InstdAmt", PAIN_NS)
        self.assertEqual(amt.text, "1000000.00")
        self.assertEqual(amt.get("Ccy"), self.company.currency_id.name)

        # 1,000,000 < configured threshold (5,000,000) => SPI
        category = tx.findtext("p:PmtTpInf/p:CtgyPurp/p:Cd", namespaces=PAIN_NS)
        self.assertEqual(category, "SPI")

        cdtr_agt_id = tx.findtext(
            "p:CdtrAgt/p:FinInstnId/p:Othr/p:Id", namespaces=PAIN_NS
        )
        self.assertEqual(cdtr_agt_id, "002")

    def test_lbtr_category_above_threshold(self):
        self.company.l10n_py_sipap_spi_lbtr_threshold = 500_000
        order = self._build_and_confirm_order()
        xml_bytes, _ext = order.generate_payment_file()
        root = etree.fromstring(xml_bytes)
        category = root.findtext(
            "p:CstmrCdtTrfInitn/p:PmtInf/p:CdtTrfTxInf/p:PmtTpInf/p:CtgyPurp/p:Cd",
            namespaces=PAIN_NS,
        )
        self.assertEqual(category, "LBTR")
