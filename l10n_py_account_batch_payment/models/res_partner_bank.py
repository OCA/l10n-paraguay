# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# "Alias CAS" refers to the alternative identifiers that the Paraguayan
# interbank payment system (SIPAP) accepts instead of a full account
# number to route a credit to a beneficiary's bank account: a phone
# number, an email address, or the beneficiary's own tax/personal
# document (RUC or CI). This module only stores the data; no module in
# this repository resolves an alias against any external directory.
L10N_PY_CAS_ALIAS_TYPES = [
    ("phone", "Teléfono"),
    ("email", "Correo Electrónico"),
    ("ruc", "RUC"),
    ("ci", "Cédula de Identidad"),
]


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    l10n_py_cas_alias_type = fields.Selection(
        selection=L10N_PY_CAS_ALIAS_TYPES,
        string="Tipo de Alias CAS",
        help="Tipo de alias SIPAP (Cuentas Alias del Sistema) usado para "
        "identificar esta cuenta bancaria en lugar del número de cuenta "
        "completo.",
    )
    l10n_py_cas_alias_value = fields.Char(
        string="Alias CAS",
        help="Valor del alias SIPAP: número de teléfono, correo "
        "electrónico, RUC o CI, según el tipo seleccionado.",
    )
    l10n_py_sipap_bank_code = fields.Char(
        related="bank_id.l10n_py_sipap_bank_code",
        string="Código de Banco SIPAP",
        help="Código asignado por el BCP al banco destino, tomado del "
        "banco (res.bank) vinculado a esta cuenta.",
    )

    @api.constrains("l10n_py_cas_alias_type", "l10n_py_cas_alias_value")
    def _check_l10n_py_cas_alias(self):
        for bank in self:
            has_type = bool(bank.l10n_py_cas_alias_type)
            has_value = bool(bank.l10n_py_cas_alias_value)
            if has_type != has_value:
                raise ValidationError(
                    _(
                        "On bank account %(account)s: the CAS alias type and "
                        "the CAS alias value must be filled in together, or "
                        "both left empty.",
                        account=bank.display_name,
                    )
                )
