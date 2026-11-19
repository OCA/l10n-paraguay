There is no end-user usage for this module yet: it does not process
payments. It exists so that:

1. The `payment.provider` record, its configuration fields, and its
   security constraints (API key access, required base URL) are already
   in place and reviewable.
2. A future implementer, once Bancard publishes integrator documentation
   and/or grants sandbox access for QR/Infonet, has a single, clearly
   marked place to implement two things:
   - the real HTTP call inside `_bancard_generate_qr_payload`
     (`models/payment_provider.py`);
   - the real signature check inside `_verify_bancard_signature`
     (same file), currently hardcoded to always return `False`
     (fail-closed) and marked as such in its docstring.
3. The webhook route (`/payment/bancard_qr/webhook`,
   `controllers/main.py`) can be safely enabled in Bancard's dashboard (if
   applicable) ahead of time, since it always rejects calls with a
   `501 Not Implemented` response instead of erroring unpredictably or,
   worse, silently accepting an unverified notification.

The POS checkout extension (OWL) to actually show a Bancard QR code to a
customer is explicitly out of scope for this module.
