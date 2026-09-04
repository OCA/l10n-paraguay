Confirm an ``account.payment.order`` using the SIPAP Batch File payment
method on an Atlas-configured bank as usual. This module intercepts the
export and calls Banco Atlas directly instead of producing a file. Use
the "Reversar pago" action on an ``account.payment.line`` to request a
reversal from the bank.

To register a beneficiary bank account known only by a CAS alias
(phone/email/RUC/CI), use the "Resolver Alias CAS (Banco Atlas)"
wizard (Accounting > Payables) instead of creating the
``res.partner.bank`` by hand. If an account with the same resolved
number already exists for that partner, the wizard opens it instead
of creating a duplicate.
