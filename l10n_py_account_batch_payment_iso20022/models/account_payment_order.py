# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import uuid

from lxml import etree

from odoo import _, fields, models
from odoo.exceptions import UserError

# Generic ISO 20022 Customer Credit Transfer Initiation schema. This is
# the version confirmed as currently correct (not pain.001.001.03, which
# an earlier, incorrect version of this spec had assumed).
L10N_PY_PAIN_NAMESPACE = "urn:iso:std:iso:20022:tech:xsd:pain.001.001.09"

# NOTE: whether any specific Paraguayan bank's home banking actually
# *accepts* this generic ISO 20022 file is NOT confirmed by this module.
# See the module README.


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def _l10n_py_generate_batch_file_iso20022(self):
        """Generate a generic ISO 20022 pain.001.001.09 batch file.

        Acceptance of this exact generic schema by any specific bank's
        home banking portal is NOT confirmed - see the module README.
        The SPI/LBTR categorization is computed from
        ``company_id.l10n_py_sipap_spi_lbtr_threshold``, which has no
        default value: it must be explicitly configured (the real cutoff
        value has to be confirmed with the BCP).
        """
        self.ensure_one()
        threshold = self.company_id.l10n_py_sipap_spi_lbtr_threshold
        if not threshold:
            raise UserError(
                _(
                    "No se puede generar el archivo ISO 20022: el umbral "
                    "SPI/LBTR de la empresa '%(company)s' no está "
                    "configurado (Contabilidad > Configuración > "
                    "Empresas). Este valor debe confirmarse con el Banco "
                    "Central del Paraguay antes de continuar: no se asume "
                    "ningún valor por defecto.",
                    company=self.company_id.display_name,
                )
            )
        if not self.payment_ids:
            raise UserError(
                _(
                    "No se puede generar el archivo ISO 20022: la orden "
                    "de pago '%(order)s' no tiene pagos confirmados "
                    "todavía.",
                    order=self.display_name,
                )
            )
        xml_root = self._l10n_py_iso20022_build_document(threshold)
        xml_bytes = etree.tostring(
            xml_root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
        )
        return (xml_bytes, "xml")

    def _l10n_py_iso20022_build_document(self, threshold):
        self.ensure_one()
        nsmap = {None: L10N_PY_PAIN_NAMESPACE}
        document = etree.Element("Document", nsmap=nsmap)
        cstmr = etree.SubElement(document, "CstmrCdtTrfInitn")
        self._l10n_py_iso20022_add_group_header(cstmr)
        # account_payment_order has no "lot" grouping (that concept only
        # existed in account_payment_batch_oca): one order already means
        # one journal + one requested execution date, so the whole order
        # maps to exactly one <PmtInf> block.
        self._l10n_py_iso20022_add_payment_info(cstmr, threshold)
        return document

    def _l10n_py_iso20022_add_group_header(self, cstmr):
        self.ensure_one()
        grp_hdr = etree.SubElement(cstmr, "GrpHdr")
        etree.SubElement(grp_hdr, "MsgId").text = self._l10n_py_iso20022_msg_id()
        etree.SubElement(grp_hdr, "CreDtTm").text = fields.Datetime.now().strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        etree.SubElement(grp_hdr, "NbOfTxs").text = str(len(self.payment_ids))
        etree.SubElement(grp_hdr, "CtrlSum").text = f"{self.total_company_currency:.2f}"
        initg_pty = etree.SubElement(grp_hdr, "InitgPty")
        etree.SubElement(initg_pty, "Nm").text = self.company_id.display_name[:70]

    def _l10n_py_iso20022_msg_id(self):
        self.ensure_one()
        return f"{self.name or 'SIPAP'}-{uuid.uuid4().hex[:12]}".replace(" ", "")[:35]

    def _l10n_py_iso20022_add_payment_info(self, cstmr, threshold):
        self.ensure_one()
        pmt_inf = etree.SubElement(cstmr, "PmtInf")
        etree.SubElement(pmt_inf, "PmtInfId").text = (self.name or "PMTINF")[:35]
        etree.SubElement(pmt_inf, "PmtMtd").text = "TRF"
        etree.SubElement(pmt_inf, "NbOfTxs").text = str(len(self.payment_ids))
        etree.SubElement(pmt_inf, "CtrlSum").text = f"{self.total_company_currency:.2f}"
        reqd_exctn_dt = etree.SubElement(pmt_inf, "ReqdExctnDt")
        # date_scheduled is optional on account.payment.order (only
        # validated -- not required -- when set); fall back to today,
        # same default the framework itself uses for "fixed" date orders
        # (see payment_mode_id_change()/_prepare_payment_line_vals()).
        execution_date = self.date_scheduled or fields.Date.context_today(self)
        etree.SubElement(reqd_exctn_dt, "Dt").text = fields.Date.to_string(
            execution_date
        )
        dbtr = etree.SubElement(pmt_inf, "Dbtr")
        etree.SubElement(dbtr, "Nm").text = self.company_id.display_name[:140]
        company_bank = self.company_partner_bank_id
        dbtr_acct = etree.SubElement(pmt_inf, "DbtrAcct")
        dbtr_acct_id = etree.SubElement(dbtr_acct, "Id")
        etree.SubElement(etree.SubElement(dbtr_acct_id, "Othr"), "Id").text = (
            company_bank.acc_number or ""
        )
        dbtr_agt = etree.SubElement(pmt_inf, "DbtrAgt")
        self._l10n_py_iso20022_add_fin_instn_id(dbtr_agt, company_bank.bank_id)
        for payment in self.payment_ids:
            self._l10n_py_iso20022_add_credit_transfer(pmt_inf, payment, threshold)

    def _l10n_py_iso20022_add_fin_instn_id(self, parent, bank):
        fin_instn_id = etree.SubElement(parent, "FinInstnId")
        if bank and bank.bic:
            etree.SubElement(fin_instn_id, "BICFI").text = bank.bic
        othr = etree.SubElement(fin_instn_id, "Othr")
        etree.SubElement(othr, "Id").text = (
            bank and bank.l10n_py_sipap_bank_code
        ) or "UNKNOWN"

    def _l10n_py_iso20022_add_credit_transfer(self, pmt_inf, payment, threshold):
        trf_tx_inf = etree.SubElement(pmt_inf, "CdtTrfTxInf")
        pmt_id = etree.SubElement(trf_tx_inf, "PmtId")
        etree.SubElement(pmt_id, "EndToEndId").text = (payment.name or "NOTPROVIDED")[
            :35
        ]
        pmt_tp_inf = etree.SubElement(trf_tx_inf, "PmtTpInf")
        ctgy_purp = etree.SubElement(pmt_tp_inf, "CtgyPurp")
        category = "LBTR" if payment.amount >= threshold else "SPI"
        etree.SubElement(ctgy_purp, "Cd").text = category
        amt = etree.SubElement(trf_tx_inf, "Amt")
        instd_amt = etree.SubElement(amt, "InstdAmt")
        instd_amt.set("Ccy", payment.currency_id.name or "PYG")
        instd_amt.text = f"{payment.amount:.2f}"
        cdtr_agt = etree.SubElement(trf_tx_inf, "CdtrAgt")
        self._l10n_py_iso20022_add_fin_instn_id(
            cdtr_agt, payment.partner_bank_id.bank_id
        )
        cdtr = etree.SubElement(trf_tx_inf, "Cdtr")
        etree.SubElement(cdtr, "Nm").text = (payment.partner_id.display_name or "")[
            :140
        ]
        cdtr_acct = etree.SubElement(trf_tx_inf, "CdtrAcct")
        cdtr_acct_id = etree.SubElement(cdtr_acct, "Id")
        alias_value = payment.partner_bank_id.l10n_py_cas_alias_value
        etree.SubElement(etree.SubElement(cdtr_acct_id, "Othr"), "Id").text = (
            alias_value or payment.partner_bank_id.acc_number or ""
        )
        remittance = payment.payment_reference or payment.memo
        if remittance:
            rmt_inf = etree.SubElement(trf_tx_inf, "RmtInf")
            etree.SubElement(rmt_inf, "Ustrd").text = remittance[:140]
