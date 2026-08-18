# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import date, timedelta
from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "l10n_py")
class TestEDIBatch(TransactionCase):
    """Envío en lote SIFEN: particionamiento, estado intermediario,
    falla parcial por documento e idempotencia (no reenviar lo ya enviado).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_py = cls.env.ref("base.py")

        cls.doc_type_invoice = cls.env["l10n_latam.document.type"].search(
            [("country_id", "=", cls.country_py.id), ("code", "=", "1")],
            limit=1,
        )
        if not cls.doc_type_invoice:
            cls.doc_type_invoice = cls.env["l10n_latam.document.type"].create(
                {
                    "name": "Factura",
                    "code": "1",
                    "country_id": cls.country_py.id,
                    "internal_type": "invoice",
                }
            )

        cls.company = cls.env["res.company"].create(
            {
                "name": "Test Company EDI Batch",
                "country_id": cls.country_py.id,
                "l10n_py_ruc": "80009401",
            }
        )

        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Cliente Test Lote",
                "is_company": True,
                "country_id": cls.country_py.id,
                "l10n_py_ruc": "80009402",
                "l10n_py_taxpayer_type": "1",
                "street": "Test Street 123",
            }
        )

        today = date.today()
        cls.authorization = cls.env["account.authorization"].create(
            {
                "name": "12345678",
                "date_from": today - timedelta(days=30),
                "date_to": today + timedelta(days=335),
                "invoice_number_from": 1,
                "invoice_number_to": 100000,
                "establishment": "001",
                "expedition_point": "001",
                "l10n_latam_document_type_id": cls.doc_type_invoice.id,
                "company_id": cls.company.id,
            }
        )

        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Test Journal EDI Batch",
                "type": "sale",
                "code": "TEDIB",
                "company_id": cls.company.id,
                "l10n_py_establishment": "001",
                "l10n_py_point": "001",
                "l10n_py_authorization_id": cls.authorization.id,
            }
        )

        cls.account_income = cls.env["account.account"].search(
            [
                ("company_ids", "in", cls.company.id),
                ("account_type", "=", "income"),
            ],
            limit=1,
        )
        if not cls.account_income:
            cls.account_income = cls.env["account.account"].create(
                {
                    "name": "Ingresos Lote",
                    "code": "400199",
                    "account_type": "income",
                    "company_ids": [Command.link(cls.company.id)],
                }
            )

        cls.account_receivable = cls.env["account.account"].search(
            [
                ("company_ids", "in", cls.company.id),
                ("account_type", "=", "asset_receivable"),
            ],
            limit=1,
        )
        if not cls.account_receivable:
            cls.account_receivable = cls.env["account.account"].create(
                {
                    "name": "Cuentas por Cobrar Lote",
                    "code": "110199",
                    "account_type": "asset_receivable",
                    "reconcile": True,
                    "company_ids": [Command.link(cls.company.id)],
                }
            )
        cls.partner.property_account_receivable_id = cls.account_receivable

        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Product Lote",
                "type": "consu",
                "default_code": "TESTLOTE001",
                "l10n_py_ncm_code": "01012100",
            }
        )

        # Producto SIN NCM, usado para forzar una falla de validación (item
        # inválido, debe ser rechazado ANTES de llegar al SIFEN).
        cls.product_invalido = cls.env["product.product"].create(
            {
                "name": "Test Product Sin NCM",
                "type": "consu",
                "default_code": "TESTLOTE002",
                "l10n_py_ncm_code": False,
            }
        )

        cls.connector = cls.env["l10n_py.edi.connector"].create(
            {
                "name": "SIFEN Test Lote",
                "company_id": cls.company.id,
                "provider_type": "sifen",
                "environment": "test",
            }
        )

    def _create_move(self, product=None, to_send=True):
        """Crear un account.move válido para EDI sin pasar por action_post.

        _validate_edi_data / _prepare_edi_document_data no requieren que el
        documento esté contabilizado (posted); alcanza con los datos
        maestros (RUC, timbrado, NCM) para probar el envío en lote sin el
        costo de una contabilización real por cada uno de los 120 docs del
        test de particionamiento.
        """
        product = product or self.product
        move = (
            self.env["account.move"]
            .with_company(self.company)
            .create(
                {
                    "move_type": "out_invoice",
                    "partner_id": self.partner.id,
                    "journal_id": self.journal.id,
                    "company_id": self.company.id,
                    "invoice_date": date.today(),
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "name": "Producto Test",
                                "product_id": product.id,
                                "quantity": 1,
                                "price_unit": 100000.0,
                                "account_id": self.account_income.id,
                            },
                        )
                    ],
                }
            )
        )
        if to_send:
            move.l10n_py_edi_status = "to_send"
        return move

    # ============== Particionamiento ==============

    @patch(
        "odoo.addons.l10n_py_edi_sifen.models.edi_connector"
        ".EDIConnector._sifen_send_batch"
    )
    def test_action_send_edi_batch_particiona_en_chunks_de_50(self, mock_send_batch):
        """120 documentos to_send -> 3 llamadas (50, 50, 20)."""
        moves = self.env["account.move"]
        for _i in range(120):
            moves |= self._create_move()

        call_sizes = []

        def _fake_send_batch(invoice_data_list):
            call_sizes.append(len(invoice_data_list))
            return {
                "success": True,
                "result": {
                    "batch_protocol": f"PROT{len(call_sizes)}",
                    "cdc_list": [
                        f"CDC{len(call_sizes)}-{i}"
                        for i in range(len(invoice_data_list))
                    ],
                },
            }

        mock_send_batch.side_effect = _fake_send_batch

        moves.action_send_edi_batch()

        self.assertEqual(mock_send_batch.call_count, 3)
        self.assertEqual(call_sizes, [50, 50, 20])
        self.assertTrue(all(m.l10n_py_edi_status == "batch_sent" for m in moves))

    def test_action_send_edi_batch_ignora_docs_fora_de_to_send(self):
        """Documentos que no están en to_send no entran a ningún chunk."""
        move_to_send = self._create_move()
        move_already_sent = self._create_move(to_send=False)
        move_already_sent.l10n_py_edi_status = "accepted"

        selection = move_to_send | move_already_sent

        with patch(
            "odoo.addons.l10n_py_edi_sifen.models.edi_connector"
            ".EDIConnector._sifen_send_batch"
        ) as mock_send_batch:
            mock_send_batch.return_value = {
                "success": True,
                "result": {"batch_protocol": "PROT1", "cdc_list": ["CDC1"]},
            }
            selection.action_send_edi_batch()

        mock_send_batch.assert_called_once()
        self.assertEqual(len(mock_send_batch.call_args[0][0]), 1)
        self.assertEqual(move_to_send.l10n_py_edi_status, "batch_sent")
        # El documento ya aceptado permanece intacto: no se reenvía.
        self.assertEqual(move_already_sent.l10n_py_edi_status, "accepted")

    def test_reenvio_documento_ya_enviado_es_bloqueado(self):
        """Reenviar la acción sobre un doc ya 'batch_sent' no lo reenvía."""
        move = self._create_move()
        move.write(
            {"l10n_py_edi_status": "batch_sent", "l10n_py_edi_batch_id": "OLDPROT"}
        )

        with patch(
            "odoo.addons.l10n_py_edi_sifen.models.edi_connector"
            ".EDIConnector._sifen_send_batch"
        ) as mock_send_batch:
            from odoo.exceptions import UserError

            with self.assertRaises(UserError):
                move.action_send_edi_batch()

        mock_send_batch.assert_not_called()
        self.assertEqual(move.l10n_py_edi_batch_id, "OLDPROT")

    def test_send_batch_seta_batch_id_y_status_batch_sent(self):
        """dProtConsLote=123 del mock -> batch_id=123, status batch_sent."""
        move1 = self._create_move()
        move2 = self._create_move()

        with patch(
            "odoo.addons.l10n_py_edi_sifen.models.edi_connector"
            ".EDIConnector._sifen_send_batch"
        ) as mock_send_batch:
            mock_send_batch.return_value = {
                "success": True,
                "result": {
                    "batch_protocol": "123",
                    "cdc_list": ["CDC-A", "CDC-B"],
                },
            }
            (move1 | move2).action_send_edi_batch()

        self.assertEqual(move1.l10n_py_edi_batch_id, "123")
        self.assertEqual(move1.l10n_py_edi_status, "batch_sent")
        self.assertEqual(move2.l10n_py_edi_batch_id, "123")
        self.assertEqual(move2.l10n_py_edi_status, "batch_sent")

    def test_send_batch_falla_de_transporte_no_marca_ningun_doc(self):
        """Excepción en enviar_lote -> ningún doc del chunk queda batch_sent."""
        move1 = self._create_move()
        move2 = self._create_move()

        with patch(
            "odoo.addons.l10n_py_edi_sifen.models.edi_connector"
            ".EDIConnector._sifen_send_batch"
        ) as mock_send_batch:
            mock_send_batch.side_effect = Exception("timeout de red")
            (move1 | move2).action_send_edi_batch()

        self.assertEqual(move1.l10n_py_edi_status, "to_send")
        self.assertEqual(move2.l10n_py_edi_status, "to_send")
        self.assertFalse(move1.l10n_py_edi_batch_id)
        self.assertFalse(move2.l10n_py_edi_batch_id)

    def test_documento_invalido_es_rechazado_antes_de_llegar_a_sifen(self):
        """Producto sin NCM -> rechazado en validación, nunca llega al payload."""
        move_valido = self._create_move()
        move_invalido = self._create_move(product=self.product_invalido)

        with patch(
            "odoo.addons.l10n_py_edi_sifen.models.edi_connector"
            ".EDIConnector._sifen_send_batch"
        ) as mock_send_batch:
            mock_send_batch.return_value = {
                "success": True,
                "result": {"batch_protocol": "PROT1", "cdc_list": ["CDC1"]},
            }
            (move_valido | move_invalido).action_send_edi_batch()

        # Sólo 1 documento llegó al payload (el inválido fue filtrado antes).
        self.assertEqual(len(mock_send_batch.call_args[0][0]), 1)
        self.assertEqual(move_valido.l10n_py_edi_status, "batch_sent")
        self.assertEqual(move_invalido.l10n_py_edi_status, "rejected")
        self.assertIn("NCM", move_invalido.l10n_py_edi_message)

    # ============== Consulta de lote / falla parcial ==============

    def test_check_batch_status_falla_parcial_marca_por_documento(self):
        """3 aceptados + 2 rechazados en el mismo lote -> por documento."""
        moves = [self._create_move() for _ in range(5)]
        for i, move in enumerate(moves):
            move.write(
                {
                    "l10n_py_edi_status": "batch_sent",
                    "l10n_py_edi_batch_id": "PROT-PARCIAL",
                    "l10n_py_cdc": f"CDC-{i}",
                }
            )

        fake_documents = [
            {"cdc": "CDC-0", "status": "accepted", "message": "OK"},
            {"cdc": "CDC-1", "status": "accepted", "message": "OK"},
            {"cdc": "CDC-2", "status": "accepted", "message": "OK"},
            {"cdc": "CDC-3", "status": "rejected", "message": "[123] Error X"},
            {"cdc": "CDC-4", "status": "rejected", "message": "[124] Error Y"},
        ]

        with patch(
            "odoo.addons.l10n_py_edi_sifen.models.edi_connector"
            ".EDIConnector._sifen_check_batch_status"
        ) as mock_check:
            mock_check.return_value = {
                "success": True,
                "result": {"pending": False, "documents": fake_documents},
            }
            self.env["account.move"]._l10n_py_apply_batch_status("PROT-PARCIAL")

        statuses = {m.l10n_py_cdc: m.l10n_py_edi_status for m in moves}
        self.assertEqual(statuses["CDC-0"], "accepted")
        self.assertEqual(statuses["CDC-1"], "accepted")
        self.assertEqual(statuses["CDC-2"], "accepted")
        self.assertEqual(statuses["CDC-3"], "rejected")
        self.assertEqual(statuses["CDC-4"], "rejected")
        # Ninguno queda residual en batch_sent.
        self.assertFalse(any(m.l10n_py_edi_status == "batch_sent" for m in moves))

    def test_check_batch_status_pendiente_mantiene_batch_sent(self):
        """Lote aún en procesamiento -> todos permanecen batch_sent, sin error."""
        moves = [self._create_move() for _ in range(2)]
        for i, move in enumerate(moves):
            move.write(
                {
                    "l10n_py_edi_status": "batch_sent",
                    "l10n_py_edi_batch_id": "PROT-PENDIENTE",
                    "l10n_py_cdc": f"CDC-P{i}",
                }
            )

        with patch(
            "odoo.addons.l10n_py_edi_sifen.models.edi_connector"
            ".EDIConnector._sifen_check_batch_status"
        ) as mock_check:
            mock_check.return_value = {
                "success": True,
                "result": {"pending": True, "documents": []},
            }
            self.env["account.move"]._l10n_py_apply_batch_status("PROT-PENDIENTE")

        for move in moves:
            self.assertEqual(move.l10n_py_edi_status, "batch_sent")
            self.assertFalse(move.l10n_py_edi_message)

    def test_cron_check_edi_status_consulta_un_lote_por_batch_id_distinto(self):
        """2 lotes distintos -> _l10n_py_apply_batch_status llamado 2 veces."""
        moves_a = [self._create_move() for _ in range(3)]
        moves_b = [self._create_move() for _ in range(2)]
        for i, move in enumerate(moves_a):
            move.write(
                {
                    "l10n_py_edi_status": "batch_sent",
                    "l10n_py_edi_batch_id": "PROT-A",
                    "l10n_py_cdc": f"CDC-A{i}",
                }
            )
        for i, move in enumerate(moves_b):
            move.write(
                {
                    "l10n_py_edi_status": "batch_sent",
                    "l10n_py_edi_batch_id": "PROT-B",
                    "l10n_py_cdc": f"CDC-B{i}",
                }
            )

        with patch(
            "odoo.addons.l10n_py_edi_base.models.account_move"
            ".AccountMove._l10n_py_apply_batch_status"
        ) as mock_apply:
            self.env["account.move"]._cron_check_edi_status()

        called_batch_ids = sorted(c.args[0] for c in mock_apply.call_args_list)
        self.assertEqual(mock_apply.call_count, 2)
        self.assertEqual(called_batch_ids, ["PROT-A", "PROT-B"])

    # ============== Regresión: flujo individual intacto ==============

    def test_flujo_individual_no_afectado_por_batch(self):
        """action_send_edi() de un único doc no pasa por el camino de lote."""
        move = self._create_move()

        with (
            patch(
                "odoo.addons.l10n_py_edi_sifen.models.edi_connector"
                ".EDIConnector._sifen_send_document"
            ) as mock_send_document,
            patch(
                "odoo.addons.l10n_py_edi_sifen.models.edi_connector"
                ".EDIConnector._sifen_send_batch"
            ) as mock_send_batch,
        ):
            mock_send_document.return_value = {
                "success": True,
                "result": {
                    "deList": [{"cdc": "0" * 44, "qr": "", "xml": "<rDE></rDE>"}]
                },
            }
            move.action_send_edi()

        mock_send_batch.assert_not_called()
        self.assertEqual(move.l10n_py_edi_status, "accepted")
        self.assertFalse(move.l10n_py_edi_batch_id)
