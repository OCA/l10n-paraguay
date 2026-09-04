The first real (non-file) SIPAP batch payment exporter for Banco Atlas:
dispatches ``account.payment.order`` batches directly to the bank's
``Pago a Proveedores`` REST API instead of generating a file for manual
upload, with automatic SPI/LBTR routing based on the limit confirmed by
Banco Atlas (2026-09-02, item 9 of the SIPAP clarification round): Gs.
10.000.000 per SPI transfer, PYG only. This supersedes the Gs. 5.000.000
figure previously assumed from BCP Resolución 1/2023 §50.01, which the
bank's own confirmation overrides for this integration. The limit
applies PER TRANSFER: a batch is only routed/validated as SPI when
EVERY individual line is within the limit, never based on the batch's
total sum).

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
  account type, and ``AtlasApiClient.consultar_alias`` is never called
  from this dispatch path.
- Beneficiary bank accounts that need to be identified only by a CAS
  alias (phone/email/RUC/CI) instead of a full account number can no
  longer be resolved at dispatch time: a previous version of this
  module attempted that (a ``_l10n_py_resolver_alias_atlas`` helper
  called from ``_l10n_py_dispatch_batch_api_atlas``), but a live test
  against a real Odoo 18 instance proved that branch to be dead code --
  ``res.partner.bank.acc_number`` is ``required=True`` in Odoo's own
  core (``odoo/addons/base/models/res_bank.py``, no override anywhere in
  this repo), so a beneficiary bank account without an account number
  can never be persisted in the first place, and the alias-resolution
  branch could never actually be reached. That code (helper, dispatch
  branch, and its isolated unit tests) has been removed.

  Instead, alias resolution now happens once, at REGISTRATION time, via
  the new **"Resolver Alias CAS (Banco Atlas)"** wizard
  (``l10n_py.atlas.alias.resolver``, Accounting > Payables menu). Given
  the company's own Atlas-enabled bank account (used to authenticate the
  lookup), the beneficiary partner, and the alias type/value, the wizard
  calls ``AtlasApiClient.consultar_alias`` once, shows the account
  holder's name returned by the bank (``denominacion``) for a human to
  visually confirm it matches the expected beneficiary, and only then
  creates (or, if one with the same resolved account number already
  exists for that partner, opens the existing) ``res.partner.bank``
  record with a proper ``acc_number`` (the one the bank resolved,
  ``nroCuenta``) plus the alias type/value kept for reference. From that
  point on, every downstream flow (dispatch included) only ever deals
  with a normal, fully-numbered bank account -- no alias-only branch
  exists anywhere in the dispatch path any more.
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
