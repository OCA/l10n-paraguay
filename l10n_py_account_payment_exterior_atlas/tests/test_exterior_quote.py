# Copyright 2026 KMEE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from unittest import mock

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install", "l10n_py")
class TestExteriorQuote(AccountTestInvoicingCommon):
    def setUp(self):
        super().setUp()
        self.company_bank_account = self.env["res.partner.bank"].create(
            {
                "acc_number": "ATLAS-EXT-0001",
                "partner_id": self.company_data["company"].partner_id.id,
                "atlas_enabled": True,
                "atlas_numero_cuenta": "1285242",
                "atlas_api_key": "test-key",
                "atlas_private_key_pem": "-----BEGIN PRIVATE KEY-----\n...",
            }
        )
        self.transfer = self.env["l10n_py.atlas.exterior.transfer"].create(
            {
                "company_bank_account_id": self.company_bank_account.id,
                "moneda": "USD",
                "monto_transferencia": 101,
                "codigo_motivo": "5",
                "tipo_cargo": "OUR",
                "plazo": "24",
                "beneficiario_nombre": "Javier Meza",
                "beneficiario_cuenta": "3973099",
                "beneficiario_swift": "VISCPYPA",
                "beneficiario_pais": 1,
                "beneficiario_ciudad": 1,
                "beneficiario_direccion": "Some street 123",
            }
        )

    @mock.patch(
        "odoo.addons.l10n_py_account_payment_atlas.models.atlas_api_client."
        "AtlasApiClient.call"
    )
    def test_cotizar_stores_the_reference_and_fees(self, mock_call):
        mock_call.return_value = {
            "datosOperacion": {
                "numeroReferencia": 1911217,
                "montoCargo": 25,
                "montoCargoIntermediario": 16.5,
                "montoCargoPlazo": 40,
                "total_debito": 182.5,
            },
            "respuesta": {"estado": "OK", "mensaje": None},
        }
        self.transfer.action_atlas_cotizar()
        self.assertEqual(self.transfer.numero_referencia, 1911217)
        self.assertEqual(self.transfer.total_debito, 182.5)
        self.assertEqual(self.transfer.state, "quoted")
        # AtlasApiClient.call() is always invoked as call(method, path,
        # body=...) -- body is a keyword arg, never positional -- so read
        # it from kwargs, not from call_args.args.
        _, kwargs = mock_call.call_args
        sent_body = kwargs["body"]
        self.assertEqual(sent_body["modo"], "V")
