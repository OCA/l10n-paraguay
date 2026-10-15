# l10n_py_account_payment_bancard_qr/models/payment_provider.py

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# Technical code of this provider, registered via `selection_add` on
# `payment.provider.code`, following the same pattern used by every other
# Odoo/OCA payment provider module (e.g. `payment_stripe`, `payment_adyen`).
BANCARD_QR_CODE = "bancard_qr"


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[(BANCARD_QR_CODE, "Bancard QR SPI")],
        ondelete={BANCARD_QR_CODE: "set default"},
    )

    # === Configuration fields ===
    #
    # NOTE: none of these fields ever back a real HTTP call in this module.
    # They only exist so that a future implementation (once Bancard
    # publishes integrator documentation/sandbox access for QR/Infonet) has
    # somewhere to read its configuration from, without requiring a data
    # model change.
    bancard_qr_api_key = fields.Char(
        string="Bancard QR API Key",
        groups="base.group_system",
        help="API key/secret issued by Bancard for the QR/Infonet (SPI "
        "contactless) integration. Restricted to System administrators. "
        "Never logged: no code in this module writes this value to the "
        "log, to an exception message, or to any other trace.",
    )
    bancard_qr_environment = fields.Selection(
        selection=[("sandbox", "Sandbox"), ("production", "Production")],
        string="Bancard QR Environment",
        default="sandbox",
        help="Target Bancard QR/Infonet environment. Purely descriptive in "
        "this module: no HTTP call is implemented yet, so nothing actually "
        "connects to either environment.",
    )
    bancard_qr_base_url = fields.Char(
        string="Bancard QR API Base URL",
        help="Base URL of the Bancard QR/Infonet API for the selected "
        "environment. Intentionally never hardcoded in code: Bancard has "
        "not published a stable, confirmed public endpoint for this "
        "product, so the value must be configured here once available.",
    )

    # === Constraints ===

    @api.constrains("state", "code", "bancard_qr_base_url")
    def _check_bancard_qr_base_url_required(self):
        """A base URL must be configured before the provider can be enabled.

        This does not mean the module can actually talk to Bancard once a
        URL is set: `_bancard_generate_qr_payload` below still raises
        `NotImplementedError` unconditionally. This constraint only avoids
        an enabled provider with an *obviously* incomplete configuration.
        """
        for provider in self:
            if (
                provider.code == BANCARD_QR_CODE
                and provider.state != "disabled"
                and not provider.bancard_qr_base_url
            ):
                raise ValidationError(
                    _(
                        "Bancard QR SPI: the API Base URL must be configured "
                        "before this provider can be enabled or set to test "
                        "mode."
                    )
                )

    # === Business methods ===

    def _bancard_generate_qr_payload(self, amount, currency, reference, **kwargs):
        """Generate the QR payload for a Bancard QR/Infonet payment request.

        Deliberately NOT implemented. Bancard QR/Infonet (SPI contactless)
        is a different product from Bancard vPOS 2.0 (card tokenization),
        and as of this writing there is no publicly available integrator
        manual, API reference, or sandbox/credentials for QR/Infonet that
        Odoo/OCA maintainers can implement against.

        Simulating a fake HTTP call or returning a fabricated payload here
        would be worse than not implementing it at all: it would look like
        a working integration while being pure fiction. This method
        therefore always raises `NotImplementedError`, with a message
        explaining exactly what is missing, so that whoever picks this up
        next knows this is a real gap and not a bug.

        :param float amount: transaction amount.
        :param res.currency currency: transaction currency.
        :param str reference: payment transaction reference.
        :raise NotImplementedError: always.
        """
        self.ensure_one()
        raise NotImplementedError(
            _(
                "Bancard QR/Infonet (SPI contactless) payload generation is "
                "not implemented. There is no public Bancard integrator "
                "manual, API reference, or sandbox/credentials available for "
                "this specific product (QR/Infonet — do not confuse with "
                "Bancard vPOS 2.0 card tokenization, which is a different "
                "product with its own, separate documentation). Before "
                "implementing this method: (1) obtain the Bancard QR "
                "integrator manual describing the QR generation endpoint, "
                "request/response payload and authentication scheme, (2) "
                "obtain sandbox credentials to validate the implementation "
                "against, then (3) implement the real HTTP call here and "
                "remove this exception."
            )
        )

    @api.model
    def _verify_bancard_signature(self, payload, signature, secret=None):
        """Verify the HMAC signature of an inbound Bancard QR webhook call.

        WARNING — ALGORITHM NOT CONFIRMED: Bancard has not published
        integrator documentation for QR/Infonet (SPI contactless)
        describing the exact webhook signature scheme (hash function,
        payload canonicalization, header name/encoding, secret
        derivation...). Until that documentation (or sandbox access that
        lets us observe real signed callbacks) is obtained, this method
        MUST fail closed: every call returns ``False``, rejecting the
        webhook, instead of guessing an algorithm and risking silently
        accepting a forged or unverifiable notification as if it were
        confirmed to come from Bancard.

        Do not change the body of this method to `return True`, nor to a
        best-guess HMAC implementation, without an authoritative Bancard
        source (integrator manual, official support answer, or verified
        sandbox behavior) backing the change.

        :param bytes payload: raw request body received from Bancard.
        :param str signature: signature value provided by Bancard, in
            whatever header/field it uses (also unconfirmed).
        :param str secret: shared secret to verify against, when/if one is
            confirmed. Unused for now.
        :return: always ``False`` (fail-closed).
        :rtype: bool
        """
        return False
