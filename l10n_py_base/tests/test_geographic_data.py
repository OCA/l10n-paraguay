from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "l10n_py")
class TestGeographicData(TransactionCase):
    """Tests for Paraguay geographic data"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_py = cls.env.ref("base.py")

    def test_departments_loaded(self):
        """17 PY departments must be loaded"""
        departments = self.env["res.country.state"].search(
            [("country_id", "=", self.country_py.id)]
        )
        self.assertGreaterEqual(
            len(departments), 17, "Must have at least 17 departments"
        )

    def test_department_set_codes(self):
        """Departments must have SET codes"""
        departments = self.env["res.country.state"].search(
            [
                ("country_id", "=", self.country_py.id),
                ("l10n_py_code", "!=", False),
                ("l10n_py_code", "!=", 0),
            ]
        )
        self.assertGreater(
            len(departments), 0, "At least one department must have SET code"
        )

    def test_cities_loaded(self):
        """PY cities must be loaded"""
        cities = self.env["res.city"].search([("country_id", "=", self.country_py.id)])
        self.assertGreater(len(cities), 0, "Must have cities loaded")

    def test_neighborhoods_loaded(self):
        """Neighborhoods must be loaded"""
        neighborhoods = self.env["l10n_py.neighborhood"].search([])
        self.assertGreater(len(neighborhoods), 0, "Must have neighborhoods loaded")

    # ============== SET code uniqueness constraint ==============

    def test_set_code_unique_per_country(self):
        """Two departments in the same country cannot share a SET code."""
        State = self.env["res.country.state"]
        State.create(
            {
                "name": "PY Test Dept A",
                "country_id": self.country_py.id,
                "code": "QW",
                "l10n_py_code": 9991,
            }
        )
        with self.assertRaises(ValidationError):
            State.create(
                {
                    "name": "PY Test Dept B",
                    "country_id": self.country_py.id,
                    "code": "QX",
                    "l10n_py_code": 9991,
                }
            )

    def test_set_code_reused_across_countries(self):
        """The same SET code is allowed in different countries (per-country)."""
        State = self.env["res.country.state"]
        country_ar = self.env.ref("base.ar")
        State.create(
            {
                "name": "PY Test Dept",
                "country_id": self.country_py.id,
                "code": "QY",
                "l10n_py_code": 9992,
            }
        )
        state_ar = State.create(
            {
                "name": "AR Test Prov",
                "country_id": country_ar.id,
                "code": "QY",
                "l10n_py_code": 9992,
            }
        )
        self.assertTrue(state_ar.id)
