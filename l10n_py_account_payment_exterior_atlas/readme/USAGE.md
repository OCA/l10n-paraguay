Create an ``l10n_py.atlas.exterior.transfer`` record with the beneficiary
and transfer data, then:

1. Click "Cotizar" (``action_atlas_cotizar``, modo V) to get the bank's
   fee quote without debiting the account yet. This populates
   ``numero_referencia`` and the ``monto_cargo*``/``total_debito``
   fields.
2. Review the quote, then click "Confirmar"
   (``action_atlas_confirmar``, modo C) to actually debit the account.
   This can only be done once the transfer is in the "Cotizado" state.

Accessible via Accounting > Vendors > Transferencias al Exterior
(Atlas).
