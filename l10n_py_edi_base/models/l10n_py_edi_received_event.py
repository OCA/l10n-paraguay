# l10n_py_edi_base/models/l10n_py_edi_received_event.py

"""
Eventos del lado receptor SIFEN (acuse de recibo y manifestación de mérito).

Cuando esta empresa es la RECEPTORA de un DTE emitido por un proveedor, el
SIFEN permite (y en algunos casos exige) que informe eventos referenciando el
CDC ajeno: Notificación de Recepción (el "acuse de recibo" propiamente dicho),
Conformidad, Disconformidad y Desconocimiento (análogo a la Manifestación del
Destinatario de la NF-e brasileña).

No existe un webservice nuevo: los 4 eventos ya son campos opcionales del
mismo `TgGroupEvt` que el conector usa hoy para cancelación/inutilización
(ver `l10n_py_edi_sifen/models/edi_connector.py`). Este modelo sólo modela el
lado Odoo y orquesta el payload por tipo de evento.
"""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..services.cdc_generator import CDCGenerator

_logger = logging.getLogger(__name__)

# event_type que requieren cada campo condicional (Tabla del design doc)
_REQUIRE_TIPO_RECEPTOR = ("desconocimiento", "notificacion_recepcion")
_REQUIRE_FECHA_EMISION = ("desconocimiento", "notificacion_recepcion")
_REQUIRE_FECHA_RECEPCION = ("desconocimiento", "notificacion_recepcion")
_REQUIRE_MOTIVO = ("disconformidad", "desconocimiento")

# Camada 2 (manifestación de mérito): mutuamente exclusivos por CDC en estado
# aceptado. La notificación de recepción (camada 1) queda fuera de la regla.
_MERITO_EVENT_TYPES = ("conformidad", "disconformidad", "desconocimiento")


