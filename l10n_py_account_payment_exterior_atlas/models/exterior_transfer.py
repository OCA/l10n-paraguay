# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client import (
    AtlasApiClient,
    AtlasApiError,
)


class L10nPyAtlasExteriorTransfer(models.Model):
    """One international transfer via Banco Atlas's two-phase
    (quote/confirm) Transferencias al Exterior API. Not a batch --
    this API processes one operation per call (spec §5)."""

    _name = "l10n_py.atlas.exterior.transfer"
    _description = "Transferencia al Exterior (Banco Atlas)"

    company_bank_account_id = fields.Many2one(
        "res.partner.bank",
        required=True,
        string="Cuenta Origen (Atlas)",
        domain="[('atlas_enabled', '=', True)]",
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("quoted", "Cotizado"),
            ("confirmed", "Confirmado"),
            ("settled", "Liquidado"),
            ("rejected", "Rechazado"),
        ],
        default="draft",
    )
    moneda = fields.Selection([("USD", "USD"), ("EUR", "EUR")], required=True)
    monto_transferencia = fields.Monetary(required=True, currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency", compute="_compute_currency_id", store=True
    )
    codigo_motivo = fields.Char(required=True, string="Código de Motivo")
    numero_orden_pago_dna = fields.Char(
        string="N.º Orden de Pago DNA",
        help="Obligatorio solo cuando la finalidad es importación de "
        "mercaderías (Dirección Nacional de Aduanas).",
    )
    numero_contrato_cambio = fields.Char(string="N.º Contrato de Cambio")
    tipo_cargo = fields.Selection(
        [("BEN", "Beneficiario paga"), ("OUR", "Ordenante paga")], required=True
    )
    plazo = fields.Selection(
        [("0", "Mismo día (solo USD)"), ("24", "24 horas"), ("48", "48 horas")],
        required=True,
    )
    beneficiario_nombre = fields.Char(required=True)
    beneficiario_cuenta = fields.Char(required=True)
    beneficiario_swift = fields.Char(required=True, string="SWIFT Banco Beneficiario")
    beneficiario_pais = fields.Integer(required=True, string="Código País Beneficiario")
    beneficiario_ciudad = fields.Integer(
        required=True, string="Código Ciudad Beneficiario"
    )
    beneficiario_direccion = fields.Char(required=True)
    swift_banco_intermediario = fields.Char()
    beneficiario_banco_nombre = fields.Char(
        readonly=True,
        string="Nombre Banco Beneficiario (Atlas)",
        help="Completado por 'Validar SWIFT' -- nombre del banco "
        "beneficiario devuelto por Banco Atlas al consultar el código "
        "SWIFT, usado para llenar 'nombreBancoBeneficiario' en el "
        "payload en vez de enviarlo vacío.",
    )

    numero_referencia = fields.Integer(readonly=True)
    monto_cargo = fields.Monetary(readonly=True, currency_field="currency_id")
    monto_cargo_intermediario = fields.Monetary(
        readonly=True, currency_field="currency_id"
    )
    monto_cargo_plazo = fields.Monetary(readonly=True, currency_field="currency_id")
    total_debito = fields.Monetary(readonly=True, currency_field="currency_id")

    @api.depends("moneda")
    def _compute_currency_id(self):
        for record in self:
            record.currency_id = self.env["res.currency"].search(
                [("name", "=", record.moneda)], limit=1
            )

    def _l10n_py_atlas_exterior_payload(self, modo):
        self.ensure_one()
        payload = {
            "modo": modo,
            "plazo": int(self.plazo),
            "moneda": self.moneda,
            "montoTransferencia": self.monto_transferencia,
            "codigoMotivo": self.codigo_motivo,
            "tipoCargo": self.tipo_cargo,
            "beneficiario": {
                "numeroCuentaBeneficiario": self.beneficiario_cuenta,
                "denominacionBeneficiario": self.beneficiario_nombre,
                "direccionBeneficiario": self.beneficiario_direccion,
                "codigoPaisBeneficiario": self.beneficiario_pais,
                "codigoCiudadBeneficiario": self.beneficiario_ciudad,
                "codigoSwiftBancoBeneficiario": self.beneficiario_swift,
                "nombreBancoBeneficiario": self.beneficiario_banco_nombre or "",
            },
        }
        if self.numero_orden_pago_dna:
            payload["numeroOrdenPago"] = self.numero_orden_pago_dna
        if self.numero_contrato_cambio:
            payload["numeroContratoCambio"] = self.numero_contrato_cambio
        if modo == "C":
            payload["numeroReferencia"] = self.numero_referencia
        return payload

    def action_validar_swift(self):
        """Validate beneficiario_swift against Banco Atlas's foreign-bank
        lookup (spec item 8, exterior branch) before quoting, catching a
        typo before it reaches the real quote/confirm endpoint. On
        success, caches the bank's own name so the payload no longer
        sends an empty nombreBancoBeneficiario. Deliberately NOT called
        automatically from action_atlas_cotizar -- see this plan's
        Global Constraints for why."""
        self.ensure_one()
        if not self.beneficiario_swift:
            raise UserError(
                _("Ingrese el código SWIFT del banco beneficiario antes de validar.")
            )
        client = AtlasApiClient.from_bank_account(self.company_bank_account_id)
        try:
            datos = client.consultar_banco_exterior(self.beneficiario_swift)
        except AtlasApiError as exc:
            raise UserError(
                _(
                    "El Banco Atlas no reconoce el código SWIFT '%(swift)s': "
                    "%(error)s",
                    swift=self.beneficiario_swift,
                    error=exc.message,
                )
            ) from exc
        nombre_banco = datos.get("nombreBanco")
        if not nombre_banco:
            raise UserError(
                _(
                    "El Banco Atlas no devolvió un nombre de banco para el "
                    "código SWIFT '%(swift)s'.",
                    swift=self.beneficiario_swift,
                )
            )
        self.beneficiario_banco_nombre = nombre_banco

    def action_atlas_cotizar(self):
        """Modo V: quote the transfer's fees without debiting yet."""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Solo se puede cotizar una transferencia en borrador."))
        client = AtlasApiClient.from_bank_account(self.company_bank_account_id)
        response = client.call(
            "POST",
            "/transferencias-atlas/v1.5.0/exterior/registrar-operacion",
            body=self._l10n_py_atlas_exterior_payload("V"),
        )
        datos = response.get("datosOperacion", {})
        self.write(
            {
                "numero_referencia": datos.get("numeroReferencia"),
                "monto_cargo": datos.get("montoCargo"),
                "monto_cargo_intermediario": datos.get("montoCargoIntermediario"),
                "monto_cargo_plazo": datos.get("montoCargoPlazo"),
                "total_debito": datos.get("total_debito"),
                "state": "quoted",
            }
        )

    def action_atlas_confirmar(self):
        """Modo C: confirm a previously quoted transfer, using the
        numeroReferencia from action_atlas_cotizar(). This is what
        actually debits the account (spec §5.2)."""
        self.ensure_one()
        if self.state != "quoted" or not self.numero_referencia:
            raise UserError(_("Solo se puede confirmar una transferencia ya cotizada."))
        client = AtlasApiClient.from_bank_account(self.company_bank_account_id)
        response = client.call(
            "POST",
            "/transferencias-atlas/v1.5.0/exterior/registrar-operacion",
            body=self._l10n_py_atlas_exterior_payload("C"),
        )
        estado = response.get("respuesta", {}).get("estado")
        self.state = "confirmed" if estado == "OK" else "rejected"
