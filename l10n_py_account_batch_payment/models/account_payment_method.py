# l10n_py_account_batch_payment/models/account_payment_method.py

from odoo import api, models


class AccountPaymentMethod(models.Model):
    _inherit = "account.payment.method"

    @api.model
    def _get_payment_method_information(self):
        """Register ``l10n_py_sipap_batch`` in Odoo's payment method
        information registry.

        Without this override, ``account.journal._compute_available_payment_method_ids``
        never considers this method for ANY journal: it only looks at
        methods whose ``code`` is a key of this dict (see
        ``account.journal._get_journals_payment_method_information``).
        The XML data record alone (``data/account_payment_method.xml``)
        is not enough to make the method selectable in the UI, even
        though it exists and looks correctly configured.
        """
        res = super()._get_payment_method_information()
        res["l10n_py_sipap_batch"] = {
            "mode": "multi",
            "type": ("bank",),
        }
        return res
