# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models

from .atlas_api_client import AtlasApiClient


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    atlas_enabled = fields.Boolean(
        string="Banco Atlas",
        help="Habilita la integración con las APIs REST del Banco Atlas "
        "(Paraguay) para esta cuenta bancaria: autenticación JWT/RSA "
        "compartida por consulta de saldo, consulta de alias, pago a "
        "proveedores y transferencias al exterior.",
    )
    atlas_environment = fields.Selection(
        [("testing", "Testing"), ("production", "Producción")],
        string="Entorno Atlas",
        default="testing",
    )
    atlas_production_url = fields.Char(
        string="URL de Producción Atlas",
        help="Ninguna API del Banco Atlas documenta su URL de producción "
        "de forma pública: se debe solicitar al banco y completar aquí "
        "antes de cambiar el entorno a 'Producción'.",
    )
    atlas_numero_cuenta = fields.Char(
        string="Número de Cuenta Atlas",
        help="Número de cuenta usado como parámetro de ruta en las APIs "
        "del Banco Atlas (puede diferir del formato de acc_number).",
    )
    atlas_api_key = fields.Char(
        string="API Key Atlas",
        groups="account.group_account_manager",
    )
    atlas_private_key_pem = fields.Text(
        string="Clave Privada Atlas (PEM)",
        groups="account.group_account_manager",
        help="Clave privada RSA de la aplicación, en formato PEM PKCS8 "
        "sin cifrar. Usada para firmar el JWT de cada petición.",
    )
    atlas_bank_public_key_pem = fields.Text(
        string="Clave Pública del Banco Atlas (PEM)",
        help="Clave pública RSA del banco, usada para validar la firma "
        "del JWT de respuesta.",
    )
    atlas_auth_token = fields.Char(
        string="Token de Autorización Atlas",
        groups="account.group_account_manager",
        help="Token de autorización de cuenta, obtenido una única vez del "
        "banco fuera de esta API (proceso manual/comercial). Revocable "
        "sin afectar otros tokens.",
    )
    atlas_saldo = fields.Monetary(
        string="Saldo Atlas", currency_field="atlas_saldo_currency_id"
    )
    atlas_saldo_disponible = fields.Monetary(
        string="Saldo Disponible Atlas", currency_field="atlas_saldo_currency_id"
    )
    atlas_saldo_currency_id = fields.Many2one(
        "res.currency",
        string="Moneda del Saldo Atlas",
        default=lambda self: self.env.ref("base.PYG", raise_if_not_found=False),
    )
    atlas_saldo_consulta_fecha = fields.Datetime(
        string="Última Consulta de Saldo Atlas"
    )

    def action_atlas_consultar_saldo(self):
        """Query the current balance for this Banco-Atlas-enabled account
        and store it (spec §2.5 -- this is an on-demand snapshot, not a
        reconciliation feed; the API returns no transaction list)."""
        self.ensure_one()
        client = AtlasApiClient.from_bank_account(self)
        response = client.call(
            "GET", f"/cuentas-atlas/v1.5.0/cuentas/{self.atlas_numero_cuenta}/saldo"
        )
        self.write(
            {
                "atlas_saldo": response.get("saldo"),
                "atlas_saldo_disponible": response.get("saldoDisponible"),
                "atlas_saldo_consulta_fecha": fields.Datetime.now(),
            }
        )
