# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


class ResBank(models.Model):
    _inherit = "res.bank"

    l10n_py_sipap_bank_code = fields.Char(
        string="Código de Banco SIPAP",
        help="Código de banco asignado por el Banco Central del Paraguay "
        "(BCP) para el Sistema de Pagos (SIPAP). Requerido para poder "
        "identificar el banco destino en un archivo de pago por lote.",
    )
    l10n_py_sipap_export_code = fields.Char(
        string="Formato de Exportación SIPAP",
        help="Código técnico del generador de archivo de lote SIPAP a "
        "usar para este banco (por ejemplo 'iso20022'). Se resuelve, en "
        "tiempo de generación del archivo, contra los métodos "
        "'_l10n_py_generate_batch_file_<code>' que los módulos "
        "exportadores instalados registren en account.payment.order. "
        "Dejar vacío si el banco no tiene un exportador implementado "
        "todavía: la generación del archivo fallará entonces con un "
        "mensaje de error explícito, en lugar de producir un archivo "
        "en un formato no confirmado.",
    )
    l10n_py_sipap_export_mode = fields.Selection(
        [("file", "Archivo (subida manual)"), ("api", "API directa")],
        string="Modo de Exportación SIPAP",
        default="file",
        help="'Archivo' resuelve contra "
        "'_l10n_py_generate_batch_file_<code>' (comportamiento histórico "
        "de este framework: produce un archivo para subir manualmente al "
        "home banking). 'API directa' resuelve en cambio contra "
        "'_l10n_py_dispatch_batch_api_<code>', para bancos que exponen "
        "una API de disparo directo (por ejemplo Banco Atlas).",
    )
