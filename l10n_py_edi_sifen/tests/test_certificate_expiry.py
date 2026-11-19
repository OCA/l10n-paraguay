# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import base64
import datetime

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from odoo.tests.common import TransactionCase, tagged

CERT_PASSWORD = "test1234"


def _build_pkcs12(not_valid_after, password=CERT_PASSWORD):
    """Build a self-signed PKCS12 blob (base64) expiring at `not_valid_after`."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "SIFEN Test Certificate")]
    )
    not_valid_before = datetime.datetime.now(
        datetime.timezone.utc
    ) - datetime.timedelta(days=1)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_valid_before)
        .not_valid_after(not_valid_after)
        .sign(key, hashes.SHA256())
    )
    pkcs12_bytes = pkcs12.serialize_key_and_certificates(
        name=b"sifen-test",
        key=key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(
            password.encode()
        ),
    )
    return base64.b64encode(pkcs12_bytes)


@tagged("post_install", "-at_install", "l10n_py")
class TestCertificateExpiry(TransactionCase):
    """Testes do gap 1: cálculo automático de expiração + alerta (design 2026-08-18)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.company.write(
            {
                "l10n_py_certificate": False,
                "l10n_py_certificate_password": False,
            }
        )

    def _set_certificate(self, days_from_now, password=CERT_PASSWORD):
        not_after = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            days=days_from_now
        )
        cert_b64 = _build_pkcs12(not_after, password=password)
        self.company.write(
            {
                "l10n_py_certificate": cert_b64,
                "l10n_py_certificate_password": password,
            }
        )
        return not_after.date()

    def test_compute_expiry_reads_pkcs12_not_after(self):
        expected_date = self._set_certificate(10)
        self.assertEqual(self.company.l10n_py_certificate_expiry, expected_date)

    def test_compute_state_valid_when_far_from_expiry(self):
        self._set_certificate(90)
        self.assertEqual(self.company.l10n_py_certificate_state, "valid")

    def test_compute_state_to_expire_within_30_days(self):
        self._set_certificate(15)
        self.assertEqual(self.company.l10n_py_certificate_state, "to_expire")

    def test_compute_state_expired_in_the_past(self):
        # not_valid_after ontem (data de calendario anterior a hoje); a
        # janela de validade toda fica no passado para o teste ser estavel
        # independente da hora do dia em que rodar.
        not_after = datetime.datetime.now(
            datetime.timezone.utc
        ) - datetime.timedelta(days=1)
        not_before = not_after - datetime.timedelta(days=2)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name(
            [x509.NameAttribute(NameOID.COMMON_NAME, "SIFEN Test Certificate")]
        )
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(not_before)
            .not_valid_after(not_after)
            .sign(key, hashes.SHA256())
        )
        pkcs12_bytes = pkcs12.serialize_key_and_certificates(
            name=b"sifen-test",
            key=key,
            cert=cert,
            cas=None,
            encryption_algorithm=serialization.BestAvailableEncryption(
                CERT_PASSWORD.encode()
            ),
        )
        cert_b64 = base64.b64encode(pkcs12_bytes)
        self.company.write(
            {
                "l10n_py_certificate": cert_b64,
                "l10n_py_certificate_password": CERT_PASSWORD,
            }
        )
        self.assertEqual(self.company.l10n_py_certificate_state, "expired")

    def test_compute_expiry_wrong_password_does_not_raise(self):
        cert_b64 = _build_pkcs12(
            datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(days=30),
            password=CERT_PASSWORD,
        )
        self.company.write(
            {
                "l10n_py_certificate": cert_b64,
                "l10n_py_certificate_password": "senha-errada",
            }
        )
        self.assertFalse(self.company.l10n_py_certificate_expiry)
        self.assertFalse(self.company.l10n_py_certificate_state)

    def test_compute_expiry_empty_certificate_returns_false(self):
        self.company.write(
            {
                "l10n_py_certificate": False,
                "l10n_py_certificate_password": False,
            }
        )
        self.assertFalse(self.company.l10n_py_certificate_expiry)
        self.assertFalse(self.company.l10n_py_certificate_state)

    def test_cron_logs_warning_for_expiring_company(self):
        self._set_certificate(15)
        with self.assertLogs(
            "odoo.addons.l10n_py_edi_sifen.models.res_company", level="WARNING"
        ) as capture:
            self.env["res.company"]._cron_check_l10n_py_certificate_expiry()
        self.assertTrue(
            any(self.company.display_name in message for message in capture.output)
        )
