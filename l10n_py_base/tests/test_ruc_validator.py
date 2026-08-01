from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from ..validators.ruc_validator import RUCValidator

# Real Paraguayan RUCs, taken from the python-stdnum test corpus
# (stdnum/tests/test_py_ruc.doctest). Legal entities start after 80000000;
# residents and foreigners use shorter numbers.
REAL_RUCS = [
    "80028061-0",
    "80000035-8",
    "1068460-3",
    "1075150-5",
    "1152390-5",
    "999160-3",
    "2660-3",
]


@tagged("post_install", "-at_install", "l10n_py")
class TestRucValidator(TransactionCase):
    """Tests for Paraguayan RUC validator"""

    def test_check_digit_known_values(self):
        """DV correcto para RUCs reales (algoritmo modulo 11 de la SET)"""
        test_cases = [
            ("80028061", 0),
            ("80000035", 8),
            ("1068460", 3),
            ("999160", 3),
            ("2660", 3),
        ]
        for ruc_number, expected_dv in test_cases:
            self.assertEqual(
                RUCValidator._calculate_check_digit(ruc_number),
                expected_dv,
                f"RUC {ruc_number} should have DV={expected_dv}",
            )

    def test_valid_ruc_with_correct_dv(self):
        """Real RUCs with correct DV must pass validation"""
        for ruc in REAL_RUCS:
            is_valid, error = RUCValidator.validate(ruc)
            self.assertTrue(
                is_valid,
                f"RUC {ruc} should be valid, error: {error}",
            )

    def test_valid_ruc_without_dash(self):
        """The dash is optional: 800280610 is equivalent to 80028061-0"""
        is_valid, error = RUCValidator.validate("800280610")
        self.assertTrue(is_valid, error)

    def test_invalid_ruc_wrong_dv(self):
        """RUC with wrong DV must be invalid"""
        is_valid, error = RUCValidator.validate("80028061-1")
        self.assertFalse(is_valid)
        self.assertIn("Invalid check digit", error)
        self.assertIn("Expected: 0", error)

    def test_invalid_ruc_letters(self):
        """RUC with letters must be invalid"""
        is_valid, _error = RUCValidator.validate("AB1234-5")
        self.assertFalse(is_valid)
        self.assertFalse(RUCValidator.is_valid_format("1234567A"))

    def test_invalid_ruc_too_long(self):
        """RUC with more than 9 digits must be invalid"""
        is_valid, _error = RUCValidator.validate("1234567890")
        self.assertFalse(is_valid)

    def test_invalid_ruc_empty(self):
        """Empty RUC must be invalid"""
        is_valid, error = RUCValidator.validate("")
        self.assertFalse(is_valid)
        self.assertIn("required", error)

    def test_leading_zeros_do_not_change_dv(self):
        """Leading zeros do not alter the DV"""
        self.assertEqual(
            RUCValidator._calculate_check_digit("0002660"),
            RUCValidator._calculate_check_digit("2660"),
        )
        is_valid, error = RUCValidator.validate("0002660-3")
        self.assertTrue(is_valid, error)

    def test_ruc_normalization(self):
        """Normalization returns the NNNNNNNN-D format"""
        self.assertEqual(RUCValidator.normalize("800280610"), "80028061-0")
        self.assertEqual(RUCValidator.normalize("80028061-0"), "80028061-0")

    @mute_logger("odoo.addons.l10n_py_base.validators.ruc_validator")
    def test_normalize_invalid_returns_original(self):
        """An invalid RUC is returned unchanged (and a warning is logged)"""
        self.assertEqual(RUCValidator.normalize("80028061-1"), "80028061-1")

    def test_get_check_digit(self):
        """Get check digit"""
        self.assertEqual(RUCValidator.get_check_digit("80028061"), "0")

    def test_format_ruc_includes_dv(self):
        """Format RUC with computed DV"""
        self.assertEqual(RUCValidator.format_ruc("80028061"), "80028061-0")

    def test_format_ruc_excludes_dv(self):
        """Format RUC without DV"""
        formatted = RUCValidator.format_ruc("80028061", include_dv=False)
        self.assertEqual(formatted, "80028061")
        self.assertNotIn("-", formatted)

    def test_get_ruc_number(self):
        """Extract only RUC number"""
        self.assertEqual(RUCValidator.get_ruc_number("80028061-0"), "80028061")

    def test_get_ruc_number_from_full(self):
        """Extract RUC number from full format (concatenated digits)"""
        self.assertEqual(RUCValidator.get_ruc_number("800280610"), "80028061")
