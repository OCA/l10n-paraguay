{
    "name": "Paraguay - Libros DNIT (RG 90/2021)",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations",
    "summary": "Registro de comprobantes Ventas/Compras/Ingresos/Egresos (DNIT)",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-paraguay",
    "license": "LGPL-3",
    "depends": [
        "account",
        "l10n_py_base",
        "l10n_py_account",
        "l10n_py_edi_base",
    ],
    "data": [
        # Views
        "views/l10n_py_libro_views.xml",
        "views/l10n_py_libro_menu.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
