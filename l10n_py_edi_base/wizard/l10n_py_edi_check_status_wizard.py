# l10n_py_edi_base/wizard/l10n_py_edi_check_status_wizard.py

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class L10nPyEdiCheckStatusWizard(models.TransientModel):
    _name = "l10n_py.edi.check.status.wizard"
    _description = "Consultar status EDI (SIFEN)"

    invoice_id = fields.Many2one(
        "account.move", string="Factura", required=True, readonly=True
    )
    status = fields.Char(readonly=True)
    message = fields.Text(readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get("active_model") == "account.move":
            res["invoice_id"] = self.env.context.get("active_id")
        return res

    def action_check_status(self):
        """Consultar el estado del DE en el SIFEN y persistirlo en la factura."""
        self.ensure_one()
        invoice = self.invoice_id
        if not invoice.l10n_py_cdc:
            raise UserError(_("La factura no tiene CDC: aún no fue enviada al SIFEN."))
        connector = invoice._get_edi_connector()
        response = connector.check_status(invoice.l10n_py_cdc)
        edi_status, message = invoice._l10n_py_apply_check_status_response(response)
        self.status = edi_status
        self.message = message
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
