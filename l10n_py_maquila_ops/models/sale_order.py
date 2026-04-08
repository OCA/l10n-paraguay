# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    l10n_py_maquila_program_id = fields.Many2one(
        "l10n_py.maquila.program",
        string="Maquila Program",
    )
    l10n_py_is_maquila_export = fields.Boolean(
        compute="_compute_is_maquila_export",
    )

    @api.depends("l10n_py_maquila_program_id")
    def _compute_is_maquila_export(self):
        for order in self:
            order.l10n_py_is_maquila_export = bool(order.l10n_py_maquila_program_id)

    @api.onchange("l10n_py_maquila_program_id")
    def _onchange_maquila_program(self):
        if self.l10n_py_maquila_program_id:
            fp = self.env.ref(
                "l10n_py_maquila_ops.fiscal_position_maquila_export",
                raise_if_not_found=False,
            )
            if fp:
                self.fiscal_position_id = fp

    def action_confirm(self):
        for order in self:
            program = order.l10n_py_maquila_program_id
            if program and program.maquila_type == "pura":
                # Pure maquila cannot sell domestically
                partner_country = order.partner_id.country_id
                py_country = self.env.ref("base.py", raise_if_not_found=False)
                if partner_country and py_country and partner_country == py_country:
                    raise UserError(
                        _("Pure maquila programs cannot sell" " to domestic customers.")
                    )
        return super().action_confirm()
