from odoo import models


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    def _get_fpos_ranking_functions(self, partner):
        if self.env.company.country_id.code != "PY":
            return super()._get_fpos_ranking_functions(partner)
        # Ranking por el marcador l10n_py_is_export (campo booleano seteado
        # en el CSV del chart template), no por nombre: el nombre de una
        # posición fiscal es traducible/renombrable. Ver
        # l10n_ar/models/account_fiscal_position.py:14-21 para el patrón.
        return [
            (
                "l10n_py_export",
                lambda fpos: (
                    bool(partner.country_id)
                    and partner.country_id.code != "PY"
                    and fpos.l10n_py_is_export
                ),
            ),
        ] + super()._get_fpos_ranking_functions(partner)
