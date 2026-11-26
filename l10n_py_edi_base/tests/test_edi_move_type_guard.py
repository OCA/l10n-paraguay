# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from lxml import etree

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

EDI_BUTTONS = (
    "action_preview_xml",
    "action_preview_kude",
    "action_l10n_py_preview_qr",
    "action_send_edi",
)
GUARD_MESSAGE = "proveedor"


@tagged("post_install", "-at_install", "l10n_py")
class TestEDIMoveTypeGuard(TransactionCase):
    """Only the issuer transmits a DE: vendor bills never go to SIFEN."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Proveedor Test"})

    def _move(self, move_type):
        return self.env["account.move"].create(
            {"move_type": move_type, "partner_id": self.partner.id}
        )

    def test_vendor_bills_are_refused(self):
        for move_type in ("in_invoice", "in_refund"):
            move = self._move(move_type)
            for action in ("action_send_edi", "action_preview_xml"):
                with (
                    self.subTest(move_type=move_type, action=action),
                    self.assertRaisesRegex(UserError, GUARD_MESSAGE),
                ):
                    getattr(move, action)()

    def test_customer_invoice_passes_the_guard(self):
        """The guard must not block customer moves; other validations still apply."""
        move = self._move("out_invoice")
        try:
            move._validate_edi_data()
        except UserError as error:
            self.assertNotIn(GUARD_MESSAGE, str(error))

    def test_edi_buttons_hidden_on_vendor_bills(self):
        arch = etree.fromstring(
            self.env["account.move"].get_view(view_type="form")["arch"]
        )
        for name in EDI_BUTTONS:
            with self.subTest(button=name):
                button = arch.xpath(f"//header/button[@name='{name}']")[0]
                self.assertIn(
                    "move_type not in ['out_invoice', 'out_refund']",
                    button.get("invisible"),
                )
