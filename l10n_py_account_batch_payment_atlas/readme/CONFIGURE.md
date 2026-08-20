1. Configure the company's own bank account (``res.partner.bank``) as a
   Banco Atlas account (see ``l10n_py_account_payment_atlas``).
2. On the relevant ``res.bank`` (the beneficiary's OR the company's own
   bank -- whichever this payment method targets), set "Formato de
   Exportación SIPAP" to ``atlas`` and "Modo de Exportación SIPAP" to
   "API directa".
3. Add the "SIPAP Batch File" payment method to the relevant bank journal
   (see ``l10n_py_account_batch_payment``'s own CONFIGURE.md for that
   step -- unchanged by this module).

Known limitation: the Atlas credential fields (API Key, private key PEM,
auth token) are restricted to the Accounting Manager group
(``account.group_account_manager``). A user in a lesser group (e.g.
``account.group_account_invoice``) who triggers dispatch, reversal, or
the polling cron may hit an ``AccessError`` reading those fields. This is
a known limitation, not a bug fixed in this module: granting broader
access via ``sudo()`` is a security-relevant decision left for a
deliberate follow-up, not bundled into this fix wave.
