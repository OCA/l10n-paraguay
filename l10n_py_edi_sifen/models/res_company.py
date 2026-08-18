# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import base64
import logging

from cryptography.hazmat.primitives.serialization import pkcs12

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

CERTIFICATE_EXPIRY_THRESHOLD_DAYS = 30


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_py_certificate = fields.Binary("Certificado PKCS12 (.pfx)")
    l10n_py_certificate_filename = fields.Char()
    l10n_py_certificate_password = fields.Char("Contraseña del Certificado")
    l10n_py_certificate_expiry = fields.Date(
        string="Expiración",
        compute="_compute_l10n_py_certificate_expiry",
        store=True,
        readonly=True,
    )
    l10n_py_certificate_state = fields.Selection(
        [
            ("valid", "Válido"),
            ("to_expire", "Por vencer"),
            ("expired", "Vencido"),
        ],
        string="Estado del Certificado",
        compute="_compute_l10n_py_certificate_state",
        store=True,
    )

    def _get_pkcs12_data(self):
        """Return (cert_bytes, password) for SIFEN mTLS."""
        self.ensure_one()
        if not self.l10n_py_certificate:
            raise UserError(
                _("Configure el certificado PKCS12 en la empresa %s") % self.name
            )
        cert_bytes = base64.b64decode(self.l10n_py_certificate)
        return cert_bytes, self.l10n_py_certificate_password or ""

    @api.depends("l10n_py_certificate", "l10n_py_certificate_password")
    def _compute_l10n_py_certificate_expiry(self):
        for company in self:
            expiry = False
            if company.l10n_py_certificate and company.l10n_py_certificate_password:
                try:
                    cert_bytes = base64.b64decode(company.l10n_py_certificate)
                    password = company.l10n_py_certificate_password.encode()
                    _key, cert, _chain = pkcs12.load_key_and_certificates(
                        cert_bytes, password
                    )
                    if cert is not None:
                        not_after = getattr(
                            cert, "not_valid_after_utc", None
                        ) or cert.not_valid_after
                        expiry = not_after.date()
                except Exception:
                    _logger.warning(
                        "No se pudo leer la fecha de vencimiento del "
                        "certificado SIFEN de %s",
                        company.display_name,
                    )
            company.l10n_py_certificate_expiry = expiry

    @api.depends("l10n_py_certificate_expiry")
    def _compute_l10n_py_certificate_state(self):
        today = fields.Date.context_today(self)
        for company in self:
            if not company.l10n_py_certificate_expiry:
                company.l10n_py_certificate_state = False
            elif company.l10n_py_certificate_expiry < today:
                company.l10n_py_certificate_state = "expired"
            elif (
                company.l10n_py_certificate_expiry - today
            ).days <= CERTIFICATE_EXPIRY_THRESHOLD_DAYS:
                company.l10n_py_certificate_state = "to_expire"
            else:
                company.l10n_py_certificate_state = "valid"

    def _cron_check_l10n_py_certificate_expiry(self):
        """Forzar el recompute diario del estado del certificado SIFEN.

        `store=True` solo recomputa cuando el certificado/contraseña cambian;
        sin este cron el estado queda stale al cruzar el umbral de
        vencimiento sin que nadie reabra el registro.
        """
        companies = self.sudo().search([("l10n_py_certificate", "!=", False)])
        companies._compute_l10n_py_certificate_expiry()
        companies._compute_l10n_py_certificate_state()
        for company in companies:
            if company.l10n_py_certificate_state in ("to_expire", "expired"):
                _logger.warning(
                    "Certificado digital SIFEN de %s está %s (vence %s)",
                    company.display_name,
                    company.l10n_py_certificate_state,
                    company.l10n_py_certificate_expiry,
                )
