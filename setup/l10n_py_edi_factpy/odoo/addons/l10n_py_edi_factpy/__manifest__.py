{
    "name": "Paraguay - FactPy EDI Connector",
    "version": "16.0.1.2.0",
    "category": "Accounting/Localizations/EDI",
    "summary": "FactPy connector for Electronic Invoicing in Paraguay",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-paraguay",
    "license": "LGPL-3",
    "depends": [
        "l10n_py_edi_base",
    ],
    "data": [
        # Security
        "security/ir.model.access.csv",
        # Views
        "views/factpy_connector_views.xml",
        # Wizard
        "wizard/factpy_connector_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
