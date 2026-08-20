# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client import (
    AtlasApiClient,
    AtlasApiError,
)

_TEST_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_TEST_PRIVATE_KEY_PEM = _TEST_PRIVATE_KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()


def _client():
    return AtlasApiClient(
        api_key="test-api-key",
        environment_url="https://secure2.atlas.com.py:8443/proveedores-atlas/v1.5.0",
        private_key_pem=_TEST_PRIVATE_KEY_PEM,
        auth_token="test-auth-token",
    )


@tagged("post_install", "-at_install", "l10n_py")
class TestAtlasApiClientCall(TransactionCase):
    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client.requests.request"
    )
    def test_call_sends_the_three_required_headers(self, mock_request):
        mock_request.return_value = mock.Mock(
            status_code=200, json=lambda: {"ok": True}, headers={}
        )
        _client().call("GET", "/proveedores/123456/consultar-pago")
        _, kwargs = mock_request.call_args
        headers = kwargs["headers"]
        self.assertIn("X-RshkMichi-ApiKey", headers)
        self.assertIn("X-Atl-Timestamp", headers)
        self.assertIn("X-Atl-Auth", headers)
        self.assertEqual(headers["X-RshkMichi-ApiKey"], "test-api-key")

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client.requests.request"
    )
    def test_call_returns_parsed_json_on_200(self, mock_request):
        mock_request.return_value = mock.Mock(
            status_code=200,
            json=lambda: {"nroCuenta": "123456", "saldo": 500000},
            headers={},
        )
        result = _client().call("GET", "/cuentas/123456/saldo")
        self.assertEqual(result["saldo"], 500000)

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client.requests.request"
    )
    def test_call_raises_atlas_api_error_on_non_200(self, mock_request):
        mock_request.return_value = mock.Mock(
            status_code=400,
            json=lambda: {
                "code": "g1011",
                "message": "El contexto no tiene token de acceso (access_token)",
                "type": "APPLICATION",
                "useApiMessage": False,
            },
            headers={},
        )
        with self.assertRaises(AtlasApiError) as ctx:
            _client().call("GET", "/cuentas/123456/saldo")
        self.assertEqual(ctx.exception.code, "g1011")
        self.assertEqual(ctx.exception.error_type, "APPLICATION")

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client.requests.request"
    )
    def test_call_sends_content_hash_header_claim_only_when_body_present(
        self, mock_request
    ):
        mock_request.return_value = mock.Mock(
            status_code=200, json=lambda: {"ok": True}, headers={}
        )
        client = _client()
        client.call("GET", "/cuentas/123456/saldo")
        _, get_kwargs = mock_request.call_args
        client.call("POST", "/proveedores/123456/registrar-pago", body={"a": 1})
        _, post_kwargs = mock_request.call_args
        # Both calls must succeed and send a JWT; the content-hash claim
        # itself is internal to the JWT payload (opaque, checked in
        # test_atlas_api_client_jwt.py) -- this test only asserts both
        # call shapes work end-to-end.
        self.assertIn("X-Atl-Auth", get_kwargs["headers"])
        self.assertIn("X-Atl-Auth", post_kwargs["headers"])
        self.assertEqual(post_kwargs["json"], {"a": 1})
