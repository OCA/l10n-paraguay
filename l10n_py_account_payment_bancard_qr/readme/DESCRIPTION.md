**This module is an honest skeleton, not a working integration.**

It registers a `payment.provider` for Bancard QR/Infonet (SPI
contactless) — a Paraguayan QR payment product, *different* from Bancard
vPOS 2.0 (card tokenization) — and provides the scaffolding a future
integration would need:

- The provider record and its configuration fields (API key, environment,
  API base URL), following the standard Odoo payment provider pattern.
- A `_bancard_generate_qr_payload` method that always raises
  `NotImplementedError`, explaining exactly what is missing.
- A webhook route (`/payment/bancard_qr/webhook`) that always rejects
  incoming calls (fail-closed), because the actual signature/callback
  protocol used by Bancard for this product has no public integrator
  documentation available.

No HTTP call to Bancard is implemented anywhere in this module. No test
in this module simulates or asserts a real Bancard response. This is
deliberate: there is currently no public documentation, sandbox, or
credentials for Bancard's QR/Infonet integrator API, and simulating one
would misrepresent the state of this integration.

Out of scope for this module (tracked separately): the POS front-end
(OWL) extension to actually present a Bancard QR code at checkout.
