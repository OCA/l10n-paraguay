# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MaquilaProgram(models.Model):
    _inherit = "l10n_py.maquila.program"

    bom_ids = fields.One2many(
        "mrp.bom",
        "l10n_py_maquila_program_id",
        string="Bills of Materials",
    )
    bom_count = fields.Integer(compute="_compute_bom_count")
    production_ids = fields.One2many(
        "mrp.production",
        "l10n_py_maquila_program_id",
        string="Productions",
    )
    production_count = fields.Integer(compute="_compute_production_count")
    waste_ids = fields.One2many(
        "l10n_py.maquila.waste",
        "program_id",
        string="Waste Records",
    )
    waste_count = fields.Integer(compute="_compute_waste_count")

    @api.depends("bom_ids")
    def _compute_bom_count(self):
        for rec in self:
            rec.bom_count = len(rec.bom_ids)

    @api.depends("production_ids")
    def _compute_production_count(self):
        for rec in self:
            rec.production_count = len(rec.production_ids)

    @api.depends("waste_ids")
    def _compute_waste_count(self):
        for rec in self:
            rec.waste_count = len(rec.waste_ids)

    def action_view_boms(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Bills of Materials",
            "res_model": "mrp.bom",
            "view_mode": "tree,form",
            "domain": [("l10n_py_maquila_program_id", "=", self.id)],
            "context": {"default_l10n_py_maquila_program_id": self.id},
        }

    def action_view_productions(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Productions",
            "res_model": "mrp.production",
            "view_mode": "tree,form",
            "domain": [("l10n_py_maquila_program_id", "=", self.id)],
        }

    def action_view_waste(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Waste Records",
            "res_model": "l10n_py.maquila.waste",
            "view_mode": "tree,form",
            "domain": [("program_id", "=", self.id)],
            "context": {"default_program_id": self.id},
        }
