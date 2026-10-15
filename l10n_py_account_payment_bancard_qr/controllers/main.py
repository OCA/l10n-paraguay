# l10n_py_account_payment_bancard_qr/controllers/main.py

import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class BancardQrController(http.Controller):
    """Webhook endpoint for Bancard QR/Infonet (SPI contactless).

    This controller does not implement any real Bancard webhook protocol:
    there is no public Bancard integrator documentation for QR/Infonet
    confirming the request format, headers, or signature scheme. It exists
    only to provide an isolated, always-fail-closed route so that this
    module never accepts an unverified notification as genuine.
    """

    _webhook_url = "/payment/bancard_qr/webhook"

    @http.route(
        _webhook_url,
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def bancard_qr_webhook(self, **kwargs):
        """Receive a Bancard QR/Infonet webhook call and reject it.

        The header name Bancard would actually use to carry a signature is
        not confirmed either, so this reads a best-guess header only to
        pass *something* into `_verify_bancard_signature`; the outcome does
        not depend on which header (or none) is present, since that method
        always returns ``False`` (fail-closed) until a confirmed algorithm
        is implemented.
        """
        payload = request.httprequest.get_data()
        signature = request.httprequest.headers.get("X-Bancard-Signature", "")

        provider_model = request.env["payment.provider"].sudo()
        is_verified = provider_model._verify_bancard_signature(payload, signature)

        if not is_verified:
            _logger.warning(
                "Bancard QR webhook call rejected: signature verification "
                "is not implemented for this product (fail-closed by "
                "design). No transaction was processed."
            )
            return request.make_json_response(
                {
                    "error": "not_implemented",
                    "message": (
                        "Bancard QR/Infonet webhook processing is not "
                        "implemented in this module. This call was rejected, "
                        "not silently accepted."
                    ),
                },
                status=501,
            )

        # Unreachable with the current implementation of
        # `_verify_bancard_signature`, which always returns False. Kept
        # explicit rather than removed, so that whoever implements real
        # signature verification later has an obvious place to continue
        # the flow (look up the transaction, update its state, ...).
        return request.make_json_response(
            {"error": "not_implemented"}, status=501
        )  # pragma: no cover
