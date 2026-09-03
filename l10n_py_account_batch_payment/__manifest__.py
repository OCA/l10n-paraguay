{
    "name": "Paraguay - SIPAP Batch Payment Foundation",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations",
    "summary": "Master data and pluggable export framework for Paraguayan "
    "SIPAP batch payment files",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-paraguay",
    "license": "LGPL-3",
    "depends": [
        "l10n_py_base",
        "account_payment_order",
    ],
    "data": [
        "data/account_payment_method.xml",
        "views/res_partner_bank_views.xml",
        "views/res_bank_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
