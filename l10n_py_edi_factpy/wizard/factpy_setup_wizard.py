from odoo import _, fields, models
from odoo.exceptions import UserError


class FactPySetupWizard(models.TransientModel):
    _name = "factpy.setup.wizard"
    _description = "FactPy Setup Wizard"

    name = fields.Char(
        string="Connector Name", default="FactPy Connector", required=True
    )

    api_key = fields.Char(
        string="API Key",
        required=True,
        help="Token de autenticación proporcionado por FactPy",
    )

    api_secret = fields.Char(
        string="API Secret",
        required=True,
        help="Secret de autenticación proporcionado por FactPy",
    )

    environment = fields.Selection(
        [("test", "Pruebas"), ("prod", "Producción")],
        default="test",
        required=True,
    )

    def action_create_connector(self):
        """Create FactPy connector with provided credentials"""
        self.ensure_one()

        # Check if connector already exists for this company
        existing = self.env["l10n_py.edi.connector.factpy"].search(
            [("company_id", "=", self.env.company.id)]
        )

        if existing:
            raise UserError(_("A FactPy connector already exists for this company"))

        # Create new connector
        connector = self.env["l10n_py.edi.connector.factpy"].create(
            {
                "name": self.name,
                "company_id": self.env.company.id,
                "api_key": self.api_key,
                "api_secret": self.api_secret,
                "environment": self.environment,
            }
        )

        # Test connection
        try:
            result = connector.test_connection()
            if result.get("type") == "ir.actions.client":
                # Connection successful
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Configuración Completa"),
                        "message": _(
                            "El conector FactPy ha sido configurado exitosamente"
                        ),
                        "type": "success",
                        "sticky": False,
                    },
                }
            else:
                # Connection failed
                return {
                    "name": _("Error de Conexión"),
                    "type": "ir.actions.act_window",
                    "res_model": "factpy.setup.wizard",
                    "view_mode": "form",
                    "target": "new",
                    "context": {
                        "default_error_message": (
                            "No se pudo conectar con FactPy. "
                            "Verifique sus credenciales."
                        )
                    },
                }
        except Exception as e:
            return {
                "name": _("Error de Conexión"),
                "type": "ir.actions.act_window",
                "res_model": "factpy.setup.wizard",
                "view_mode": "form",
                "target": "new",
                "context": {"default_error_message": str(e)},
            }
