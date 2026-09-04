from unittest import mock

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import HttpCase

from ..models.payment_provider import BANCARD_QR_CODE


@tagged("post_install", "-at_install", "l10n_py")
class TestPaymentProviderBancardQr(HttpCase):
    """Tests que cubren únicamente lo determinístico de este esqueleto.

    Deliberadamente NO se prueba (ni se mockea como si funcionara) ninguna
    respuesta "exitosa" de Bancard: no existe protocolo real implementado,
    y simular una respuesta ficticia haría parecer que esta integración
    funciona cuando no es el caso. Ver README (DESCRIPTION.md) del módulo.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env.ref(
            "l10n_py_account_payment_bancard_qr.payment_provider_bancard_qr"
        )

    def test_provider_registered_via_data_file(self):
        """El provider se registra deshabilitado por defecto."""
        self.assertEqual(self.provider.code, BANCARD_QR_CODE)
        self.assertEqual(self.provider.state, "disabled")
        self.assertEqual(self.provider.bancard_qr_environment, "sandbox")

    def test_enable_without_base_url_raises_validation_error(self):
        """No se puede habilitar el provider sin URL base configurada."""
        with self.assertRaises(ValidationError):
            self.provider.write({"state": "test"})

    def test_enable_with_base_url_ok(self):
        """Con URL base configurada, sí se puede pasar a modo test."""
        self.provider.write(
            {
                "bancard_qr_base_url": "https://sandbox.example.invalid/bancard",
                "state": "test",
            }
        )
        self.assertEqual(self.provider.state, "test")

    def test_generate_qr_payload_not_implemented(self):
        """La generación de QR debe fallar siempre con NotImplementedError."""
        self.provider.write({"bancard_qr_base_url": "https://sandbox.example.invalid"})
        with self.assertRaises(NotImplementedError):
            self.provider._bancard_generate_qr_payload(
                amount=1000,
                currency=self.env.company.currency_id,
                reference="TEST-REF-001",
            )

    def test_verify_signature_always_fails_closed(self):
        """`_verify_bancard_signature` siempre retorna False (fail-closed).

        Se prueba explícitamente tanto sin firma como con una firma
        "plausible" cualquiera, para dejar claro que no existe ningún
        valor de entrada que la haga devolver True hoy.
        """
        Provider = self.env["payment.provider"]
        self.assertFalse(Provider._verify_bancard_signature(b"{}", ""))
        self.assertFalse(
            Provider._verify_bancard_signature(
                b'{"amount": 1000}', "sha256=deadbeef", secret="whatever"
            )
        )

    def test_webhook_rejects_call_without_signature(self):
        """El endpoint de webhook siempre rechaza la llamada (fail-closed).

        No se mockea ninguna respuesta de Bancard: se llama al endpoint
        real del módulo y se verifica que responde 501 (no implementado),
        nunca 200, sin importar el contenido enviado.
        """
        response = self.url_open(
            "/payment/bancard_qr/webhook",
            data=b'{"fake": "payload"}',
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 501)

    def test_webhook_calls_verify_signature(self):
        """El controller delega la decisión en `_verify_bancard_signature`.

        Se mockea explícitamente ese método (documentado como mock) solo
        para comprobar que el controller lo invoca y respeta su
        resultado, sin acoplar el test a la implementación fail-closed
        interna de la verificación (ya cubierta en el test anterior).
        """
        with mock.patch.object(
            type(self.env["payment.provider"]),
            "_verify_bancard_signature",
            return_value=False,
        ) as mocked:
            response = self.url_open(
                "/payment/bancard_qr/webhook",
                data=b"{}",
                headers={
                    "Content-Type": "application/json",
                    "X-Bancard-Signature": "anything",
                },
            )
            self.assertEqual(response.status_code, 501)
            self.assertTrue(mocked.called)
