# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    l10n_py_maquila_program_id = fields.Many2one(
        "l10n_py.maquila.program",
        string="Maquila Program",
    )
    l10n_py_intn_certified = fields.Boolean(
        string="INTN Certified",
    )
    l10n_py_intn_certificate = fields.Char(
        string="INTN Certificate Number",
    )
    l10n_py_intn_date = fields.Date(
        string="INTN Certification Date",
    )


class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    # Builds on top of mrp_bom_line_net_qty which provides:
    # product_qty (gross), product_qty_net (net), loss_percentage
    # These map to INTN coefficients:
    # product_qty = fator_requerimento (gross)
    # product_qty_net = coeficiente_neto x qty
    # loss_percentage = coeficiente_desperdicio %

    l10n_py_origin_type = fields.Selection(
        [
            ("temporary_admission", "Temporary Admission"),
            ("national_py", "National (Paraguay)"),
            ("national_mercosul", "National (Mercosul)"),
            ("imported", "Imported (Other)"),
        ],
        string="Origin Type",
    )
    l10n_py_origin_country = fields.Many2one(
        "res.country",
        string="Origin Country",
    )


class MaquilaProgramProduct(models.Model):
    _inherit = "l10n_py.maquila.program.product"

    bom_id = fields.Many2one(
        "mrp.bom",
        string="Bill of Materials",
    )
