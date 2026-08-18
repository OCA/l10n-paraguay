# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "l10n_py")
class TestL10nPyEdiReceivedEvent(TransactionCase):
    """Tests del modelo `l10n_py.edi.received.event` (acuse de recibo PY).

    Sólo ejercitan la semántica de negocio del lado Odoo (validación
    condicional por tipo de evento, exclusividad de mérito, prefill desde
    factura, smart button). El armado del payload SIFEN por tipo de evento
    se prueba en `l10n_py_edi_sifen/tests/test_sifen_receiver_event.py`.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        from odoo.addons.l10n_py_edi_base.services.cdc_generator import CDCGenerator

        cls.CDCGenerator = CDCGenerator

        cls.company = cls.env.ref("base.main_company")
        cls.country_py = cls.env.ref("base.py")
        cls.company.write(
            {
                "country_id": cls.country_py.id,
                "account_fiscal_country_id": cls.country_py.id,
                "l10n_py_ruc": "80009401",
            }
        )

        cls.valid_cdc = CDCGenerator.generate(
            doc_type=1,
            ruc="80012345",
            dv="1",
            establishment="001",
            expedition_point="001",
            sequence=1,
            taxpayer_type="2",
            emission_date="2026-08-01T10:00:00",
            emission_type=1,
            security_code="123456789",
        )

        cls.partner_vendor = cls.env["res.partner"].create(
            {
                "name": "Proveedor PY Test",
                "country_id": cls.country_py.id,
                "l10n_py_ruc": "80067890",
            }
        )

        # Cuentas mínimas para poder crear una factura de proveedor.
        payable = cls.env["account.account"].search(
            [
                ("company_ids", "in", cls.company.id),
                ("account_type", "=", "liability_payable"),
            ],
            limit=1,
        )
        if not payable:
            payable = cls.env["account.account"].create(
                {
                    "name": "Cuentas por Pagar Test",
                    "code": "210001",
                    "account_type": "liability_payable",
                    "reconcile": True,
                    "company_ids": [Command.link(cls.company.id)],
                }
            )
        cls.payable_account = payable

        expense = cls.env["account.account"].search(
            [
                ("company_ids", "in", cls.company.id),
                ("account_type", "=", "expense"),
            ],
            limit=1,
        )
        if not expense:
            expense = cls.env["account.account"].create(
                {
                    "name": "Gastos Test",
                    "code": "610001",
                    "account_type": "expense",
                    "company_ids": [Command.link(cls.company.id)],
                }
            )
        cls.expense_account = expense

        cls.purchase_journal = cls.env["account.journal"].create(
            {
                "name": "Compras DS Test",
                "type": "purchase",
                "code": "CDS",
                "company_id": cls.company.id,
            }
        )

        # Conector EDI: no dependemos de demo data (`l10n_py_edi_sifen` la
        # trae, pero no debe ser un prerequisito silencioso de este test).
        cls.env["l10n_py.edi.connector"].sudo().search(
            [("company_id", "=", cls.company.id)]
        ).unlink()
        provider_type = (
            "sifen"
            if "sifen"
            in dict(cls.env["l10n_py.edi.connector"]._fields["provider_type"].selection)
            else False
        )
        cls.connector = (
            cls.env["l10n_py.edi.connector"]
            .sudo()
            .create(
                {
                    "name": "Conector Test",
                    "company_id": cls.company.id,
                    "provider_type": provider_type,
                    "environment": "test",
                }
            )
        )

    def _create_invoice(self, amount=1000000.0):
        return self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_vendor.id,
                "journal_id": self.purchase_journal.id,
                "currency_id": self.env.ref("base.PYG").id,
                "invoice_date": "2026-08-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Servicio de prueba",
                            "quantity": 1,
                            "price_unit": amount,
                            "account_id": self.expense_account.id,
                        }
                    )
                ],
            }
        )

    def _create_event(self, **vals):
        base_vals = {
            "company_id": self.company.id,
            "cdc": self.valid_cdc,
            "partner_id": self.partner_vendor.id,
        }
        base_vals.update(vals)
        return self.env["l10n_py.edi.received.event"].create(base_vals)

    # ============== 1. Validación condicional por tipo ==============

    def test_received_event_requires_type_specific_fields(self):
        """disconformidad sin motivo debe fallar al enviar; con motivo,
        pasa la validación (el conector es llamado)."""
        event = self._create_event(event_type="disconformidad")
        with patch.object(
            type(self.env["l10n_py.edi.connector"]),
            "send_receiver_event",
            return_value={"success": True, "protocol": "123"},
        ) as mock_send:
            with self.assertRaises(ValidationError):
                event.action_send_receiver_event()
            mock_send.assert_not_called()

        event.motivo = "Mercadería no fue recibida en el depósito"
        with patch.object(
            type(self.env["l10n_py.edi.connector"]),
            "send_receiver_event",
            return_value={"success": True, "protocol": "123"},
        ) as mock_send:
            event.action_send_receiver_event()
            mock_send.assert_called_once()
        self.assertEqual(event.state, "accepted")

    # ============== 2. Prefill desde move_id ==============

    def test_notificacion_recepcion_prefills_from_move(self):
        move = self._create_invoice(amount=1500000.0)
        move.l10n_py_cdc = self.valid_cdc
        pyg = self.env.ref("base.PYG")
        event = self.env["l10n_py.edi.received.event"].new(
            {
                "company_id": self.company.id,
                "event_type": "notificacion_recepcion",
                "move_id": move.id,
                "currency_id": pyg.id,
            }
        )
        event._onchange_move_id()
        self.assertEqual(event.cdc, self.valid_cdc)
        self.assertEqual(event.partner_id, self.partner_vendor)
        self.assertAlmostEqual(event.total_gs, move.amount_total)
        self.assertEqual(
            event.fecha_emision_dte.date(),
            move.invoice_date,
        )

    # ============== 5/6/7. Estados tras el envío ==============

    def test_send_success_sets_accepted_and_logs(self):
        event = self._create_event(
            event_type="conformidad",
            tipo_conformidad="1",
        )
        with patch.object(
            type(self.env["l10n_py.edi.connector"]),
            "send_receiver_event",
            return_value={"success": True, "protocol": "PROTO-1"},
        ):
            event.action_send_receiver_event()
        self.assertEqual(event.state, "accepted")
        self.assertEqual(event.protocolo_sifen, "PROTO-1")
        logs = self.env["l10n_py.edi.log"].search(
            [
                ("l10n_py_received_event_id", "=", event.id),
                ("operation_type", "=", "event"),
            ]
        )
        self.assertTrue(logs)
        self.assertTrue(logs[0].success)

    def test_send_rejection_sets_rejected_with_message(self):
        event = self._create_event(
            event_type="conformidad",
            tipo_conformidad="1",
        )
        with patch.object(
            type(self.env["l10n_py.edi.connector"]),
            "send_receiver_event",
            return_value={"success": False, "error": "[100] CDC no existe"},
        ):
            event.action_send_receiver_event()
        self.assertEqual(event.state, "rejected")
        self.assertIn("CDC no existe", event.error_message)
        self.assertFalse(event.protocolo_sifen)

    def test_send_transport_error_sets_error_state(self):
        event = self._create_event(
            event_type="conformidad",
            tipo_conformidad="1",
        )
        with patch.object(
            type(self.env["l10n_py.edi.connector"]),
            "send_receiver_event",
            side_effect=ConnectionError("timeout mTLS"),
        ):
            with self.assertRaises(UserError):
                event.action_send_receiver_event()
        self.assertEqual(event.state, "error")
        self.assertIn("timeout mTLS", event.error_message)

        # Reenvío manual disponible después de un error.
        event.action_reset_to_draft()
        self.assertEqual(event.state, "draft")

    # ============== 8. Exclusividad de mérito ==============

    def test_exclusividade_merito_bloqueia_segundo_evento_aceito(self):
        cdc = self.valid_cdc
        event_conf = self._create_event(
            cdc=cdc, event_type="conformidad", tipo_conformidad="1"
        )
        with patch.object(
            type(self.env["l10n_py.edi.connector"]),
            "send_receiver_event",
            return_value={"success": True, "protocol": "P1"},
        ):
            event_conf.action_send_receiver_event()
        self.assertEqual(event_conf.state, "accepted")

        event_disconf = self._create_event(
            cdc=cdc,
            event_type="disconformidad",
            motivo="Producto con defecto de fabricación grave",
        )
        with patch.object(
            type(self.env["l10n_py.edi.connector"]),
            "send_receiver_event",
            return_value={"success": True, "protocol": "P2"},
        ):
            with self.assertRaises(ValidationError):
                event_disconf.action_send_receiver_event()

        # notificacion_recepcion NO entra en la exclusión de mérito.
        event_notrec = self._create_event(
            cdc=cdc,
            event_type="notificacion_recepcion",
            tipo_receptor="1",
            fecha_emision_dte="2026-08-01 10:00:00",
            fecha_recepcion="2026-08-02 10:00:00",
            total_gs=1000000.0,
        )
        with patch.object(
            type(self.env["l10n_py.edi.connector"]),
            "send_receiver_event",
            return_value={"success": True, "protocol": "P3"},
        ):
            event_notrec.action_send_receiver_event()
        self.assertEqual(event_notrec.state, "accepted")

    # ============== 9. CDC inválido ==============

    def test_cdc_invalido_rejeitado_na_validacao(self):
        with patch.object(
            type(self.env["l10n_py.edi.connector"]),
            "send_receiver_event",
        ) as mock_send:
            with self.assertRaises(ValidationError):
                self._create_event(
                    cdc="0" * 43 + "9",  # 44 dígitos, DV incorrecto
                    event_type="conformidad",
                    tipo_conformidad="1",
                )
            mock_send.assert_not_called()

    # ============== 10. Smart button en account.move ==============

    def test_smart_button_conta_eventos_da_fatura(self):
        move = self._create_invoice()
        move.l10n_py_cdc = self.valid_cdc
        self._create_event(
            event_type="conformidad", tipo_conformidad="1", move_id=move.id
        )
        self._create_event(
            event_type="disconformidad",
            motivo="Segundo evento de prueba para el contador",
            move_id=move.id,
        )
        self.assertEqual(move.l10n_py_received_event_count, 2)
        action = move.action_open_received_events()
        self.assertEqual(action["res_model"], "l10n_py.edi.received.event")
        self.assertEqual(action["domain"], [("move_id", "=", move.id)])

    # ============== Sem reintento automático ==============

    def test_no_puede_reenviar_desde_draft_o_accepted(self):
        event = self._create_event(event_type="conformidad", tipo_conformidad="1")
        with self.assertRaises(UserError):
            event.action_reset_to_draft()

    # ============== Unlink bloqueado fuera de draft ==============

    def test_unlink_bloqueado_fuera_de_draft(self):
        event = self._create_event(
            event_type="conformidad",
            tipo_conformidad="1",
        )
        with patch.object(
            type(self.env["l10n_py.edi.connector"]),
            "send_receiver_event",
            return_value={"success": True, "protocol": "P1"},
        ):
            event.action_send_receiver_event()
        with self.assertRaises(UserError):
            event.unlink()