class L10nPyEdiReceivedEvent(models.Model):
    """Evento SIFEN del lado receptor, referenciando el CDC de un DTE ajeno."""

    _name = "l10n_py.edi.received.event"
    _description = "Evento de Receptor SIFEN (acuse de recibo)"
    _order = "create_date desc"

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
        help="La empresa receptora (el propio comprador).",
    )

    move_id = fields.Many2one(
        "account.move",
        string="Factura de proveedor",
        domain=[("move_type", "in", ("in_invoice", "in_refund"))],
        help="Factura de proveedor ya registrada en Odoo (opcional). "
        "Cuando se informa, precompleta CDC/proveedor/fecha/total, "
        "pero esos valores siguen siendo editables.",
    )

    cdc = fields.Char(
        string="CDC",
        size=44,
        required=True,
        help="Código de Control del DTE ajeno (del proveedor), 44 dígitos.",
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Proveedor (emisor del DTE)",
        help="Informativo/filtro. No es obligatorio: el evento es válido "
        "sólo con el CDC.",
    )

    event_type = fields.Selection(
        [
            ("notificacion_recepcion", "Notificación de Recepción"),
            ("conformidad", "Conformidad"),
            ("disconformidad", "Disconformidad"),
            ("desconocimiento", "Desconocimiento"),
        ],
        string="Tipo de Evento",
        required=True,
    )

    tipo_receptor = fields.Selection(
        [
            ("1", "Contribuyente"),
            ("2", "No contribuyente"),
        ],
        string="Tipo de Receptor",
        help="iTipRec. Obligatorio para Desconocimiento y Notificación de "
        "Recepción. Rótulos placeholder, a confirmar según el manual "
        "técnico SIFEN vigente.",
    )

    tipo_documento_id_receptor = fields.Selection(
        [
            ("1", "Cédula paraguaya"),
            ("2", "Pasaporte"),
            ("3", "Cédula extranjera"),
            ("4", "Carnet de residencia"),
            ("5", "Innominado"),
        ],
        string="Tipo de Documento (No Contribuyente)",
        help="dTipIDRec. Obligatorio cuando 'Tipo de Receptor' = No "
        "contribuyente. Rótulos placeholder, a confirmar según el manual "
        "técnico SIFEN vigente.",
    )

    numero_documento_receptor = fields.Char(
        string="Número de Documento (No Contribuyente)",
        size=20,
        help="dNumID. Obligatorio cuando 'Tipo de Receptor' = No " "contribuyente.",
    )

    tipo_conformidad = fields.Selection(
        [
            ("1", "Conforme"),
            ("2", "Conforme parcial"),
        ],
        string="Tipo de Conformidad",
        help="iTipConf. Obligatorio sólo para Conformidad. Rótulos "
        "placeholder, a confirmar según el manual técnico SIFEN vigente.",
    )

    fecha_emision_dte = fields.Datetime(
        string="Fecha de Emisión del DTE",
        help="dFecEmi. Obligatorio para Desconocimiento y Notificación de "
        "Recepción.",
    )

    fecha_recepcion = fields.Datetime(
        string="Fecha de Recepción",
        default=lambda self: fields.Datetime.now(),
        help="dFecRecep. Opcional en Conformidad, obligatorio en "
        "Desconocimiento/Notificación de Recepción.",
    )

    motivo = fields.Text(
        help="mOtEve. Obligatorio para Disconformidad y Desconocimiento "
        "(5 a 500 caracteres).",
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        default=lambda self: self.env.ref("base.PYG", raise_if_not_found=False),
    )

    total_gs = fields.Monetary(
        string="Total (Gs.)",
        currency_field="currency_id",
        help="dTotalGs. Obligatorio sólo para Notificación de Recepción.",
    )

    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("to_send", "Por Enviar"),
            ("accepted", "Aceptado"),
            ("rejected", "Rechazado"),
            ("error", "Error"),
        ],
        string="Estado",
        default="draft",
        readonly=True,
        copy=False,
    )

    protocolo_sifen = fields.Char(
        string="Protocolo SIFEN",
        readonly=True,
        copy=False,
    )

    error_message = fields.Text(
        string="Mensaje de Error",
        readonly=True,
        copy=False,
    )

    edi_log_ids = fields.One2many(
        "l10n_py.edi.log",
        "l10n_py_received_event_id",
        string="Logs EDI",
    )

    # ============== ONCHANGE ==============

    @api.onchange("move_id")
    def _onchange_move_id(self):
        for rec in self:
            if not rec.move_id:
                continue
            move = rec.move_id
            if move.l10n_py_cdc:
                rec.cdc = move.l10n_py_cdc
            rec.partner_id = move.partner_id
            if move.invoice_date:
                rec.fecha_emision_dte = fields.Datetime.to_datetime(move.invoice_date)
            if move.currency_id and rec.currency_id:
                if move.currency_id == rec.currency_id:
                    rec.total_gs = move.amount_total
                else:
                    rec.total_gs = move.currency_id._convert(
                        move.amount_total,
                        rec.currency_id,
                        rec.company_id or move.company_id,
                        fields.Date.context_today(rec),
                    )
            else:
                rec.total_gs = move.amount_total

    # ============== CONSTRAINTS ==============

    @api.constrains("cdc")
    def _check_cdc_format(self):
        for rec in self:
            if not rec.cdc:
                continue
            valid, error = CDCGenerator.validate_cdc(rec.cdc)
            if not valid:
                raise ValidationError(
                    _("CDC inválido para el evento de receptor: %s") % error
                )

    @api.constrains(
        "tipo_receptor", "tipo_documento_id_receptor", "numero_documento_receptor"
    )
    def _check_documento_no_contribuyente(self):
        """Cuando el receptor es 'No contribuyente' (tipo_receptor='2'), el
        SIFEN identifica a la empresa por documento alternativo (dTipIDRec/
        dNumID) en vez de RUC (dRucRec/dDVRec). No permite guardar el evento
        sin esos campos, para no descubrir el payload incompleto sólo al
        transmitir."""
        for rec in self:
            if rec.tipo_receptor != "2":
                continue
            if not rec.tipo_documento_id_receptor or not rec.numero_documento_receptor:
                raise ValidationError(
                    _(
                        "Para 'Tipo de Receptor' = No contribuyente, informe "
                        "el Tipo y Número de Documento del receptor "
                        "(dTipIDRec/dNumID)."
                    )
                )

    def _get_missing_fields_for_type(self, raise_error=True):
        """Devuelve (y opcionalmente levanta) los campos condicionales
        faltantes según el `event_type` del registro.

        Deliberadamente NO es un `@api.constrains`: un evento en borrador
        puede quedar incompleto mientras el usuario lo completa (igual que
        una factura en borrador). La validación se exige recién al intentar
        transmitir (`action_send_receiver_event`), para que el error
        aparezca ANTES de llamar al conector, no después."""
        self.ensure_one()
        missing = []
        if self.event_type in _REQUIRE_TIPO_RECEPTOR and not self.tipo_receptor:
            missing.append(_("Tipo de Receptor"))
        if self.tipo_receptor == "2" and not self.tipo_documento_id_receptor:
            missing.append(_("Tipo de Documento (No Contribuyente)"))
        if self.tipo_receptor == "2" and not self.numero_documento_receptor:
            missing.append(_("Número de Documento (No Contribuyente)"))
        if self.event_type == "conformidad" and not self.tipo_conformidad:
            missing.append(_("Tipo de Conformidad"))
        if self.event_type in _REQUIRE_FECHA_EMISION and not self.fecha_emision_dte:
            missing.append(_("Fecha de Emisión del DTE"))
        if self.event_type in _REQUIRE_FECHA_RECEPCION and not self.fecha_recepcion:
            missing.append(_("Fecha de Recepción"))
        if self.event_type in _REQUIRE_MOTIVO:
            if not self.motivo or not (5 <= len(self.motivo) <= 500):
                missing.append(_("Motivo (5 a 500 caracteres)"))
        if self.event_type == "notificacion_recepcion" and not self.total_gs:
            missing.append(_("Total (Gs.)"))
        if missing and raise_error:
            raise ValidationError(
                _(
                    "Faltan campos obligatorios para el evento '%(tipo)s': "
                    "%(campos)s.",
                    tipo=dict(self._fields["event_type"].selection).get(
                        self.event_type, self.event_type
                    ),
                    campos=", ".join(missing),
                )
            )
        return missing

    @api.constrains("state", "event_type", "cdc")
    def _check_exclusividade_merito(self):
        """Para un mismo CDC, a lo sumo un evento ACEPTADO entre
        conformidad/disconformidad/desconocimiento (camada 2). La
        notificación de recepción (camada 1) queda fuera de esta regla."""
        for rec in self:
            if rec.state != "accepted" or rec.event_type not in _MERITO_EVENT_TYPES:
                continue
            other = self.search(
                [
                    ("id", "!=", rec.id),
                    ("cdc", "=", rec.cdc),
                    ("state", "=", "accepted"),
                    ("event_type", "in", list(_MERITO_EVENT_TYPES)),
                ],
                limit=1,
            )
            if other:
                raise ValidationError(
                    _(
                        "Ya existe un evento de mérito (%(tipo)s) aceptado "
                        "para el CDC %(cdc)s. Sólo se permite uno.",
                        tipo=other.event_type,
                        cdc=rec.cdc,
                    )
                )

    # ============== ACTIONS ==============

    def action_send_receiver_event(self):
        """Enviar el evento de receptor al SIFEN a través del conector EDI."""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Sólo se pueden enviar eventos en estado borrador."))
        self._get_missing_fields_for_type()

        self.state = "to_send"
        connector = None
        try:
            connector = self.company_id._get_edi_connector()
            vals = self._prepare_event_vals()
            response = connector.send_receiver_event(self.cdc, self.event_type, vals)
        except UserError as e:
            self.write({"state": "error", "error_message": str(e)})
            self._log_attempt(connector=connector, response=None, error=str(e))
            self.env.flush_all()
            raise
        except Exception as e:
            _logger.error("Error enviando evento de receptor: %s", str(e))
            self.write({"state": "error", "error_message": str(e)})
            self._log_attempt(connector=connector, response=None, error=str(e))
            self.env.flush_all()
            raise UserError(_("Error enviando evento de receptor: %s") % str(e)) from e

        if response.get("success"):
            self.write(
                {
                    "state": "accepted",
                    "protocolo_sifen": response.get("protocol"),
                    "error_message": False,
                }
            )
        else:
            error = response.get("error") or _("Error desconocido")
            self.write({"state": "rejected", "error_message": error})

        self._log_attempt(connector=connector, response=response)
        self.env.flush_all()
        return True

    def action_reset_to_draft(self):
        """Reenviar: volver a borrador manteniendo los datos, para eventos
        rechazados o con error de transporte. No hay reintento automático."""
        for rec in self:
            if rec.state not in ("rejected", "error"):
                raise UserError(
                    _("Sólo se pueden reenviar eventos rechazados o " "con error.")
                )
        self.write({"state": "draft"})

    def _prepare_event_vals(self):
        """Arma el diccionario de valores del evento por `event_type`,
        conforme a la tabla del design doc. El conector es responsable de
        traducirlo al binding pysifen correcto (TrGeVeNotRec/Conf/Disconf/
        Descon)."""
        self.ensure_one()
        company = self.company_id
        vals = {}
        if self.event_type == "notificacion_recepcion":
            vals.update(
                {
                    "dFecEmi": self.fecha_emision_dte,
                    "dFecRecep": self.fecha_recepcion,
                    "iTipRec": self.tipo_receptor,
                    "dNomRec": company.name,
                    "dTotalGs": self.total_gs,
                }
            )
            vals.update(self._receptor_identificacion_vals())
        elif self.event_type == "conformidad":
            vals.update(
                {
                    "iTipConf": self.tipo_conformidad,
                    "dFecRecep": self.fecha_recepcion,
                }
            )
        elif self.event_type == "disconformidad":
            vals.update({"mOtEve": self.motivo})
        elif self.event_type == "desconocimiento":
            vals.update(
                {
                    "dFecEmi": self.fecha_emision_dte,
                    "dFecRecep": self.fecha_recepcion,
                    "iTipRec": self.tipo_receptor,
                    "dNomRec": company.name,
                    "mOtEve": self.motivo,
                }
            )
            vals.update(self._receptor_identificacion_vals())
        return vals

    def _receptor_identificacion_vals(self):
        """Identificación de la propia empresa como receptor en el payload.

        `tipo_receptor='1'` (Contribuyente) usa RUC/DV (dRucRec/dDVRec);
        `tipo_receptor='2'` (No contribuyente) usa el documento alternativo
        (dTipIDRec/dNumID), nunca ambos a la vez (ver constraint
        `_check_documento_no_contribuyente`)."""
        self.ensure_one()
        if self.tipo_receptor == "2":
            return {
                "dTipIDRec": self.tipo_documento_id_receptor,
                "dNumID": self.numero_documento_receptor,
            }
        return {
            "dRucRec": self.company_id.l10n_py_ruc,
            "dDVRec": self.company_id.l10n_py_dv,
        }

    def _log_attempt(self, connector, response, error=None):
        """Registra la tentativa (éxito o fallo) en l10n_py.edi.log."""
        self.ensure_one()
        success = bool(response and response.get("success"))
        error_message = error or (response.get("error") if response else None)
        self.env["l10n_py.edi.log"].sudo().log_operation(
            operation_type="event",
            provider=(connector.provider_type if connector else "local"),
            cdc=self.cdc,
            success=success,
            error_message=error_message,
            response_data=response,
            l10n_py_received_event_id=self.id,
        )

    # ============== SMART BUTTON (account.move) ==============

    def action_view_move(self):
        self.ensure_one()
        if not self.move_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.move_id.id,
            "view_mode": "form",
            "target": "current",
        }

    # ============== UNLINK ==============

    def unlink(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(
                    _(
                        "No se puede eliminar un evento de receptor ya "
                        "transmitido (estado '%s'). Marque como error/"
                        "rechazado en su lugar."
                    )
                    % rec.state
                )
        return super().unlink()
