# l10n_py_libros/models/l10n_py_libro_line.py

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

TIPO_COMPROBANTE_SELECTION = [
    ("101", "101 - Autofactura"),
    ("102", "102 - Boleta Transporte Público"),
    ("103", "103 - Boleta de Venta"),
    ("104", "104 - Boleta Resimple"),
    ("105", "105 - Boletos de Loterías/Juegos de Azar"),
    ("106", "106 - Boleto/Ticket Transporte Aéreo"),
    ("107", "107 - Despacho de Importación"),
    ("108", "108 - Entrada Espectáculos Públicos"),
    ("109", "109 - Factura"),
    ("110", "110 - Nota de Crédito"),
    ("111", "111 - Nota de Débito"),
    ("112", "112 - Ticket Máquina Registradora"),
    ("201", "201 - Comprobante de Egresos por Compras a Crédito"),
    ("202", "202 - Comprobante del Exterior Legalizado"),
    ("203", "203 - Comprobante de Ingreso por Ventas a Crédito"),
    ("204", "204 - Comprobante Ingresos Entidades Públicas/Religiosas"),
    ("205", "205 - Extracto de Cuenta - Billetaje Electrónico"),
    ("206", "206 - Extracto de Cuenta de IPS"),
    ("207", "207 - Extracto de Cuenta TC/TD"),
    ("208", "208 - Liquidación de Salario"),
    ("209", "209 - Otros Comprobantes de Egresos"),
    ("210", "210 - Otros Comprobantes de Ingresos"),
    ("211", "211 - Transferencias o Giros Bancarios/Boleta de Depósito"),
]

ZERO_BREAKDOWN_CODES = {"101", "104", "105", "112"}


