{
    "name": "Paraguay - Banco Atlas International Transfers",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations",
    "summary": "Two-phase (quote/confirm) international transfer flow "
    "for Banco Atlas (Transferencias al Exterior)",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-paraguay",
    "license": "LGPL-3",
    "depends": [
        "l10n_py_account_payment_atlas",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/exterior_transfer_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
