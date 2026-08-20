Two-phase (quote/confirm) international transfer flow for Banco Atlas
(Paraguay): quote fees before committing, then confirm to debit. See the
spec's §5 for the full list of compliance fields and known documentation
gaps (no confirmed production URL, no exhaustive error code table, no
webhook -- settlement status requires polling, not yet implemented in
this module).

Known limitations / documented gaps (not implemented in this module):

- No menu item or list view is wired up beyond the
  ``ir.actions.act_window`` for ``l10n_py.atlas.exterior.transfer``. A
  consultant needs to add a menu item manually, or it is left for a
  future task.
- ``beneficiario_pais`` and ``beneficiario_ciudad`` are plain ``Integer``
  fields: the user must fill in the correct bank-side numeric code by
  hand, there is no friendly dropdown yet. This module does not
  implement fetching the bank's own catalogs (``GET
  /exterior/paises``, ``GET /exterior/ciudades/{pais}``) to populate
  those choices. Same gap applies to ``codigo_motivo`` -- see
  CONFIGURE.md.
- The bank's response signature is never verified (see
  ``l10n_py_account_payment_atlas``'s README for the same gap in the
  shared ``AtlasApiClient``).
