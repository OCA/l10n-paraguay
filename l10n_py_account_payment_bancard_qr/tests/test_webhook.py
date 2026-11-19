from odoo.tests import tagged
from odoo.tests.common import TransactionCase

# NOTE: none of the tests below depend on the internet or on a real
# Bancard response. They call our own `_verify_bancard_signature` model
# method directly, in-process, with no HTTP layer involved. The
# HTTP-level check of the webhook route itself (that it also responds
# with a 501 rejection end-to-end) lives in
# `test_payment_provider.py::TestPaymentProviderBancardQr`, using Odoo's
# own local test client — not a real Bancard endpoint either way.


@tagged("post_install", "-at_install", "l10n_py")
class TestVerifyBancardSignature(TransactionCase):
    def test_no_signature_is_rejected(self):
        result = self.env["payment.provider"]._verify_bancard_signature(
            payload=b"{}", signature=""
        )
        self.assertFalse(result)

    def test_arbitrary_signature_is_still_rejected(self):
        """Even a plausible-looking signature must be rejected: there is no
        confirmed algorithm to validate it against, so acceptance is never
        the outcome, regardless of input."""
        result = self.env["payment.provider"]._verify_bancard_signature(
            payload=b'{"amount": "100.00", "status": "paid"}',
            signature="deadbeef" * 8,
        )
        self.assertFalse(result)

    def test_empty_payload_is_rejected(self):
        result = self.env["payment.provider"]._verify_bancard_signature(
            payload=b"", signature="anything"
        )
        self.assertFalse(result)
