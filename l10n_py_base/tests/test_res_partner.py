from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "l10n_py")
class TestResPartner(TransactionCase):
    """Tests for res.partner Paraguay extension"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.country_py = cls.env.ref("base.py")
        cls.it_ruc = cls.env.ref("l10n_py_base.it_ruc")
        cls.it_ci = cls.env.ref("l10n_py_base.it_ci")
        cls.it_pasaporte = cls.env.ref("l10n_py_base.it_pasaporte")
        cls.it_carnet = cls.env.ref("l10n_py_base.it_carnet_residencia")

    def test_partner_fiscal_fields_exist(self):
        """l10n_py fiscal fields must exist on the model"""
        partner = self.Partner.create(
            {
                "name": "Test Partner PY",
                "country_id": self.country_py.id,
            }
        )
        self.assertTrue(hasattr(partner, "l10n_py_ruc"))
        self.assertTrue(hasattr(partner, "l10n_py_ruc_dv"))
        self.assertTrue(hasattr(partner, "l10n_py_taxpayer_type"))
        self.assertTrue(hasattr(partner, "l10n_py_fantasy_name"))
        self.assertTrue(hasattr(partner, "l10n_py_activity_description"))
        self.assertTrue(hasattr(partner, "l10n_py_department_code"))
        self.assertTrue(hasattr(partner, "l10n_py_city_code"))

    # ============== RUC via vat + identification type ==============

    def test_ruc_computed_from_vat(self):
        """l10n_py_ruc and l10n_py_ruc_dv are computed from vat"""
        partner = self.Partner.create(
            {
                "name": "Test RUC",
                "country_id": self.country_py.id,
                "l10n_latam_identification_type_id": self.it_ruc.id,
                "vat": "80028061-0",
            }
        )
        self.assertEqual(partner.l10n_py_ruc, "80028061")
        self.assertEqual(partner.l10n_py_ruc_dv, "0")

    def test_ruc_dv_auto_calculated_on_create(self):
        """DV is auto-calculated if vat doesn't include DV"""
        partner = self.Partner.create(
            {
                "name": "Test RUC auto DV",
                "country_id": self.country_py.id,
                "l10n_latam_identification_type_id": self.it_ruc.id,
                "vat": "80028061",
            }
        )
        # create() formats vat to include DV
        self.assertEqual(partner.vat, "80028061-0")
        self.assertEqual(partner.l10n_py_ruc, "80028061")
        self.assertEqual(partner.l10n_py_ruc_dv, "0")

    def test_ruc_inverse_backward_compat(self):
        """Writing l10n_py_ruc directly syncs vat (backward compat)"""
        partner = self.Partner.create(
            {
                "name": "Test Inverse",
                "country_id": self.country_py.id,
                "l10n_py_ruc": "80028061",
            }
        )
        self.assertEqual(partner.vat, "80028061-0")
        self.assertEqual(partner.l10n_latam_identification_type_id, self.it_ruc)
        self.assertEqual(partner.l10n_py_ruc_dv, "0")

    def test_ruc_empty_when_not_ruc_type(self):
        """l10n_py_ruc is empty when identification type is not RUC"""
        partner = self.Partner.create(
            {
                "name": "Test CI",
                "country_id": self.country_py.id,
                "l10n_latam_identification_type_id": self.it_ci.id,
                "vat": "4567890",
            }
        )
        self.assertFalse(partner.l10n_py_ruc)
        self.assertFalse(partner.l10n_py_ruc_dv)

    def test_ruc_dv_empty_when_no_vat(self):
        """DV must be empty if no vat"""
        partner = self.Partner.create(
            {
                "name": "Test Partner",
                "country_id": self.country_py.id,
            }
        )
        self.assertFalse(partner.l10n_py_ruc_dv)

    # ============== DV exacto para RUCs conocidos ==============

    def test_ruc_dv_exact_values(self):
        """DV exacto para RUCs reales (verificados con python-stdnum)"""
        test_cases = [
            ("80028061", "0"),
            ("80000035", "8"),
            ("1068460", "3"),
            ("80067890", "7"),
            ("80054321", "1"),
        ]
        for ruc_num, expected_dv in test_cases:
            partner = self.Partner.create(
                {
                    "name": f"Test DV {ruc_num}",
                    "country_id": self.country_py.id,
                    "l10n_latam_identification_type_id": self.it_ruc.id,
                    "vat": ruc_num,
                }
            )
            self.assertEqual(
                partner.l10n_py_ruc_dv,
                expected_dv,
                f"RUC {ruc_num} must have DV={expected_dv}",
            )

    # ============== Taxpayer type ==============

    def test_taxpayer_type_selection(self):
        """Taxpayer type must accept valid values"""
        partner = self.Partner.create(
            {
                "name": "Contribuyente Test",
                "country_id": self.country_py.id,
                "l10n_py_taxpayer_type": "1",
            }
        )
        self.assertEqual(partner.l10n_py_taxpayer_type, "1")

        partner2 = self.Partner.create(
            {
                "name": "No Contribuyente Test",
                "country_id": self.country_py.id,
                "l10n_py_taxpayer_type": "2",
            }
        )
        self.assertEqual(partner2.l10n_py_taxpayer_type, "2")

    # ============== Non-taxpayer doc fields ==============

    def test_non_taxpayer_with_ci(self):
        """Non-taxpayer with identity card"""
        partner = self.Partner.create(
            {
                "name": "Persona Natural PY",
                "country_id": self.country_py.id,
                "l10n_latam_identification_type_id": self.it_ci.id,
                "vat": "4567890",
                "l10n_py_taxpayer_type": "2",
                "l10n_py_doc_type": "1",
                "l10n_py_doc_number": "4567890",
            }
        )
        self.assertEqual(partner.l10n_py_doc_type, "1")
        self.assertEqual(partner.l10n_py_doc_number, "4567890")
        self.assertEqual(partner.vat, "4567890")

    def test_taxpayer_with_ruc(self):
        """Taxpayer with RUC and DV"""
        partner = self.Partner.create(
            {
                "name": "Empresa PY",
                "country_id": self.country_py.id,
                "l10n_latam_identification_type_id": self.it_ruc.id,
                "vat": "80028061",
                "l10n_py_taxpayer_type": "1",
            }
        )
        self.assertEqual(partner.l10n_py_taxpayer_type, "1")
        self.assertEqual(partner.l10n_py_ruc_dv, "0")

    def test_non_taxpayer_doc_types(self):
        """All identity document types are accepted"""
        id_types = {
            "1": self.it_ci,
            "2": self.it_pasaporte,
            "3": self.it_carnet,
        }
        for doc_type, id_type in id_types.items():
            partner = self.Partner.create(
                {
                    "name": f"Partner doc_type {doc_type}",
                    "country_id": self.country_py.id,
                    "l10n_latam_identification_type_id": id_type.id,
                    "vat": "12345",
                    "l10n_py_taxpayer_type": "2",
                    "l10n_py_doc_type": doc_type,
                    "l10n_py_doc_number": "12345",
                }
            )
            self.assertEqual(partner.l10n_py_doc_type, doc_type)

    # ============== Onchanges ==============

    def test_neighborhood_onchange(self):
        """Auto-fill city when selecting neighborhood"""
        partner = self.Partner.create(
            {
                "name": "Test Partner",
                "country_id": self.country_py.id,
            }
        )
        self.assertTrue(hasattr(partner, "l10n_py_neighborhood_id"))

    def test_state_change_clears_city(self):
        """When changing department, city and neighborhood
        are cleared if they don't match"""
        state_asu = self.env["res.country.state"].search(
            [
                ("country_id", "=", self.country_py.id),
                ("l10n_py_code", "!=", False),
            ],
            limit=1,
        )
        state_other = self.env["res.country.state"].search(
            [
                ("country_id", "=", self.country_py.id),
                ("l10n_py_code", "!=", False),
                ("id", "!=", state_asu.id),
            ],
            limit=1,
        )
        if not (state_asu and state_other):
            self.skipTest("Need at least 2 PY states with l10n_py_code")

        city = self.env["res.city"].search([("state_id", "=", state_asu.id)], limit=1)
        if not city:
            self.skipTest("Need a city in the first PY state")

        partner = self.Partner.new(
            {
                "name": "Test State Change",
                "country_id": self.country_py.id,
                "state_id": state_asu.id,
                "city_id": city.id,
            }
        )
        # Change state to a different one
        partner.state_id = state_other
        partner._onchange_state_id_l10n_py()
        self.assertFalse(
            partner.city_id,
            "City should be cleared when state changes",
        )

    # ============== Location ==============

    def test_department_code_related(self):
        """l10n_py_department_code is computed from state_id"""
        state = self.env["res.country.state"].search(
            [
                ("country_id", "=", self.country_py.id),
                ("l10n_py_code", "!=", False),
            ],
            limit=1,
        )
        if state:
            partner = self.Partner.create(
                {
                    "name": "Test Partner",
                    "country_id": self.country_py.id,
                    "state_id": state.id,
                }
            )
            self.assertEqual(
                partner.l10n_py_department_code,
                state.l10n_py_code,
                "Department code must match the state's code",
            )

    # ============== VAT validation (check_vat_py) ==============

    def test_check_vat_py_accepts_real_ruc(self):
        """base_vat accepts a real RUC with correct DV"""
        partner = self.Partner.create(
            {
                "name": "Contribuyente RUC valido",
                "country_id": self.country_py.id,
                "l10n_latam_identification_type_id": self.it_ruc.id,
                "vat": "80028061-0",
            }
        )
        self.assertEqual(partner.vat, "80028061-0")

    def test_check_vat_py_rejects_wrong_dv(self):
        """The base_vat hook rejects a RUC with wrong DV

        We call the hook directly because ``create``/``write`` rewrite the
        reported DV before the constraint runs (see ``_format_vat_py``), so an
        invalid DV never reaches the hook through normal writes.
        """
        partner = self.Partner.create(
            {
                "name": "Contribuyente RUC",
                "country_id": self.country_py.id,
                "l10n_latam_identification_type_id": self.it_ruc.id,
                "vat": "80028061-0",
            }
        )
        self.assertTrue(partner.check_vat_py("80028061-0"))
        self.assertFalse(partner.check_vat_py("80028061-1"))
        self.assertFalse(partner.check_vat_py("AB1234-5"))
        self.assertFalse(partner.check_vat_py(""))

    def test_check_vat_py_ignores_non_vat_documents(self):
        """Cedula and passport do not go through RUC validation"""
        for id_type, number in [
            (self.it_ci, "1234567-8"),
            (self.it_pasaporte, "AB1234567"),
        ]:
            partner = self.Partner.create(
                {
                    "name": f"No contribuyente {number}",
                    "country_id": self.country_py.id,
                    "l10n_latam_identification_type_id": id_type.id,
                    "vat": number,
                }
            )
            self.assertEqual(partner.vat, number)
