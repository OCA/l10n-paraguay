# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from psycopg2.errors import UniqueViolation

from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.base.models.res_bank import sanitize_account_number
from odoo.addons.l10n_py_account_batch_payment.models.res_partner_bank import (
    L10N_PY_CAS_ALIAS_TYPES,
)
from odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client import (
    AtlasApiClient,
)

# Mapping from this module's local alias type
# (``res.partner.bank.l10n_py_cas_alias_type``) to the bank's own
# ``tipo`` parameter for ``AtlasApiClient.consultar_alias``. Confirmed
# against the bank's own specification (API de Consulta de Alias v0.1,
# "Petición" section): the bank's ``tipo`` enum has six literal values
# (CI, CRC, CRP, EMAIL, MOBILE, RUC); this module only maps to the four
# of them it has a local alias type for. ``CRP``/``CRC`` are two other
# values of that same enum whose exact meaning is not used or needed
# here.
L10N_PY_ATLAS_ALIAS_TIPO_BY_LOCAL_TYPE = {
    "phone": "MOBILE",
    "email": "EMAIL",
    "ci": "CI",
    "ruc": "RUC",
}


class L10nPyAtlasAliasResolver(models.TransientModel):
    """One-shot wizard to resolve a beneficiary's CAS alias
    (phone/email/RUC/CI) to a real Atlas account number via
    ``AtlasApiClient.consultar_alias``, and turn the result into a
    proper ``res.partner.bank`` record with a real ``acc_number``.

    This replaces an earlier attempt at resolving the alias inline
    during batch dispatch: since ``res.partner.bank.acc_number`` is
    required in Odoo's own core, a beneficiary bank account without an
    account number can never be persisted in the first place, so that
    dispatch-time branch could never actually be reached. Resolving the
    alias once, here, at registration time, is what makes the result
    usable by every downstream flow (dispatch included) as a normal,
    fully-numbered bank account.
    """

    _name = "l10n_py.atlas.alias.resolver"
    _description = "Resolver Alias CAS Banco Atlas"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        string="Compañía",
    )
    company_bank_account_id = fields.Many2one(
        "res.partner.bank",
        required=True,
        string="Cuenta Atlas (Empresa)",
        domain="[('atlas_enabled', '=', True),"
        " '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
    )
    partner_id = fields.Many2one("res.partner", required=True, string="Proveedor")
    alias_tipo = fields.Selection(
        selection=L10N_PY_CAS_ALIAS_TYPES,
        required=True,
        string="Tipo de Alias CAS",
    )
    alias_valor = fields.Char(required=True, string="Alias CAS")
    state = fields.Selection(
        [("draft", "Borrador"), ("resolved", "Resuelto")], default="draft"
    )
    resolved_nro_cuenta = fields.Char(readonly=True, string="Número de Cuenta Resuelto")
    resolved_denominacion = fields.Char(
        readonly=True, string="Titular (según el banco)"
    )
    resolved_alias_valor = fields.Char(
        readonly=True,
        string="Alias CAS Validado",
        help="Copia normalizada (sin espacios) de 'alias_valor' en el "
        "momento en que fue efectivamente validada contra el banco en "
        "action_buscar. Es la que debe persistirse en "
        "res.partner.bank.l10n_py_cas_alias_value, para no guardar un "
        "valor distinto del que el banco realmente confirmó.",
    )

    def action_buscar(self):
        self.ensure_one()
        tipo_atlas = L10N_PY_ATLAS_ALIAS_TIPO_BY_LOCAL_TYPE.get(self.alias_tipo)
        if not tipo_atlas:
            raise UserError(
                _(
                    "El tipo de alias CAS '%(tipo)s' no tiene un equivalente "
                    "conocido en la API de Banco Atlas.",
                    tipo=self.alias_tipo,
                )
            )
        alias_valor = (self.alias_valor or "").strip()
        if not alias_valor:
            raise UserError(
                _("El alias no puede estar vacío ni contener solo espacios.")
            )
        client = AtlasApiClient.from_bank_account(self.company_bank_account_id)
        response = client.consultar_alias(tipo=tipo_atlas, alias=alias_valor)
        nro_cuenta = response.get("nroCuenta")
        if not nro_cuenta:
            raise UserError(
                _(
                    "La respuesta del Banco Atlas para el alias '%(alias)s' "
                    "no incluyó el campo 'nroCuenta' esperado.",
                    alias=alias_valor,
                )
            )
        self.write(
            {
                "resolved_nro_cuenta": nro_cuenta,
                "resolved_denominacion": response.get("denominacion"),
                "resolved_alias_valor": alias_valor,
                "state": "resolved",
            }
        )

    def action_confirmar(self):
        self.ensure_one()
        if self.state != "resolved":
            raise UserError(
                _("Primero debe buscar y resolver el alias antes de confirmar.")
            )
        sanitized = sanitize_account_number(self.resolved_nro_cuenta)
        bank_model = self.env["res.partner.bank"]

        def _find_existing():
            return bank_model.search(
                [
                    ("partner_id", "=", self.partner_id.id),
                    ("sanitized_acc_number", "=", sanitized),
                ],
                limit=1,
            )

        existing = _find_existing()
        if not existing:
            # Two near-simultaneous confirmations for the same alias can
            # both pass the search above and both reach create(): the
            # core's unique(sanitized_acc_number, partner_id) constraint
            # is the real guard, so the create is wrapped in its own
            # savepoint and a UniqueViolation there is treated exactly
            # like finding it via search -- open the record the other
            # transaction won the race to create, instead of surfacing a
            # raw IntegrityError to the user.
            try:
                with self.env.cr.savepoint():
                    new_bank = bank_model.create(
                        {
                            "acc_number": self.resolved_nro_cuenta,
                            "partner_id": self.partner_id.id,
                            "l10n_py_cas_alias_type": self.alias_tipo,
                            "l10n_py_cas_alias_value": self.resolved_alias_valor,
                        }
                    )
            except UniqueViolation:
                existing = _find_existing()
                if not existing:
                    raise
            else:
                return {
                    "type": "ir.actions.act_window",
                    "res_model": "res.partner.bank",
                    "view_mode": "form",
                    "res_id": new_bank.id,
                    "target": "current",
                }
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.partner.bank",
            "view_mode": "form",
            "res_id": existing.id,
            "target": "current",
        }
