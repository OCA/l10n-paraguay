# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from pysifen.de.bindings.v150.evento_types_v150 import TiTiDeev

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

EVENTO = (
    "odoo.addons.l10n_py_edi_sifen.models.edi_connector.EDIConnector._sifen_get_evento"
)


@tagged("post_install", "-at_install")
class TestSIFENInutilization(TransactionCase):
    """Inutilization sends the authorization's own document type and numbering."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.company.write({"l10n_py_ruc": "80012345"})
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
        today = fields.Date.today()
        cls.authorization_nr = cls.env["account.authorization"].create(
            {
                "name": "12345678",
                "date_from": today - timedelta(days=10),
                "date_to": today + timedelta(days=355),
                "invoice_number_from": 1,
                "invoice_number_to": 1000,
                "establishment": "003",
                "expedition_point": "002",
                "l10n_latam_document_type_id": cls.env.ref(
                    "l10n_py_account.dc_py_nr"
                ).id,
                "company_id": cls.company.id,
            }
        )

    def _send(self, authorization):
        inutilization = self.env["l10n_py.number.inutilization"].create(
            {
                "authorization_id": authorization.id,
                "number_from": 5,
                "number_to": 9,
                "motive": "Saltos en la numeración",
            }
        )
        sent = []

        def enviar_evento(grupo):
            sent.append(grupo.rGesEve[0].rEve.gGroupTiEvt.rGeVeInu)
            return SimpleNamespace(gResProcEVe=SimpleNamespace(dEstRes="Aprobado"))

        with patch(EVENTO) as get_evento:
            get_evento.return_value.enviar_evento.side_effect = enviar_evento
            inutilization.action_send()
        return inutilization, sent

    def test_delivery_note_range_is_inutilized_as_delivery_note(self):
        """A Nota de Remisión range must not be sent as Factura (iTiDE 1)."""
        inutilization, sent = self._send(self.authorization_nr)
        self.assertEqual(inutilization.state, "accepted")
        event = sent[0]
        self.assertEqual(event.iTiDE, TiTiDeev.VALUE_7)
        self.assertEqual(event.dNumTim, "12345678")
        self.assertEqual(event.dEst, "003")
        self.assertEqual(event.dPunExp, "002")
        self.assertEqual(event.dNumIn, "0000005")
        self.assertEqual(event.dNumFin, "0000009")

    def test_every_document_type_maps_to_itself(self):
        for code in ("1", "4", "5", "6", "7"):
            with self.subTest(code=code):
                self.assertEqual(
                    self.connector._sifen_inutilization_doc_type(code).value,
                    int(code),
                )

    def test_invalid_document_type_is_refused(self):
        for value in (None, "", "X", 99):
            with self.subTest(value=value), self.assertRaises(UserError):
                self.connector._sifen_inutilization_doc_type(value)
