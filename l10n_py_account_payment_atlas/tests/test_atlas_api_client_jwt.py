# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import base64
import json

from cryptography.hazmat.primitives.asymmetric import rsa

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client import (
    AtlasApiClient,
)

# Fixed 2048-bit test keypair, generated once for this test suite only.
# Never use this key outside of tests.
_TEST_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _pem(key):
    from cryptography.hazmat.primitives import serialization

    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


@tagged("post_install", "-at_install", "l10n_py")
class TestAtlasApiClientJwt(TransactionCase):
    def test_jwt_has_three_dot_separated_base64url_segments(self):
        token = AtlasApiClient.build_jwt(
            private_key_pem=_pem(_TEST_PRIVATE_KEY),
            timestamp="2026-08-19T10:00:00-04:00",
            resource="/proveedores/123456/registrar-pago",
        )
        self.assertEqual(len(token.split(".")), 3)

    def test_jwt_payload_contains_required_claims(self):
        token = AtlasApiClient.build_jwt(
            private_key_pem=_pem(_TEST_PRIVATE_KEY),
            timestamp="2026-08-19T10:00:00-04:00",
            resource="/proveedores/123456/registrar-pago",
            auth_token="some-auth-token",
            content_hash="deadbeef",
        )
        _header_b64, payload_b64, _sig_b64 = token.split(".")
        payload_b64 += "=" * (-len(payload_b64) % 4)  # restore stripped padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        self.assertEqual(payload["time"], "2026-08-19T10:00:00-04:00")
        self.assertEqual(payload["resource"], "/proveedores/123456/registrar-pago")
        self.assertEqual(payload["auth"], "some-auth-token")
        self.assertEqual(payload["content-hash"], "deadbeef")

    def test_jwt_omits_optional_claims_when_not_given(self):
        token = AtlasApiClient.build_jwt(
            private_key_pem=_pem(_TEST_PRIVATE_KEY),
            timestamp="2026-08-19T10:00:00-04:00",
            resource="/cuentas/123456/saldo",
        )
        _header_b64, payload_b64, _sig_b64 = token.split(".")
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        self.assertNotIn("auth", payload)
        self.assertNotIn("content-hash", payload)
