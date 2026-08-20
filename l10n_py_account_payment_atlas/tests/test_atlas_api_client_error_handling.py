# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from unittest import mock

import requests

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client import (
    AtlasApiError,
)

from .test_atlas_api_client_call import _client


@tagged("post_install", "-at_install", "l10n_py")
class TestAtlasApiClientErrorHandling(TransactionCase):
    def test_atlas_api_error_is_a_user_error(self):
        """I1: bank-side rejections must surface as a proper Odoo
        user-facing error dialog, not an uncaught exception/traceback."""
        error = AtlasApiError(code="g1011", message="boom", error_type="APPLICATION")
        self.assertIsInstance(error, UserError)
        # Existing callers doing assertRaises(AtlasApiError) must still
        # work, since UserError is still an Exception subclass.
        self.assertIsInstance(error, Exception)

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client.requests.request"
    )
    def test_connection_error_is_wrapped_as_atlas_api_error(self, mock_request):
        """I2: a connection-level failure (timeout, DNS, refused
        connection) must not be an opaque requests traceback."""
        mock_request.side_effect = requests.exceptions.ConnectionError(
            "Connection refused"
        )
        with self.assertRaises(AtlasApiError) as ctx:
            _client().call("GET", "/cuentas/123456/saldo")
        self.assertIn("Connection refused", str(ctx.exception))

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client.requests.request"
    )
    def test_timeout_is_wrapped_as_atlas_api_error(self, mock_request):
        mock_request.side_effect = requests.exceptions.Timeout("timed out")
        with self.assertRaises(AtlasApiError):
            _client().call("GET", "/cuentas/123456/saldo")

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client.requests.request"
    )
    def test_non_json_response_is_wrapped_as_atlas_api_error_with_excerpt(
        self, mock_request
    ):
        """I2: a non-JSON body (e.g. an HTML gateway error page) must
        raise a diagnosable AtlasApiError carrying the HTTP status and a
        truncated excerpt of the raw body, not a raw ValueError."""
        html_body = "<html><body>502 Bad Gateway</body></html>" * 10

        def _raise_value_error():
            raise ValueError("Expecting value: line 1 column 1 (char 0)")

        mock_request.return_value = mock.Mock(
            status_code=502,
            json=_raise_value_error,
            text=html_body,
            headers={},
        )
        with self.assertRaises(AtlasApiError) as ctx:
            _client().call("GET", "/cuentas/123456/saldo")
        message = str(ctx.exception)
        self.assertIn("502", message)
        # Truncated to ~200 chars, not the full body.
        self.assertLess(len(message), len(html_body))
