# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

"""HTTP client for Banco Atlas (Paraguay) REST APIs.

Every Banco Atlas API (Consulta de Alias, Consulta de Saldo, Consulta de
Movimientos, Pago a Proveedores, Pago Salarios, Transferencias,
Transferencias Exterior) shares the same authentication scheme: an API
Key plus a JWT signed with the calling application's RSA private key, sent
as three HTTP headers (``X-RshkMichi-ApiKey``, ``X-Atl-Timestamp``,
``X-Atl-Auth``). This is *not* OAuth2 and *not* mTLS -- see the spec at
``docs/superpowers/specs`` (or the session's SIPAP/Atlas spec) for the
full breakdown of the scheme, sourced from the bank's own PDFs.
"""

import base64
import datetime
import hashlib
import json
from urllib.parse import urlencode

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def _b64url_encode(raw_bytes: bytes) -> str:
    """Base64url without padding, as required by JWT (RFC 7519)."""
    return base64.urlsafe_b64encode(raw_bytes).rstrip(b"=").decode()


class AtlasApiClient:
    """Client for one Banco Atlas bank account's credentials.

    Full constructor and ``call()``/``_verify_response_jwt()`` are added in
    Task 3; this task only adds the pure, database-free JWT builder so it
    can be unit-tested without an Odoo environment.
    """

    @staticmethod
    def build_jwt(
        private_key_pem: str,
        timestamp: str,
        resource: str,
        auth_token: str | None = None,
        content_hash: str | None = None,
    ) -> str:
        """Build the ``X-Atl-Auth`` JWT for one request.

        ``private_key_pem`` is the calling application's RSA private key
        (PEM, PKCS8, unencrypted -- Odoo already restricts read access to
        the field storing it via ``groups=``). ``timestamp`` must be the
        exact same string sent in the ``X-Atl-Timestamp`` header -- the
        bank's ``time`` claim must match it verbatim. ``resource`` is the
        request path, e.g. ``/proveedores/123456/registrar-pago``.
        ``auth_token`` and ``content_hash`` are omitted from the payload
        entirely when not given, per the bank's own JWT spec (they are
        optional/conditional claims, not claims sent as null).
        """
        header = {"alg": "RS256", "typ": "JWT"}
        payload = {"time": timestamp, "resource": resource}
        if auth_token is not None:
            payload["auth"] = auth_token
        if content_hash is not None:
            payload["content-hash"] = content_hash

        header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
        payload_b64 = _b64url_encode(
            json.dumps(payload, separators=(",", ":")).encode()
        )
        signing_input = f"{header_b64}.{payload_b64}".encode()

        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(), password=None
        )
        signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        signature_b64 = _b64url_encode(signature)

        return f"{header_b64}.{payload_b64}.{signature_b64}"

    @staticmethod
    def sha256_content_hash(raw_body: bytes) -> str:
        """SHA256 hex digest of a request body, for the ``content-hash``
        claim -- computed on the body *before* any additional encoding,
        per the bank's spec."""
        return hashlib.sha256(raw_body).hexdigest()

    def __init__(
        self,
        api_key: str,
        environment_url: str,
        private_key_pem: str,
        bank_public_key_pem: str | None = None,
        auth_token: str | None = None,
    ):
        self.api_key = api_key
        self.environment_url = environment_url.rstrip("/")
        self.private_key_pem = private_key_pem
        self.bank_public_key_pem = bank_public_key_pem
        self.auth_token = auth_token

    @classmethod
    def from_bank_account(cls, bank_account):
        """Build a client from a Banco-Atlas-enabled ``res.partner.bank``
        record (fields added in Task 4)."""
        environment_urls = {
            "testing": "https://secure2.atlas.com.py:8443",
            "production": bank_account.atlas_production_url or "",
        }
        base_url = environment_urls[bank_account.atlas_environment]
        return cls(
            api_key=bank_account.atlas_api_key,
            environment_url=base_url,
            private_key_pem=bank_account.atlas_private_key_pem,
            bank_public_key_pem=bank_account.atlas_bank_public_key_pem,
            auth_token=bank_account.atlas_auth_token,
        )

    def call(self, method: str, path: str, body: dict | None = None) -> dict:
        """Perform one Banco Atlas API call, fully authenticated.

        Raises ``AtlasApiError`` for any HTTP status other than 200. Does
        not retry -- retry/backoff policy, if any, is the caller's
        responsibility (this client is a thin, side-effect-transparent
        transport layer).
        """
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        content_hash = None
        raw_body = None
        if body is not None:
            raw_body = json.dumps(body, separators=(",", ":")).encode()
            content_hash = self.sha256_content_hash(raw_body)

        token = self.build_jwt(
            private_key_pem=self.private_key_pem,
            timestamp=timestamp,
            resource=path,
            auth_token=self.auth_token,
            content_hash=content_hash,
        )
        headers = {
            "X-RshkMichi-ApiKey": self.api_key,
            "X-Atl-Timestamp": timestamp,
            "X-Atl-Auth": token,
            "Content-Type": "application/json",
        }
        response = requests.request(
            method,
            f"{self.environment_url}{path}",
            headers=headers,
            json=body,
            timeout=30,
        )
        response_json = response.json()
        if response.status_code != 200:
            raise AtlasApiError(
                code=response_json.get("code"),
                message=response_json.get("message"),
                error_type=response_json.get("type"),
            )
        return response_json

    def consultar_alias(
        self, tipo: str, alias: str, cod_swift: str | None = None
    ) -> dict:
        """Resolve a CAS alias (CI/RUC/CRP/CRC/EMAIL/MOBILE) to account
        data via ``GET /cuentas-atlas/v1.5.0/cuentas/cas/obt-cta-by-alias``.
        ``tipo`` must be one of the bank's documented values verbatim."""
        params = {"tipo": tipo, "alias": alias}
        if cod_swift:
            params["codSwift"] = cod_swift
        query = urlencode(params)
        return self.call(
            "GET", f"/cuentas-atlas/v1.5.0/cuentas/cas/obt-cta-by-alias?{query}"
        )


class AtlasApiError(Exception):
    """Raised for any non-200 response from a Banco Atlas API.

    Every Banco Atlas API uses the same error body shape:
    ``{"code": ..., "message": ..., "type": ..., "useApiMessage": ...}``.
    There is no exhaustive, bank-published list of ``code`` values (see
    the spec's pendency list) -- this class always carries the raw values
    through rather than translating them into a fixed enum.
    """

    def __init__(self, code, message, error_type):
        self.code = code
        self.message = message
        self.error_type = error_type
        super().__init__(f"[{error_type}] {code}: {message}")
