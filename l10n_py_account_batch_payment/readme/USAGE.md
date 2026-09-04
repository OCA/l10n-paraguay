Create a payment/debit order (``account.payment.order``) using the
**SIPAP Batch File** payment method, add payment lines, confirm it, and
click **Generate File**. If a bank on the company's account has an
exporter registered (via an installed module such as
``l10n_py_account_batch_payment_iso20022``), the file is generated;
otherwise, an explicit error explains that no exporter is registered for
that bank instead of producing an unverified file.
