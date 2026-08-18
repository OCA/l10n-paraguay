# l10n_py_edi_base/models/account_authorization.py

from odoo import models


class AccountAuthorization(models.Model):
    """Extiende account.authorization (definido en l10n_py_account) con el
    botón de inutilización de numeración.

    El modelo del wizard (`l10n_py.number.inutilization.wizard`) vive en este
    módulo, no en l10n_py_account: l10n_py_edi_base depende de
    l10n_py_account (y no al revés), así que el botón que abre ese wizard
    también debe vivir aquí para que una instalación con sólo
    l10n_py_account (sin l10n_py_edi_base) nunca lo exponga.
    """

    _inherit = "account.authorization"

    def action_open_inutilization_wizard(self):
        """Abrir el wizard de inutilización de numeración desde el timbrado."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "l10n_py.number.inutilization.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_authorization_id": self.id},
        }
