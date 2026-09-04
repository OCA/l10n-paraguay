# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import _, models
from odoo.exceptions import UserError

# Technical code of the SIPAP batch payment method, registered as a
# ``account.payment.method`` data record (see
# ``data/account_payment_method.xml``), following the same pattern used
# by every OCA payment-format module built on top of
# ``account_payment_order`` (e.g. ``account_banking_sepa_credit_transfer``).
L10N_PY_SIPAP_BATCH_CODE = "l10n_py_sipap_batch"


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def generate_payment_file(self):
        """Dispatch SIPAP batch file generation, delegate everything else.

        This module never generates a concrete file by itself: it only
        resolves, per company bank account, which exporter module should
        do it (see ``_l10n_py_generate_batch_file``). A concrete exporter
        (for example ``l10n_py_account_batch_payment_iso20022``) is what
        actually implements a ``_l10n_py_generate_batch_file_<code>``
        method.
        """
        self.ensure_one()
        if self.payment_method_id.code != L10N_PY_SIPAP_BATCH_CODE:
            return super().generate_payment_file()
        return self._l10n_py_generate_batch_file()

    def _l10n_py_generate_batch_file(self):
        """Resolve and call the SIPAP exporter for this order's bank.

        The exporter is chosen by the ``l10n_py_sipap_export_code`` set on
        the ``res.bank`` of the company's own bank account (the account
        set on this order's ``journal_id``) — it is *that* bank's home
        banking portal that will receive and interpret the file, so the
        export layout depends on it, not on the beneficiaries' banks.
        """
        self.ensure_one()
        company_bank_account = self.company_partner_bank_id
        if not company_bank_account or not company_bank_account.bank_id:
            raise UserError(
                _(
                    "No se puede generar el archivo de lote SIPAP: la "
                    "cuenta bancaria de la empresa configurada en el "
                    "diario '%(journal)s' no tiene un banco (res.bank) "
                    "asociado.",
                    journal=self.journal_id.display_name,
                )
            )
        export_code = company_bank_account.bank_id.l10n_py_sipap_export_code
        if not export_code:
            raise UserError(
                _(
                    "No se puede generar el archivo de lote SIPAP: el "
                    "banco '%(bank)s' no tiene un formato de exportación "
                    "SIPAP configurado (campo 'Formato de Exportación "
                    "SIPAP' en el banco). Configúrelo o instale el módulo "
                    "exportador correspondiente antes de continuar.",
                    bank=company_bank_account.bank_id.display_name,
                )
            )
        export_mode = company_bank_account.bank_id.l10n_py_sipap_export_mode
        handler_prefix = (
            "_l10n_py_dispatch_batch_api_"
            if export_mode == "api"
            else "_l10n_py_generate_batch_file_"
        )
        handler_name = f"{handler_prefix}{export_code}"
        handler = getattr(self, handler_name, None)
        if handler is None:
            raise UserError(
                _(
                    "No se puede generar el archivo de lote SIPAP: no hay "
                    "ningún exportador instalado para el formato "
                    "'%(export_code)s' configurado en el banco "
                    "'%(bank)s'. Instale el módulo exportador "
                    "correspondiente (por ejemplo "
                    "'l10n_py_account_batch_payment_iso20022' para el "
                    "formato 'iso20022').",
                    export_code=export_code,
                    bank=company_bank_account.bank_id.display_name,
                )
            )
        return handler()
