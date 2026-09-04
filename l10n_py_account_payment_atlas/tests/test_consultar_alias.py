# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client import (
    AtlasApiClient,
)

_TEST_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_TEST_PRIVATE_KEY_PEM = _TEST_PRIVATE_KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()


@tagged("post_install", "-at_install", "l10n_py")
class TestConsultarAlias(TransactionCase):
    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client.requests.request"
    )
    def test_consultar_alias_builds_the_right_query_params(self, mock_request):
        mock_request.return_value = mock.Mock(
            status_code=200,
            json=lambda: {
                "entidad": {"codigo": "BNITPYPA", "descripcion": "Banco X"},
                "nroCuenta": "123456",
                "denominacion": "JAVIER MEZA",
            },
            headers={},
        )
        client = AtlasApiClient(
            api_key="test-key",
            environment_url="https://secure2.atlas.com.py:8443",
            private_key_pem=_TEST_PRIVATE_KEY_PEM,
        )
        result = client.consultar_alias("RUC", "5100159-4")
        self.assertEqual(result["nroCuenta"], "123456")
        args, _ = mock_request.call_args
        url = args[1]
        self.assertIn("tipo=RUC", url)
        self.assertIn("alias=5100159-4", url)
