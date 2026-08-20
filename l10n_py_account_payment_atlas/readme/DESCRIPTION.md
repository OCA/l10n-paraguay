Shared authentication client and per-bank-account credential storage for
Banco Atlas (Paraguay) REST APIs: consulta de alias, consulta de saldo, and
the transport layer used by ``l10n_py_account_batch_payment_atlas`` and
``l10n_py_account_payment_exterior_atlas``.

This module implements no payment dispatch by itself.

Known limitation: ``atlas_bank_public_key_pem`` is collected and stored on
the bank account, but the bank's response signature is never verified --
no ``_verify_response_jwt()`` method exists on ``AtlasApiClient``. A
tampered or spoofed response currently would not be detected. This is a
documented gap, not yet implemented in this fix wave.
