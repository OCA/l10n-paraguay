import base64
import io
import zipfile

from odoo.exceptions import UserError
from odoo.tests import tagged

from ..models.l10n_py_libro_serializer import FIELD_ORDER
from .test_libro_common import LibroCommonCase


@tagged("post_install", "-at_install", "l10n_py", "l10n_py_libros")
class TestLibroSerializer(LibroCommonCase):
    def _bulk_create_egresos_lines(self, libro, count):
        Line = self.env["l10n_py.libro.line"]
        vals_list = []
        for i in range(count):
            vals_list.append(
                {
                    "libro_id": libro.id,
                    "f_tipo_comprobante": "210",
                    "f_fecha_emision": "2026-01-15",
                    "f_numero_comprobante": f"{i + 1:07d}",
                    "f_tipo_identificacion": "11",
                    "f_numero_identificacion": "80011111",
                    "f_nombre_razon_social": f"Test {i}",
                    "f_monto_total": 1000,
                    "f_imputa_ire": "S",
                    "f_especificar_tipo_documento": "Otro",
                }
            )
        Line.create(vals_list)

    def test_lote_5001_lineas_dois_zips_xxxxx_algoritmo(self):
        libro = self._create_libro("egresos")
        self._bulk_create_egresos_lines(libro, 5001)
        self.assertEqual(libro.error_line_count, 0)
        libro.action_download_zip()
        self.assertEqual(len(libro.l10n_py_libro_attachment_ids), 2)
        total_lines = 0
        for attachment in libro.l10n_py_libro_attachment_ids:
            content = base64.b64decode(attachment.datas)
            with zipfile.ZipFile(io.BytesIO(content)) as zip_file:
                names = zip_file.namelist()
                self.assertEqual(len(names), 1)
                self.assertTrue(attachment.name.endswith(".zip"))
                # Mismo basename (RUC_REG_periodo_XXXXX), extensión distinta
                # (.csv/.txt dentro del ZIP, .zip para el propio archivo).
                self.assertEqual(
                    names[0].rsplit(".", 1)[0],
                    attachment.name.rsplit(".", 1)[0],
                )
                with zip_file.open(names[0]) as f:
                    total_lines += len(f.readlines())
        self.assertEqual(total_lines, 5001)

    def test_reenvio_gera_xxxxx_diferente(self):
        libro = self._create_libro("egresos")
        self._bulk_create_egresos_lines(libro, 1)
        libro.action_download_zip()
        first_names = set(libro.l10n_py_libro_attachment_ids.mapped("name"))
        libro.action_download_zip()
        second_names = set(libro.l10n_py_libro_attachment_ids.mapped("name"))
        self.assertTrue(second_names - first_names)

    def test_lote_manual_override_usado_no_xxxxx(self):
        libro = self._create_libro("egresos", lote_manual_override="ABCDE")
        self._bulk_create_egresos_lines(libro, 1)
        libro.action_download_zip()
        self.assertIn("ABCDE", libro.l10n_py_libro_attachment_ids[0].name)

    def test_lote_manual_override_com_multiplos_sublotes_rejeitado(self):
        libro = self._create_libro("egresos", lote_manual_override="ABCDE")
        self._bulk_create_egresos_lines(libro, 5001)
        with self.assertRaises(UserError):
            libro.action_download_zip()

    def test_nome_arquivo_955_e_956(self):
        libro_955 = self._create_libro("egresos", obligacion="955", year=2026, month=1)
        self.assertTrue(
            libro_955._get_file_basename("E0000").startswith("80009401_REG_012026_")
        )
        libro_956 = self._create_libro("egresos", obligacion="956", year=2026, month=0)
        self.assertTrue(
            libro_956._get_file_basename("E0000").startswith("80009401_REG_2026_")
        )

    def test_separador_csv_e_delimitador_txt(self):
        libro_coma = self._create_libro("egresos", separador="coma")
        self._bulk_create_egresos_lines(libro_coma, 1)
        content_coma = libro_coma._serialize_chunk(libro_coma.line_ids)
        self.assertIn(b",", content_coma)

        libro_pyc = self._create_libro("egresos", separador="punto_y_coma", month=2)
        self._bulk_create_egresos_lines(libro_pyc, 1)
        content_pyc = libro_pyc._serialize_chunk(libro_pyc.line_ids)
        self.assertIn(b";", content_pyc)

        libro_txt = self._create_libro("egresos", formato_archivo="txt", month=3)
        self._bulk_create_egresos_lines(libro_txt, 1)
        content_txt = libro_txt._serialize_chunk(libro_txt.line_ids)
        self.assertIn(b"\t", content_txt)

    def test_field_order_por_tipo_registro(self):
        self.assertEqual(len(FIELD_ORDER["ventas"]), 19)
        self.assertEqual(len(FIELD_ORDER["compras"]), 20)
        self.assertEqual(len(FIELD_ORDER["ingresos"]), 15)
        self.assertEqual(len(FIELD_ORDER["egresos"]), 18)

    def test_attachment_vinculado_ao_libro(self):
        libro = self._create_libro("egresos")
        self._bulk_create_egresos_lines(libro, 1)
        libro.action_download_zip()
        attachment = libro.l10n_py_libro_attachment_ids
        self.assertEqual(attachment.res_model, "l10n_py.libro")
        self.assertEqual(attachment.res_id, libro.id)

    def test_action_reopen_registra_no_chatter(self):
        libro = self._create_libro("egresos")
        libro.state = "confirmed"
        message_count = len(libro.message_ids)
        libro.action_reopen()
        self.assertEqual(libro.state, "generated")
        self.assertGreater(len(libro.message_ids), message_count)
