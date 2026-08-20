1. Configure the company's own bank account (``res.partner.bank``) as a
   Banco Atlas account (see ``l10n_py_account_payment_atlas``).
2. On the relevant ``res.bank`` (the beneficiary's OR the company's own
   bank -- whichever this payment method targets), set "Formato de
   Exportación SIPAP" to ``atlas`` and "Modo de Exportación SIPAP" to
   "API directa".
3. Add the "SIPAP Batch File" payment method to the relevant bank journal
   (see ``l10n_py_account_batch_payment``'s own CONFIGURE.md for that
   step -- unchanged by this module).
