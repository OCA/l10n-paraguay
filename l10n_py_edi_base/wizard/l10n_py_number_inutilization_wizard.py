# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class L10nPyNumberInutilizationWizard(models.TransientModel):
    _name = "l10n_py.number.inutilization.wizard"
    _description = "Inutilizar numeración (SIFEN)"

    authorization_id = fields.Many2one(
        "account.authorization", string="Timbrado", required=True, readonly=True
    )
    number_from = fields.Integer(string="Número Desde", required=True)
    number_to = fields.Integer(string="Número Hasta", required=True)
    motive = fields.Char(string="Motivo", required=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get("active_model") == "account.authorization":
            res["authorization_id"] = self.env.context.get("active_id")
        return res

    @api.constrains("number_from", "number_to")
    def _check_range(self):
        for wizard in self:
            if wizard.number_from > wizard.number_to:
                raise ValidationError(
                    _("El número inicial debe ser menor o igual al final.")
                )

    def action_inutilize(self):
        """Crear la inutilización persistente y enviarla al SIFEN.

        Las validaciones de rango/faja-dentro-de-la-autorización/números-ya-
        usados ya existen como @api.constrains en l10n_py.number.inutilization
        y disparan solas en el create() de abajo; no se replican aquí.
        """
        self.ensure_one()
        record = self.env["l10n_py.number.inutilization"].create(
            {
                "authorization_id": self.authorization_id.id,
                "number_from": self.number_from,
                "number_to": self.number_to,
                "motive": self.motive,
            }
        )
        record.action_send()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": _("Inutilización enviada al SIFEN."),
                "type": "success",
            },
        }
