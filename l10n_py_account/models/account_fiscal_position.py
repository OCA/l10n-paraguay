from odoo import models


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    def _get_fpos_ranking_functions(self, partner):
        if self.env.company.country_id.code != "PY":
            return super()._get_fpos_ranking_functions(partner)
        # NOTE: `self.env.ref("l10n_py.py_fiscal_position_ventas_exportacion")` does not
        # resolve to the per-company record instantiated from the `account.chart.template`
        # data (the xmlid on the company-specific record differs), so we rank by name
        # instead of by id. See l10n_ar/models/account_fiscal_position.py:14-21 for the
        # pattern this override is based on.
        return [
            ("l10n_py_export", lambda fpos: (
                bool(partner.country_id) and partner.country_id.code != "PY"
                and fpos.name == "Ventas - Exportación"
            )),
        ] + super()._get_fpos_ranking_functions(partner)
