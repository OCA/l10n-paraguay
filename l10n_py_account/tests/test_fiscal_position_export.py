from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "l10n_py")
class TestFiscalPositionExport(TransactionCase):
    def test_export_fp_maps_vat_to_exonerado(self):
        company = self.env["res.company"].create({"name": "PY Co FP"})
        self.env["account.chart.template"].try_loading("py", company=company, install_demo=False)
        fp = self.env["account.fiscal.position"].with_company(company).search(
            [("name", "=", "Ventas - Exportación")], limit=1)
        self.assertTrue(fp, "FP de exportación debe existir")
        vat10 = self.env["account.tax"].with_company(company).search(
            [("type_tax_use", "=", "sale"), ("amount", "=", 10)], limit=1)
        mapped = fp.map_tax(vat10)
        self.assertEqual(mapped.l10n_py_iva_affectation, "2",
                         "La FP debe mapear IVA 10% venta -> exonerado (afectación 2)")

    def test_foreign_partner_gets_export_fp(self):
        company = self.env["res.company"].create({"name": "PY Co Rank"})
        self.env["account.chart.template"].try_loading("py", company=company, install_demo=False)
        foreign = self.env["res.partner"].create({
            "name": "Cliente Brasil", "country_id": self.env.ref("base.br").id})
        fp = self.env["account.fiscal.position"].with_company(company)._get_fiscal_position(foreign)
        self.assertEqual(fp.name, "Ventas - Exportación",
                         "Parceiro do exterior deve resolver a FP de exportación")
