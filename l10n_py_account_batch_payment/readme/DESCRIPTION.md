Foundation module for exporting Paraguayan SIPAP batch payment files
(pagos por lote via el Sistema de Pagos del Banco Central del Paraguay).

**Important scope note**: SIPAP itself only standardizes bank-to-BCP
communication in ISO 20022. There is no single "SIPAP file format" that
every home banking portal accepts: each bank's corporate home banking
typically expects its own proprietary layout (CSV/TXT), and ISO 20022
pain.001 is only *one possible* format among several, not a universal
standard. Because of this, this module implements no concrete bank
layout at all: it only provides

- Master data fields needed by any exporter: an "Alias CAS" (SIPAP
  account alias by phone/email/RUC/CI) and a SIPAP bank code on bank
  accounts and banks (``res.partner.bank`` / ``res.bank``).
- A new ``account.payment.method`` ("SIPAP Batch File") usable on
  ``account.payment.order`` (from the OCA ``account_payment_batch_oca``
  module — this module never touches Odoo's Enterprise
  ``account.batch.payment``, which is not usable here).
- A pluggable dispatch mechanism (
  ``AccountPaymentOrder._l10n_py_generate_batch_file``): it looks up
  ``l10n_py_sipap_export_code`` on the ``res.bank`` of the company's own
  bank account, and calls a matching
  ``_l10n_py_generate_batch_file_<code>`` method. If no matching method
  exists (because no exporter module is installed for that bank), it
  raises a clear error instead of producing a guessed file.

A concrete exporter, such as the generic ISO 20022 one, is implemented
in a separate module (``l10n_py_account_batch_payment_iso20022``) that
depends on this one.

**Dependency note**: this module depends on ``account_payment_batch_oca``
(``OCA/bank-payment-alternative``), which is licensed AGPL-3. This
module itself remains LGPL-3 (a dependent module is not required to
adopt the license of a dependency), but this is noted here for
transparency, since AGPL-3 has network-use implications that do not
apply to this LGPL-3 module directly but are worth knowing about the
dependency chain.
