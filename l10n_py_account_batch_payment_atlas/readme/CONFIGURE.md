1. Configure the company's own bank account (``res.partner.bank``) as a
   Banco Atlas account (see ``l10n_py_account_payment_atlas``).
2. On the relevant ``res.bank`` (the beneficiary's OR the company's own
   bank -- whichever this payment method targets), set "Formato de
   Exportación SIPAP" to ``atlas`` and "Modo de Exportación SIPAP" to
   "API directa".
3. Add the "SIPAP Batch File" payment method to the relevant bank journal
   (see ``l10n_py_account_batch_payment``'s own CONFIGURE.md for that
   step -- unchanged by this module).
4. Mark the newly-added "SIPAP Batch File" line as **Selectable**. This is
   a property of the underlying ``account_payment_batch_oca`` framework's
   ``account.payment.method.line`` model: new lines default to
   ``selectable = False``, so the method will NOT appear as a choosable
   option in a new Payment Order's "Payment Method" field until this is
   turned on. You can toggle it either:

   - inline, in the journal's own "Outgoing Payments" tab, by clicking
     the "Selectable" toggle column on the "SIPAP Batch File" row; or
   - via Accounting > Configuration > Management > Payment Methods,
     opening the "SIPAP Batch File" line and checking "Selectable" there.

   No developer mode is required for either path -- this cost significant
   time to diagnose during live testing because it is easy to add the
   payment method to the journal and assume it is immediately usable.

Known limitation: the Atlas credential fields (API Key, private key PEM,
auth token) are restricted to the Accounting Manager group
(``account.group_account_manager``). A user in a lesser group (e.g.
``account.group_account_invoice``) who triggers dispatch, reversal, or
the polling cron may hit an ``AccessError`` reading those fields. This is
a known limitation, not a bug fixed in this module: granting broader
access via ``sudo()`` is a security-relevant decision left for a
deliberate follow-up, not bundled into this fix wave.
