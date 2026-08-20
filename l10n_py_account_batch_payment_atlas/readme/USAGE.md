Confirm an ``account.payment.order`` using the SIPAP Batch File payment
method on an Atlas-configured bank as usual. This module intercepts the
export and calls Banco Atlas directly instead of producing a file. Use
the "Reversar pago" action on an ``account.payment.line`` to request a
reversal from the bank.
