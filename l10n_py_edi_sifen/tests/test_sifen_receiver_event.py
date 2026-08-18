# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

"""Tests del ruteo del payload SIFEN por tipo de evento de receptor.

Cubren la Tesis central del design doc (docs/superpowers/specs/
2026-08-18-l10n-py-acuse-recibo-design.md): un único `TgGroupEvt`, un sólo
campo poblado por llamada, mismo endpoint `evento` que cancelación/
inutilización. Se ejercitan de punta a punta (modelo `l10n_py.edi.received.
event` → `_prepare_event_vals` → conector SIFEN → binding pysifen), sin red
real: se mockea `_sifen_get_evento` (igual patrón que
`test_sifen_connector.TestSIFENConnector.test_test_connection`).
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.l10n_py_edi_base.services.cdc_generator import CDCGenerator

_GROUP_FIELDS = (
    "rGeVeCan",
    "rGeVeInu",
    "rGeVeNotRec",
    "rGeVeConf",
    "rGeVeDisconf",
    "rGeVeDescon",
)


@tagged("post_install", "-at_install")
class TestSifenReceiverEvent(TransactionCase):
    """Test del armado del `TgGroupEvt` por `event_type`."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.company.write(
            {
                "name": "Empresa Receptora Test",
                "l10n_py_ruc": "80012345",
            }
        )
        cls.env["l10n_py.edi.connector"].sudo().search(
            [("company_id", "=", cls.company.id)]
        ).unlink()
        cls.connector = cls.env["l10n_py.edi.connector"].create(
            {
                "name": "SIFEN Test",
                "company_id": cls.company.id,
                "provider_type": "sifen",
                "environment": "test",
            }
        )
        cls.partner_vendor = cls.env["res.partner"].create(
            {"name": "Proveedor Test", "l10n_py_ruc": "80067890"}
        )
        cls.cdc = CDCGenerator.generate(
            doc_type=1,
            ruc="80098765",
            dv="3",
            establishment="001",
            expedition_point="001",
            sequence=42,
            taxpayer_type="2",
            emission_date="2026-08-01T10:00:00",
            emission_type=1,
            security_code="987654321",
        )

    def _create_event(self, **vals):
        base_vals = {
            "company_id": self.company.id,
            "cdc": self.cdc,
            "partner_id": self.partner_vendor.id,
        }
        base_vals.update(vals)
        return self.env["l10n_py.edi.received.event"].create(base_vals)

    @staticmethod
    def _mock_evento(mock_get_evento, protocol="PROT-XYZ"):
        """Arma un `_sifen_get_evento()` falso cuyo `enviar_evento` responde
        Aprobado, y devuelve el mock para inspeccionar el `grupo` recibido."""
        mock_evento = MagicMock()
        mock_result = MagicMock()
        mock_result.gResProcEVe.dEstRes = "Aprobado"
        mock_result.gResProcEVe.dProtConsLote = protocol
        mock_evento.enviar_evento.return_value = mock_result
        mock_evento.cleanup.return_value = None
        mock_get_evento.return_value = mock_evento
        return mock_evento

    def _assert_only_field_populated(self, mock_evento, populated_field):
        grupo = mock_evento.enviar_evento.call_args[0][0]
        evt = grupo.rGesEve[0].rEve.gGroupTiEvt
        self.assertIsNotNone(
            getattr(evt, populated_field),
            f"{populated_field} debería estar poblado",
        )
        for field_name in _GROUP_FIELDS:
            if field_name == populated_field:
                continue
            self.assertIsNone(
                getattr(evt, field_name),
                f"{field_name} no debería estar poblado (vaciado de otro tipo)",
            )
        return evt

    # ============== 3. Conformidad ==============

    @patch(
        "odoo.addons.l10n_py_edi_sifen.models.edi_connector"
        ".EDIConnector._sifen_get_evento"
    )
    def test_send_conformidad_builds_correct_payload(self, mock_get_evento):
        mock_evento = self._mock_evento(mock_get_evento)
        event = self._create_event(
            event_type="conformidad",
            tipo_conformidad="1",
        )
        event.action_send_receiver_event()

        self.assertEqual(event.state, "accepted")
        self.assertEqual(event.protocolo_sifen, "PROT-XYZ")
        evt = self._assert_only_field_populated(mock_evento, "rGeVeConf")
        self.assertEqual(evt.rGeVeConf.Id, self.cdc)

    # ============== 4. Desconocimiento ==============

    @patch(
        "odoo.addons.l10n_py_edi_sifen.models.edi_connector"
        ".EDIConnector._sifen_get_evento"
    )
    def test_send_desconocimiento_builds_correct_payload(self, mock_get_evento):
        mock_evento = self._mock_evento(mock_get_evento)
        event = self._create_event(
            event_type="desconocimiento",
            tipo_receptor="1",
            fecha_emision_dte="2026-08-01 10:00:00",
            fecha_recepcion="2026-08-02 10:00:00",
            motivo="Documento no reconocido: nunca se recibió mercadería",
        )
        event.action_send_receiver_event()

        self.assertEqual(event.state, "accepted")
        evt = self._assert_only_field_populated(mock_evento, "rGeVeDescon")
        self.assertEqual(evt.rGeVeDescon.Id, self.cdc)
        self.assertEqual(evt.rGeVeDescon.dNomRec, self.company.name)
        self.assertEqual(evt.rGeVeDescon.dRucRec, self.company.l10n_py_ruc)
        self.assertEqual(
            evt.rGeVeDescon.mOtEve,
            "Documento no reconocido: nunca se recibió mercadería",
        )

    # ============== Disconformidad y Notificación de Recepción ==============
    # (mismo mecanismo que 3/4; cubre los 4 ramales de _RECEIVER_EVENT_BUILDERS)

    @patch(
        "odoo.addons.l10n_py_edi_sifen.models.edi_connector"
        ".EDIConnector._sifen_get_evento"
    )
    def test_send_disconformidad_builds_correct_payload(self, mock_get_evento):
        mock_evento = self._mock_evento(mock_get_evento)
        event = self._create_event(
            event_type="disconformidad",
            motivo="Mercadería recibida con daños graves de transporte",
        )
        event.action_send_receiver_event()

        evt = self._assert_only_field_populated(mock_evento, "rGeVeDisconf")
        self.assertEqual(
            evt.rGeVeDisconf.mOtEve,
            "Mercadería recibida con daños graves de transporte",
        )

    @patch(
        "odoo.addons.l10n_py_edi_sifen.models.edi_connector"
        ".EDIConnector._sifen_get_evento"
    )
    def test_send_notificacion_recepcion_builds_correct_payload(self, mock_get_evento):
        mock_evento = self._mock_evento(mock_get_evento)
        event = self._create_event(
            event_type="notificacion_recepcion",
            tipo_receptor="2",
            fecha_emision_dte="2026-08-01 10:00:00",
            fecha_recepcion="2026-08-02 10:00:00",
            total_gs=2500000.0,
        )
        event.action_send_receiver_event()

        evt = self._assert_only_field_populated(mock_evento, "rGeVeNotRec")
        self.assertEqual(evt.rGeVeNotRec.Id, self.cdc)
        self.assertEqual(evt.rGeVeNotRec.dTotalGs, Decimal("2500000.0"))

    # ============== 11. Regresión: cancelación no afectada ==============

    @patch(
        "odoo.addons.l10n_py_edi_sifen.models.edi_connector"
        ".EDIConnector._sifen_get_evento"
    )
    def test_cancelacion_nao_afetada_por_send_receiver_event(self, mock_get_evento):
        """El método nuevo en la interfaz del conector (`send_receiver_event`)
        no debe alterar la firma/comportamiento de `cancel_document`."""
        mock_evento = self._mock_evento(mock_get_evento)
        result = self.connector.cancel_document(
            self.cdc, "Cancelación solicitada por el emisor"
        )
        self.assertTrue(result["success"])
        evt = self._assert_only_field_populated(mock_evento, "rGeVeCan")
        self.assertEqual(evt.rGeVeCan.Id, self.cdc)
