from odoo.tests import tagged

from .test_libro_common import LibroCommonCase


@tagged("post_install", "-at_install", "l10n_py", "l10n_py_libros")
class TestLibroIngresosEgresos(LibroCommonCase):
    def _create_ingresos_line(self, libro, **vals):
        base_vals = {
            "libro_id": libro.id,
            "f_tipo_comprobante": "203",
            "f_fecha_emision": "2026-01-15",
            "f_numero_comprobante": "0000001",
            "f_tipo_identificacion": "11",
            "f_numero_identificacion": "80011111",
            "f_nombre_razon_social": "Cliente Ingresos Test",
            "f_monto_gravado": 1000,
            "f_monto_no_gravado_exonerado": 0,
            "f_monto_total": 1000,
            "f_imputa_ire": "S",
            "f_imputa_irp_rsp": "N",
        }
        base_vals.update(vals)
        return self.env["l10n_py.libro.line"].create(base_vals)

    def _create_egresos_line(self, libro, **vals):
        base_vals = {
            "libro_id": libro.id,
            "f_tipo_comprobante": "201",
            "f_fecha_emision": "2026-01-15",
            "f_numero_comprobante": "0000001",
            "f_tipo_identificacion": "11",
            "f_numero_identificacion": "80022222",
            "f_nombre_razon_social": "Proveedor Egresos Test",
            "f_monto_total": 1000,
            "f_imputa_iva": "N",
            "f_imputa_ire": "S",
            "f_imputa_irp_rsp": "N",
            "f_no_imputa": "N",
        }
        base_vals.update(vals)
        return self.env["l10n_py.libro.line"].create(base_vals)

    def test_ingresos_203_lancamento_manual(self):
        libro = self._create_libro("ingresos")
        line = self._create_ingresos_line(libro)
        self.assertEqual(line.state, "ok", line.error_message)
        self.assertEqual(line.tipo_registro, "ingresos")

    def test_ingresos_208_periodo_mm_aaaa(self):
        libro = self._create_libro("ingresos")
        line = self._create_ingresos_line(
            libro,
            f_tipo_comprobante="208",
            f_periodo_mm_aaaa="01/2026",
            f_monto_gravado=1000,
            f_monto_no_gravado_exonerado=0,
            f_monto_total=1000,
        )
        self.assertEqual(line.state, "ok", line.error_message)
        line.f_periodo_mm_aaaa = False
        self.assertEqual(line.state, "erro")

    def test_egresos_201_lancamento_manual(self):
        libro = self._create_libro("egresos")
        line = self._create_egresos_line(libro)
        self.assertEqual(line.state, "ok", line.error_message)
        self.assertEqual(line.tipo_registro, "egresos")

    def test_egresos_207_imputa_iva_s_permitido(self):
        libro = self._create_libro("egresos")
        line = self._create_egresos_line(
            libro, f_tipo_comprobante="207", f_imputa_iva="S"
        )
        self.assertEqual(line.state, "ok", line.error_message)

    def test_egresos_nao_207_imputa_iva_s_marca_erro(self):
        libro = self._create_libro("egresos")
        line = self._create_egresos_line(
            libro, f_tipo_comprobante="201", f_imputa_iva="S"
        )
        self.assertEqual(line.state, "erro")

    def test_nenhuma_obrigacao_imputada_marca_linha_em_erro(self):
        libro = self._create_libro("egresos")
        line = self._create_egresos_line(
            libro, f_imputa_iva="N", f_imputa_ire="N", f_imputa_irp_rsp="N"
        )
        self.assertEqual(line.state, "erro")

    def test_periodo_vazio_confirma_sem_arquivo(self):
        libro = self._create_libro("ingresos")
        libro.action_confirm()
        self.assertEqual(libro.state, "confirmed")
        self.assertFalse(libro.l10n_py_libro_attachment_ids)
