# l10n_py_edi_facturasend/models/facturasend_connector.py

import json
import logging
from datetime import datetime

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class FacturaSendConnector(models.Model):
    _name = "l10n_py.edi.connector.facturasend"
    _description = "FacturaSend EDI Connector for Paraguay"
    _rec_name = "name"

    # ============== CONFIGURATION FIELDS ==============

    name = fields.Char(string="Nombre", required=True, default="FacturaSend Connector")

    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )

    api_key = fields.Char(
        string="API Key",
        required=True,
        help="Token de autenticación proporcionado por FacturaSend",
    )

    tenant_id = fields.Char(
        string="Tenant ID",
        required=True,
        help="Identificador del tenant en FacturaSend",
    )

    environment = fields.Selection(
        [("test", "Pruebas"), ("prod", "Producción")],
        string="Ambiente",
        default="test",
        required=True,
    )

    base_url = fields.Char(string="URL Base", compute="_compute_base_url", store=True)

    timeout = fields.Integer(
        string="Timeout (segundos)",
        default=30,
        help="Tiempo máximo de espera para respuesta",
    )

    active = fields.Boolean(string="Activo", default=True)

    # ============== COMPUTE METHODS ==============

    @api.depends("environment")
    def _compute_base_url(self):
        for record in self:
            if record.environment == "test":
                record.base_url = "https://api-test.facturasend.com.py"
            else:
                record.base_url = "https://api.facturasend.com.py"

    # ============== PRIVATE METHODS ==============

    def _get_headers(self):
        """Obtener headers para las peticiones"""
        return {
            "Authorization": f"Bearer api_key_{self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _adapt_to_facturasend_format(self, invoice_data):
        """
        Adaptar formato de datos del módulo base al formato FacturaSend
        """
        # Mapeo de tipos de IVA
        iva_mapping = {10: "I.V.A. 10%", 5: "I.V.A. 5%", 0: "EXENTO"}

        # Adaptar estructura
        adapted_data = {
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "establecimiento": invoice_data.get("establecimiento", "001"),
            "punto": invoice_data.get("punto", "001"),
            "numero": invoice_data.get("numero", "0000001"),
            "descripcion": invoice_data.get("descripcion", ""),
            "tipoDocumento": invoice_data.get("tipoDocumento"),
            "tipoEmision": invoice_data.get("tipoEmision"),
            "tipoTransaccion": invoice_data.get("tipoTransaccion"),
            "receiptid": invoice_data.get("receiptId", ""),
            "moneda": invoice_data.get("moneda", "PYG"),
            "cambio": invoice_data.get("cambio", 0),
            "codigoSeguridadAleatorio": invoice_data.get("codigoSeguridadAleatorio"),
        }

        # Adaptar datos del cliente
        cliente_data = invoice_data.get("cliente", {})
        adapted_data["cliente"] = {
            "ruc": cliente_data.get("ruc", ""),
            "nombre": cliente_data.get("razonSocial", ""),
            "direccion": cliente_data.get("direccion", "N/A"),
            "cpais": cliente_data.get("pais", "PRY"),
            "correo": cliente_data.get("email", ""),
            "numCasa": int(cliente_data.get("numeroCasa", 0)),
            "diplomatico": cliente_data.get("diplomatico", False),
            "dncp": int(cliente_data.get("dncp", 0)),
        }

        # Adaptar items
        items = []
        for item in invoice_data.get("items", []):
            # Calcular base gravable e IVA
            iva_tasa = item.get("iva", 10)
            cantidad = item.get("cantidad", 1)
            precio_unitario = item.get("precioUnitario", 0)
            precio_total = cantidad * precio_unitario

            if iva_tasa > 0:
                base_grav = precio_total / (1 + iva_tasa / 100)
                liq_iva = precio_total - base_grav
            else:
                base_grav = 0
                liq_iva = 0

            adapted_item = {
                "descripcion": item.get("descripcion", ""),
                "codigo": item.get("codigo", ""),
                "tipoIva": iva_mapping.get(iva_tasa, "I.V.A. 10%"),
                "unidadMedida": float(item.get("unidadMedida", 77)),
                "ivaTasa": iva_tasa,
                "ivaAfecta": item.get("ivaTipo", 1),
                "cantidad": cantidad,
                "precioUnitario": precio_unitario,
                "precioTotal": precio_total,
                "baseGravItem": round(base_grav, 8),
                "liqIvaItem": round(liq_iva, 8),
            }
            items.append(adapted_item)

        adapted_data["items"] = items

        # Adaptar condición de pago
        condicion = invoice_data.get("condicion", {})
        if condicion.get("tipo") == 2:  # Crédito
            # Adaptar información de crédito
            credito = condicion.get("credito", {})
            cuotas = []
            for i, cuota in enumerate(credito.get("infoCuotas", [])):
                cuotas.append(
                    {
                        "numero": i + 1,
                        "monto": cuota.get("monto", 0),
                        "fechaVencimiento": cuota.get("vencimiento", ""),
                    }
                )

            adapted_data["credito"] = {
                "condicionCredito": 2,  # Cuota
                "cantidadCuota": len(cuotas),
                "cuotas": cuotas,
            }
            adapted_data["condicionPago"] = 2  # Crédito
        else:
            # Contado
            adapted_data["pagos"] = [{}]  # Pago contado simplificado
            adapted_data["condicionPago"] = 1  # Contado

        # Calcular total
        total = sum(item["precioTotal"] for item in items)
        adapted_data["totalPago"] = total
        adapted_data["totalRedondeo"] = 0

        # Documentos asociados (Grupo H)
        if invoice_data.get("documentosAsociados"):
            adapted_data["documentosAsociados"] = invoice_data["documentosAsociados"]

        # Campos NRE (tipo 7)
        if invoice_data.get("remision"):
            adapted_data["remision"] = invoice_data["remision"]

        # Totales SIFEN
        if invoice_data.get("totales"):
            adapted_data["totales"] = invoice_data["totales"]

        return adapted_data

    def _process_response(self, response):
        """Procesar respuesta de FacturaSend"""
        try:
            data = response.json()
        except json.JSONDecodeError as err:
            _logger.error(f"Error decodificando JSON: {response.text}")
            raise UserError(_("Error en la respuesta del servidor")) from err

        if response.status_code == 200:
            if data.get("success"):
                return {"success": True, "result": data.get("result", {})}
            else:
                return {
                    "success": False,
                    "error": data.get("message", "Error desconocido"),
                }
        elif response.status_code == 400:
            # Error de validación
            errors = data.get("errors", {})
            error_messages = []
            for field, messages in errors.items():
                for msg in messages:
                    error_messages.append(f"{field}: {msg}")

            return {
                "success": False,
                "error": "\n".join(error_messages)
                or data.get("message", "Error de validación"),
            }
        elif response.status_code == 401:
            return {
                "success": False,
                "error": "Autenticación fallida. Verifique su API Key",
            }
        elif response.status_code == 404:
            return {
                "success": False,
                "error": "Endpoint no encontrado. Verifique la configuración",
            }
        elif response.status_code == 429:
            return {
                "success": False,
                "error": "Límite de rate excedido. Intente más tarde",
            }
        elif response.status_code == 500:
            return {"success": False, "error": "Error interno del servidor FacturaSend"}
        else:
            return {
                "success": False,
                "error": f"Error HTTP {response.status_code}: {response.text[:200]}",
            }

    def _log_request(self, operation_type, method, endpoint, data=None, response=None):
        """Registrar petición y respuesta"""
        log_vals = {
            "operation_type": operation_type,
            "provider": "facturasend",
            "method": method,
            "endpoint": endpoint,
            "request_data": json.dumps(data, indent=2) if data else "",
        }

        if response:
            log_vals.update(
                {
                    "status_code": response.status_code,
                    "response_data": response.text[:5000],
                    "success": response.status_code < 400,
                }
            )

        self.env["l10n_py.edi.log"].create(log_vals)

    # ============== PUBLIC METHODS ==============

    def test_connection(self):
        """Probar conexión con FacturaSend"""
        self.ensure_one()

        try:
            # Endpoint de prueba - obtener estado del servicio
            url = f"{self.base_url}/{self.tenant_id}/status"

            response = requests.get(
                url, headers=self._get_headers(), timeout=self.timeout
            )

            if response.status_code == 200:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Conexión Exitosa"),
                        "message": _("La conexión con FacturaSend fue exitosa"),
                        "type": "success",
                        "sticky": False,
                    },
                }
            else:
                raise UserError(
                    _("Error de conexión: HTTP %(code)s\n%(msg)s")
                    % {"code": response.status_code, "msg": response.text[:200]}
                )

        except requests.exceptions.Timeout as err:
            raise UserError(_("Timeout: El servidor no respondió a tiempo")) from err
        except requests.exceptions.ConnectionError as err:
            raise UserError(
                _("Error de conexión: No se pudo conectar con FacturaSend")
            ) from err
        except Exception as e:
            raise UserError(_("Error inesperado: %s") % str(e)) from e

    def send_document(self, invoice_data):
        """
        Enviar documento a FacturaSend

        :param invoice_data: Diccionario con los datos del documento
        :return: Diccionario con resultado de la operación
        """
        self.ensure_one()

        # Adaptar formato
        adapted_data = self._adapt_to_facturasend_format(invoice_data)

        # URL del endpoint
        url = f"{self.base_url}/{self.tenant_id}/lote/create"

        try:
            # Enviar petición
            response = requests.post(
                url,
                json=[adapted_data],  # FacturaSend espera un array
                headers=self._get_headers(),
                timeout=self.timeout,
            )

            # Registrar petición
            self._log_request("send", "POST", "/lote/create", adapted_data, response)

            # Procesar respuesta
            return self._process_response(response)

        except requests.exceptions.Timeout as err:
            raise UserError(
                _("Timeout: El servidor no respondió a tiempo: %s") % str(err)
            ) from err
        except requests.exceptions.ConnectionError as err:
            raise UserError(
                _("Error de conexión con FacturaSend: %s") % str(err)
            ) from err
        except Exception as e:
            _logger.exception("Error enviando documento a FacturaSend")
            raise UserError(_("Error inesperado: %s") % str(e)) from e

    def check_status(self, batch_id):
        """
        Consultar estado de un lote

        :param batch_id: ID del lote a consultar
        :return: Diccionario con el estado
        """
        self.ensure_one()

        url = f"{self.base_url}/{self.tenant_id}/lote/{batch_id}/status"

        try:
            response = requests.get(
                url, headers=self._get_headers(), timeout=self.timeout
            )

            self._log_request(
                "status", "GET", f"/lote/{batch_id}/status", None, response
            )

            return self._process_response(response)

        except Exception as e:
            _logger.exception("Error consultando estado del lote")
            return {"success": False, "error": str(e)}

    def cancel_document(self, cdc):
        """
        Cancelar documento electrónico

        :param cdc: CDC del documento a cancelar
        :return: Diccionario con resultado
        """
        self.ensure_one()

        url = f"{self.base_url}/{self.tenant_id}/documento/{cdc}/cancel"

        cancel_data = {"motivo": "Cancelación solicitada por el usuario"}

        try:
            response = requests.post(
                url, json=cancel_data, headers=self._get_headers(), timeout=self.timeout
            )

            self._log_request(
                "cancel", "POST", f"/documento/{cdc}/cancel", cancel_data, response
            )

            return self._process_response(response)

        except Exception as e:
            _logger.exception("Error cancelando documento")
            return {"success": False, "error": str(e)}

    def get_pdf(self, cdc):
        """
        Obtener KUDE (PDF) del documento

        :param cdc: CDC del documento
        :return: Contenido del PDF en base64 o False
        """
        self.ensure_one()

        url = f"{self.base_url}/{self.tenant_id}/documento/{cdc}/pdf"

        try:
            response = requests.get(
                url, headers=self._get_headers(), timeout=self.timeout
            )

            if response.status_code == 200:
                # Retornar el PDF en base64
                import base64

                return base64.b64encode(response.content).decode("utf-8")
            else:
                _logger.error(f"Error obteniendo PDF: {response.status_code}")
                return False

        except Exception:
            _logger.exception("Error obteniendo PDF")
            return False

    def get_xml(self, cdc):
        """
        Obtener XML del documento

        :param cdc: CDC del documento
        :return: Contenido del XML o False
        """
        self.ensure_one()

        url = f"{self.base_url}/{self.tenant_id}/documento/{cdc}/xml"

        try:
            response = requests.get(
                url, headers=self._get_headers(), timeout=self.timeout
            )

            if response.status_code == 200:
                return response.text
            else:
                _logger.error(f"Error obteniendo XML: {response.status_code}")
                return False

        except Exception:
            _logger.exception("Error obteniendo XML")
            return False