class L10nPyLibroLine(models.Model):
    _name = "l10n_py.libro.line"
    _description = "Línea de Libro DNIT"
    _order = "id"

    libro_id = fields.Many2one(
        "l10n_py.libro", required=True, ondelete="cascade", index=True
    )
    tipo_registro = fields.Selection(
        related="libro_id.tipo_registro", store=True, string="Tipo de Registro"
    )
    move_id = fields.Many2one("account.move", string="Comprobante de Origen")
    payment_id = fields.Many2one("account.payment", string="Pago de Origen")

    manual_override = fields.Boolean(
        string="Editado manualmente",
        default=False,
        help="Marcado automáticamente quando o usuário edita um campo f_* "
        "de uma linha derivada de account.move: impede que "
        "action_generate_lines sobrescreva o valor na regeneração.",
    )

    state = fields.Selection(
        [("ok", "Ok"), ("erro", "Error")],
        compute="_compute_state",
        store=True,
        default="ok",
    )
    error_message = fields.Text(compute="_compute_state", store=True)

    # Campos comunes
    f_tipo_identificacion = fields.Char(size=2)
    f_numero_identificacion = fields.Char(size=20)
    f_nombre_razon_social = fields.Char(size=250)
    f_tipo_comprobante = fields.Selection(TIPO_COMPROBANTE_SELECTION)
    f_fecha_emision = fields.Date()
    f_periodo_mm_aaaa = fields.Char(size=7)
    f_timbrado = fields.Char(size=8)
    f_numero_comprobante = fields.Char(size=20)
    f_monto_total = fields.Integer()
    f_condicion = fields.Selection([("1", "Contado"), ("2", "Crédito")])
    f_moneda_extranjera = fields.Selection([("S", "Sí"), ("N", "No")], default="N")
    f_imputa_ire = fields.Selection([("S", "Sí"), ("N", "No")], default="N")
    f_imputa_irp_rsp = fields.Selection([("S", "Sí"), ("N", "No")], default="N")
    f_especificar_tipo_documento = fields.Char(size=50)

    # Ventas/Compras
    f_monto_gravado_10 = fields.Integer()
    f_monto_gravado_5 = fields.Integer()
    f_monto_exento = fields.Integer()
    f_imputa_iva = fields.Selection([("S", "Sí"), ("N", "No")], default="N")
    f_comprobante_asociado_numero = fields.Char(size=20)
    f_comprobante_asociado_timbrado = fields.Char(size=8)

    # Compras/Egresos
    f_no_imputa = fields.Selection([("S", "Sí"), ("N", "No")], default="N")

    # Ingresos
    f_monto_gravado = fields.Integer()
    f_monto_no_gravado_exonerado = fields.Integer()

    # Egresos
    f_numero_cuenta = fields.Char(size=30)
    f_banco = fields.Char(size=250)
    f_empleador_ips = fields.Char(size=30)

    @api.constrains(
        "f_monto_total",
        "f_monto_gravado_10",
        "f_monto_gravado_5",
        "f_monto_exento",
        "f_monto_gravado",
        "f_monto_no_gravado_exonerado",
    )
    def _check_montos_no_negativos(self):
        for line in self:
            for field_name in (
                "f_monto_total",
                "f_monto_gravado_10",
                "f_monto_gravado_5",
                "f_monto_exento",
                "f_monto_gravado",
                "f_monto_no_gravado_exonerado",
            ):
                value = line[field_name]
                if value and value < 0:
                    raise ValidationError(
                        _("Los montos de la línea del libro no pueden ser negativos.")
                    )

    def write(self, vals):
        f_fields = [k for k in vals if k.startswith("f_")]
        if f_fields and not self.env.context.get("l10n_py_libro_regenerating"):
            for line in self:
                if line.move_id:
                    super(L10nPyLibroLine, line).write(dict(vals, manual_override=True))
                else:
                    super(L10nPyLibroLine, line).write(vals)
            return True
        return super().write(vals)

    def action_view_source_document(self):
        self.ensure_one()
        if self.move_id:
            return {
                "type": "ir.actions.act_window",
                "res_model": "account.move",
                "view_mode": "form",
                "res_id": self.move_id.id,
            }
        if self.payment_id:
            return {
                "type": "ir.actions.act_window",
                "res_model": "account.payment",
                "view_mode": "form",
                "res_id": self.payment_id.id,
            }
        return False

    def action_restore_generated_values(self):
        for line in self:
            line.with_context(l10n_py_libro_regenerating=True).write(
                {"manual_override": False}
            )
            line.libro_id.action_generate_lines(line_ids=line)

    def action_fill_from_source(self):
        for line in self:
            source = line.move_id or (
                line.payment_id.move_id if line.payment_id else False
            )
            if not source:
                continue
            line.with_context(l10n_py_libro_regenerating=True).write(
                {
                    "f_monto_total": abs(int(round(source.amount_total or 0))),
                    "f_fecha_emision": source.invoice_date or source.date,
                    "f_nombre_razon_social": source.partner_id.name,
                }
            )

    # ============== VALIDATION MATRIX (D4) ==============

    @api.depends(
        "f_tipo_comprobante",
        "f_monto_total",
        "f_monto_gravado_10",
        "f_monto_gravado_5",
        "f_monto_exento",
        "f_monto_gravado",
        "f_monto_no_gravado_exonerado",
        "f_tipo_identificacion",
        "f_numero_identificacion",
        "f_timbrado",
        "f_numero_comprobante",
        "f_periodo_mm_aaaa",
        "f_especificar_tipo_documento",
        "f_comprobante_asociado_numero",
        "f_comprobante_asociado_timbrado",
        "f_imputa_iva",
        "f_imputa_ire",
        "f_imputa_irp_rsp",
        "f_no_imputa",
        "manual_override",
        "move_id.amount_total",
        "libro_id.tipo_registro",
    )
    def _compute_state(self):
        for line in self:
            problems = []
            tipo = line.tipo_registro
            if tipo in ("ventas", "compras"):
                problems += line._check_state_ventas_compras()
            if tipo == "ingresos":
                problems += line._check_state_ingresos()
            if tipo == "egresos":
                problems += line._check_state_egresos()
            problems += line._check_state_obligacion_imputada()

            line.error_message = "; ".join(problems) if problems else False
            line.state = "erro" if problems else "ok"

    def _check_state_ventas_compras(self):
        self.ensure_one()
        problems = []
        tipo = self.tipo_registro
        codigo = self.f_tipo_comprobante
        if not self.f_tipo_identificacion or not self.f_numero_identificacion:
            problems.append(_("Identificación es obligatoria."))
        if tipo == "compras" and codigo in ZERO_BREAKDOWN_CODES:
            if any(
                [self.f_monto_gravado_10, self.f_monto_gravado_5, self.f_monto_exento]
            ):
                problems.append(
                    _(
                        "Para el tipo %(codigo)s los montos gravados "
                        "10/5/exento deben estar en cero.",
                        codigo=codigo,
                    )
                )
        else:
            suma = (
                (self.f_monto_gravado_10 or 0)
                + (self.f_monto_gravado_5 or 0)
                + (self.f_monto_exento or 0)
            )
            if abs(suma - (self.f_monto_total or 0)) > 1:
                problems.append(
                    _(
                        "El monto total no coincide con la suma de los "
                        "montos gravados (10%%/5%%/exento)."
                    )
                )
        if not self.f_monto_total or self.f_monto_total <= 0:
            problems.append(_("El monto total debe ser mayor a 0."))
        if codigo in ("110", "111") and not (
            self.f_comprobante_asociado_numero and self.f_comprobante_asociado_timbrado
        ):
            problems.append(
                _(
                    "Número y timbrado del comprobante asociado son "
                    "obligatorios para Notas de Crédito/Débito."
                )
            )
        if (
            tipo == "compras"
            and self.move_id
            and self.move_id.move_type in ("in_invoice", "in_refund")
            and not (self.f_timbrado and self.f_numero_comprobante)
        ):
            problems.append(_("Timbrado/número del proveedor ausente o inconsistente."))
        return problems

    def _check_state_ingresos(self):
        self.ensure_one()
        problems = []
        codigo = self.f_tipo_comprobante
        if codigo != "203":
            suma = (self.f_monto_gravado or 0) + (
                self.f_monto_no_gravado_exonerado or 0
            )
            if abs(suma - (self.f_monto_total or 0)) > 1:
                problems.append(
                    _(
                        "El monto total no coincide con la suma de monto "
                        "gravado + no gravado/exonerado."
                    )
                )
        if not self.f_monto_total or self.f_monto_total <= 0:
            problems.append(_("El monto total debe ser mayor a 0."))
        if codigo == "208" and (
            not self.f_periodo_mm_aaaa or len(self.f_periodo_mm_aaaa or "") != 7
        ):
            problems.append(_("El período mm/aaaa es obligatorio para el tipo 208."))
        if codigo == "210" and not self.f_especificar_tipo_documento:
            problems.append(_("Especificar Tipo de Documento es obligatorio (210)."))
        return problems

    def _check_state_egresos(self):
        self.ensure_one()
        problems = []
        codigo = self.f_tipo_comprobante
        if not self.f_monto_total or self.f_monto_total <= 0:
            problems.append(_("El monto total debe ser mayor a 0."))
        if codigo != "207" and self.f_imputa_iva == "S":
            problems.append(_("Imputa al IVA solo puede ser 'S' para el tipo 207."))
        if codigo in ("208", "206") and (
            not self.f_periodo_mm_aaaa or len(self.f_periodo_mm_aaaa or "") != 7
        ):
            problems.append(
                _("El período mm/aaaa es obligatorio para %(codigo)s.", codigo=codigo)
            )
        if codigo == "209" and not self.f_especificar_tipo_documento:
            problems.append(_("Especificar Tipo de Documento es obligatorio (209)."))
        return problems

    def _check_state_obligacion_imputada(self):
        self.ensure_one()
        if self.tipo_registro in ("ventas", "compras", "egresos"):
            obligaciones = [self.f_imputa_iva, self.f_imputa_ire, self.f_imputa_irp_rsp]
        else:
            obligaciones = [self.f_imputa_ire, self.f_imputa_irp_rsp]
        if any(value == "S" for value in obligaciones):
            return []
        return [
            _(
                "Debe marcarse al menos una obligación imputada "
                "(IVA/IRE/IRP-RSP según el registro)."
            )
        ]
