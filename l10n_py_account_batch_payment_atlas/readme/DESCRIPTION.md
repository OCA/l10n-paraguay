The first real (non-file) SIPAP batch payment exporter for Banco Atlas:
dispatches ``account.payment.order`` batches directly to the bank's
``Pago a Proveedores`` REST API instead of generating a file for manual
upload, with automatic SPI/LBTR routing based on the official BCP limit
(Gs. 5.000.000 per SPI transfer, PYG only -- Resolución 1/2023 §50.01
applies this limit PER TRANSFER: a batch is only routed/validated as SPI
when EVERY individual line is within the limit, never based on the
batch's total sum).

No webhook exists on this API: confirmation of a pending payment relies on
a scheduled polling job.

Known limitations / documented gaps (not implemented in this module):

- ``l10n_py_atlas_tipo_transferencia`` (SPI/LBTR/ACH/Atlas) only enforces
  the legal SPI limit as a PRE-FLIGHT check before dispatch. It does NOT
  control which trilho (rail) Banco Atlas actually uses for the transfer:
  the bank's Pago a Proveedores API documentation does not specify a
  field for communicating that choice, so no such field is sent in the
  payload. If/when the bank documents one, this module should be updated
  to actually pass the chosen route through.
- ``formaPago`` is always hardcoded to ``"C"`` (credit to account) in the
  batch dispatch payload. It is never derived from the beneficiary's
  account type, and ``AtlasApiClient.consultar_alias`` (which exists and
  could resolve a beneficiary via alias) is never called from this
  dispatch path.
- No per-line/aggregate ``sent``/``rejected``/``partially_rejected``
  order-level state is surfaced distinctly in the UI beyond what already
  exists (``account.payment.line.atlas_estado`` per line).
- No handling exists for a non-null ``metodoAprobacion`` in the bank's
  response (a 2FA/manual-approval flow on the bank's side): this module
  assumes every dispatch either fully succeeds or fully fails per line,
  synchronously.
- Non-manager users (e.g. ``account.group_account_invoice``) may hit an
  ``AccessError`` reading Atlas credentials (``atlas_api_key``,
  ``atlas_private_key_pem``, ``atlas_auth_token``) when triggering
  dispatch/reversal/polling actions, since those fields are restricted to
  ``account.group_account_manager``. This is intentional and NOT worked
  around with ``sudo()`` in this fix wave (that would be a
  security-relevant change better made deliberately) -- see this
  module's CONFIGURE.md.
