# l10n_py_edi_factpy/models/factpy_connector.py

import json
import logging
from datetime import datetime

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class FactPyConnector(models.Model):
    _name = "l10n_py.edi.connector.factpy"
    _description = "FactPy EDI Connector for Paraguay"
    _rec_name = "name"

    # ============== CONFIGURATION FIELDS ==============

    name = fields.Char(string="Nombre", required=True, default="FactPy Connector")

    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
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
                record.base_url = "https://api-test.factpy.com"
            else:
                record.base_url = "https://api.factpy.com"

    # ============== PRIVATE METHODS ==============

    def _get_headers(self):
        """Obtener headers para las peticiones"""
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _get_token(self):
        """Obtener token de acceso usando API Key y Secret"""
        try:
            url = f"{self.base_url}/auth/token"
            response = requests.post(
                url,
                json={"api_key": self.api_key, "api_secret": self.api_secret},
                timeout=self.timeout,
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("access_token")
            else:
                raise UserError(_("Error obteniendo token: %s") % response.text)

        except Exception as e:
            _logger.error(f"Error getting FactPy token: {str(e)}")
            raise UserError(_("Error de autenticación con FactPy: %s") % str(e)) from e

    def _adapt_to_factpy_format(self, invoice_data):
        """
        Adaptar formato de datos del módulo base al formato FactPy
        """
        # Adaptar estructura básica (similar a FacturaSend
        # pero con campos específicos de FactPy)
        adapted_data = {
            "fechaEmision": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "establecimiento": invoice_data.get("establecimiento", "001"),
            "puntoExpedicion": invoice_data.get("punto", "001"),
            "numeroFactura": invoice_data.get("numero", "0000001"),
            "tipoDocumento": invoice_data.get("tipoDocumento"),
            "tipoEmision": invoice_data.get("tipoEmision"),
            "tipoTransaccion": invoice_data.get("tipoTransaccion"),
            "cliente": invoice_data.get("cliente", {}),
            "detalles": invoice_data.get("items", []),
            "condicionPago": invoice_data.get("condicion", {}).get("tipo", 1),
            "moneda": invoice_data.get("moneda", "PYG"),
        }

        # Adaptar condición de pago
        if adapted_data["condicionPago"] == 2:  # Crédito
            adapted_data["cuotas"] = (
                invoice_data.get("condicion", {})
                .get("credito", {})
                .get("infoCuotas", [])
            )

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
        """Procesar respuesta de FactPy"""
        try:
            data = response.json()
        except json.JSONDecodeError as err:
            _logger.error(f"Error decodificando JSON: {response.text}")
            raise UserError(
                _("Error en la respuesta del servidor: %s") % response.text
            ) from err

        if response.status_code == 200:
            if data.get("success"):
                return {"success": True, "result": data.get("data", {})}
            else:
                return {
                    "success": False,
                    "error": data.get("message", _("Error desconocido")),
                }
        elif response.status_code == 400:
            # Error de validación
            errors = data.get("errors", {})
            error_messages = []
            for field, messages in errors.items():
                if isinstance(messages, list):
                    for msg in messages:
                        error_messages.append(f"{field}: {msg}")
                else:
                    error_messages.append(f"{field}: {messages}")

            return {
                "success": False,
                "error": "\n".join(error_messages)
                or data.get("message", _("Error de validación")),
            }
        elif response.status_code == 401:
            return {
                "success": False,
                "error": _("Autenticación fallida. Verifique sus credenciales"),
            }
        elif response.status_code == 404:
            return {
                "success": False,
                "error": _("Endpoint no encontrado. Verifique la configuración"),
            }
        elif response.status_code == 429:
            return {
                "success": False,
                "error": _("Límite de rate excedido. Intente más tarde"),
            }
        elif response.status_code == 500:
            return {"success": False, "error": _("Error interno del servidor FactPy")}
        else:
            return {
                "success": False,
                "error": f"Error HTTP {response.status_code}: {response.text[:200]}",
            }

    def _log_request(self, operation_type, method, endpoint, data=None, response=None):
        """Registrar petición y respuesta"""
        log_vals = {
            "operation_type": operation_type,
            "provider": "factpy",
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
        """Probar conexión con FactPy"""
        self.ensure_one()

        try:
            # Endpoint de prueba - obtener información del usuario
            url = f"{self.base_url}/user/info"

            response = requests.get(
                url, headers=self._get_headers(), timeout=self.timeout
            )

            if response.status_code == 200:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Conexión Exitosa"),
                        "message": _("La conexión con FactPy fue exitosa"),
                        "type": "success",
                        "sticky": False,
                    },
                }
            else:
                raise UserError(
                    _("Error de conexión: HTTP %(status_code)s\n%(response_text)s")
                    % {
                        "status_code": response.status_code,
                        "response_text": response.text[:200],
                    }
                )

        except requests.exceptions.Timeout as e:
            raise UserError(
                _("Timeout: El servidor no respondió a tiempo: %s") % str(e)
            ) from e
        except requests.exceptions.ConnectionError as e:
            raise UserError(
                _("Error de conexión: No se pudo conectar con FactPy: %s") % str(e)
            ) from e
        except Exception as e:
            raise UserError(_("Error inesperado: %s") % str(e)) from e

    def send_document(self, invoice_data):
        """
        Enviar documento a FactPy

        :param invoice_data: Diccionario con los datos del documento
        :return: Diccionario con resultado de la operación
        """
        self.ensure_one()

        # Adaptar formato
        adapted_data = self._adapt_to_factpy_format(invoice_data)

        # URL del endpoint
        url = f"{self.base_url}/documents/send"

        try:
            # Enviar petición
            response = requests.post(
                url,
                json=adapted_data,
                headers=self._get_headers(),
                timeout=self.timeout,
            )

            # Registrar petición
            self._log_request("send", "POST", "/documents/send", adapted_data, response)

            # Procesar respuesta
            return self._process_response(response)

        except requests.exceptions.Timeout as e:
            raise UserError(
                _("Timeout: El servidor no respondió a tiempo: %s") % str(e)
            ) from e
        except requests.exceptions.ConnectionError as e:
            raise UserError(_("Error de conexión con FactPy: %s") % str(e)) from e
        except Exception as e:
            _logger.exception("Error enviando documento a FactPy")
            return {"success": False, "error": str(e)}

    def check_status(self, document_id):
        """
        Consultar estado de un documento

        :param document_id: ID del documento a consultar
        :return: Diccionario con el estado
        """
        self.ensure_one()

        url = f"{self.base_url}/documents/{document_id}/status"

        try:
            response = requests.get(
                url, headers=self._get_headers(), timeout=self.timeout
            )

            self._log_request(
                "status", "GET", f"/documents/{document_id}/status", None, response
            )

            return self._process_response(response)

        except Exception as e:
            _logger.exception("Error consultando estado del documento")
            return {"success": False, "error": str(e)}

    def cancel_document(
        self, document_id, reason="Cancelación solicitada por el usuario"
    ):
        """
        Cancelar documento electrónico

        :param document_id: ID del documento a cancelar
        :param reason: Motivo de cancelación
        :return: Diccionario con resultado
        """
        self.ensure_one()

        url = f"{self.base_url}/documents/{document_id}/cancel"

        cancel_data = {"reason": reason}

        try:
            response = requests.post(
                url, json=cancel_data, headers=self._get_headers(), timeout=self.timeout
            )

            self._log_request(
                "cancel",
                "POST",
                f"/documents/{document_id}/cancel",
                cancel_data,
                response,
            )

            return self._process_response(response)

        except Exception as e:
            _logger.exception("Error cancelando documento")
            return {"success": False, "error": str(e)}

    def get_pdf(self, document_id):
        """
        Obtener PDF del documento

        :param document_id: ID del documento
        :return: Contenido del PDF en base64 o False
        """
        self.ensure_one()

        url = f"{self.base_url}/documents/{document_id}/pdf"

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

    def get_xml(self, document_id):
        """
        Obtener XML del documento

        :param document_id: ID del documento
        :return: Contenido del XML o False
        """
        self.ensure_one()

        url = f"{self.base_url}/documents/{document_id}/xml"

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
