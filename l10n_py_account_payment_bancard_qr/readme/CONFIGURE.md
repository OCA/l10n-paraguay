Go to **Accounting > Configuration > Payment Providers** and open
**Bancard QR SPI** (installed disabled by default).

Configuration fields, on the **Bancard QR SPI** page of the provider
form:

- **Bancard QR Environment**: sandbox or production. Purely descriptive:
  no HTTP call is implemented yet, so selecting either value does not
  connect to anything.
- **Bancard QR API Base URL**: never hardcoded in code. Must be set here
  once Bancard's real, confirmed endpoint is known. Required before the
  provider can be enabled or set to test mode (enforced by a constraint),
  even though no real call will be made against it yet.
- **Bancard QR API Key**: restricted to users in the System
  administrators group (`base.group_system`, technical name shown under
  Settings > Users & Companies > Groups). Never written to any log or
  exception message by this module's code.

Enabling this provider does **not** make it functional: any attempt to
generate a QR payment payload (`_bancard_generate_qr_payload`) raises
`NotImplementedError`, and the webhook route always rejects incoming
calls. See `DESCRIPTION.md` for why.
