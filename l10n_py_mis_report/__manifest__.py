# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Paraguay - Informes Contables MIS",
    "summary": "Balance General, Estado de Resultados y Flujo de Efectivo "
    "(RG 49/14) con MIS Builder",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations/Reporting",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-paraguay",
    "license": "AGPL-3",
    "depends": [
        "l10n_py",
        "mis_builder",
        "mis_builder_cash_flow",
    ],
    "data": [
        "data/mis_report_styles.xml",
        "data/mis_report_balance_general.xml",
        "data/mis_report_estado_resultados.xml",
        "data/mis_report_flujo_efectivo.xml",
        "data/mis_report_instances.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
