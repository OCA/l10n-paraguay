# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _prepare_edi_document_data(self):
        """Extend EDI document data with maquila legend (Feature 16 - SIFEN)."""
        data = super()._prepare_edi_document_data()
        if self.l10n_py_maquila_program_id:
            program = self.l10n_py_maquila_program_id
            maquila_legend = "Producto Maquila - Ley 1064/97 - %s" % program.code
            existing_obs = data.get("observacion") or ""
            if existing_obs:
                data["observacion"] = "%s | %s" % (existing_obs, maquila_legend)
            else:
                data["observacion"] = maquila_legend
        return data
