# l10n_py_base/models/res_partner.py

from odoo import api, fields, models

from ..validators.ruc_validator import RUCValidator


class ResPartner(models.Model):
    """Extension of res.partner for Paraguay with fiscal fields"""

    _inherit = "res.partner"

    # ============== DEFAULT COUNTRY ==============

    country_id = fields.Many2one(
        comodel_name="res.country",
        default=lambda self: self._default_country_id(),
    )

    def _default_country_id(self):
        """Default country set to Paraguay if the current company is Paraguayan."""
        return (
            self.env.ref("base.py", raise_if_not_found=False)
            if self.env.company.country_id.code == "PY"
            else False
        )

    # ============== PY FISCAL FIELDS ==============

    l10n_py_ruc = fields.Char(
        string="Tax ID (RUC)",
        size=20,
        compute="_compute_l10n_py_ruc_fields",
        inverse="_inverse_l10n_py_ruc",
        store=True,
        help="Single Taxpayer Registry (without check digit)",
    )

    l10n_py_ruc_dv = fields.Char(
        string="DV",
        size=1,
        compute="_compute_l10n_py_ruc_fields",
        store=True,
        help="RUC check digit",
    )

    l10n_py_taxpayer_type = fields.Selection(
        [
            ("1", "Taxpayer"),
            ("2", "Non-Taxpayer"),
        ],
        string="Taxpayer Type",
        help="Taxpayer type according to SET",
    )

    l10n_py_fantasy_name = fields.Char(
        string="Trade Name",
        help="Commercial or trade name",
    )

    l10n_py_activity_description = fields.Char(
        string="Economic Activity",
        help="Description of the main economic activity",
    )

    l10n_py_doc_type = fields.Selection(
        [
            ("1", "Identity Card"),
            ("2", "Passport"),
            ("3", "Residence Permit"),
            ("4", "Unnamed"),
        ],
        string="Identity Document Type",
        help="Identity document type for non-taxpayers (SIFEN D024)",
    )

    l10n_py_doc_number = fields.Char(
        string="Document Number",
        size=20,
        help="Identity document number for non-taxpayers (SIFEN D025)",
    )

    # ============== LOCATION FIELDS (RELATED) ==============

    l10n_py_department_code = fields.Integer(
        string="SET Department Code",
        related="state_id.l10n_py_code",
        store=True,
        readonly=True,
        help="Department code according to SET",
    )

    l10n_py_city_code = fields.Char(
        string="SET City Code",
        related="city_id.l10n_py_code",
        store=True,
        readonly=True,
        help="City code according to SET",
    )

    # ============== NEIGHBORHOOD FIELDS ==============

    l10n_py_neighborhood_id = fields.Many2one(
        comodel_name="l10n_py.neighborhood",
        string="Neighborhood",
        domain="[('city_id', '=', city_id)]",
        help="Neighborhood or district of the contact",
    )

    l10n_py_neighborhood_name = fields.Char(
        string="Neighborhood Name",
        related="l10n_py_neighborhood_id.name",
        store=True,
        readonly=True,
    )

    # ============== COMPUTE METHODS ==============

    @api.depends("vat", "l10n_latam_identification_type_id")
    def _compute_l10n_py_ruc_fields(self):
        """Compute l10n_py_ruc and l10n_py_ruc_dv from vat field."""
        ruc_type = self.env.ref("l10n_py_base.it_ruc", raise_if_not_found=False)
        for partner in self:
            if (
                ruc_type
                and partner.l10n_latam_identification_type_id == ruc_type
                and partner.vat
            ):
                vat_clean = partner.vat.strip()
                if "-" in vat_clean:
                    parts = vat_clean.split("-", 1)
                    partner.l10n_py_ruc = parts[0]
                    partner.l10n_py_ruc_dv = parts[1]
                else:
                    ruc_num = "".join(c for c in vat_clean if c.isdigit())
                    partner.l10n_py_ruc = ruc_num
                    partner.l10n_py_ruc_dv = str(
                        RUCValidator._calculate_check_digit(ruc_num)
                    )
            else:
                partner.l10n_py_ruc = False
                partner.l10n_py_ruc_dv = False

    def _inverse_l10n_py_ruc(self):
        """When l10n_py_ruc is written directly, sync to vat field."""
        ruc_type = self.env.ref("l10n_py_base.it_ruc", raise_if_not_found=False)
        for partner in self:
            if partner.l10n_py_ruc:
                ruc_num = partner.l10n_py_ruc.strip()
                dv = str(RUCValidator._calculate_check_digit(ruc_num))
                partner.vat = f"{ruc_num}-{dv}"
                if ruc_type:
                    partner.l10n_latam_identification_type_id = ruc_type

    # ============== CREATE / WRITE ==============

    @api.model_create_multi
    def create(self, vals_list):
        ruc_type = self.env.ref("l10n_py_base.it_ruc", raise_if_not_found=False)
        for vals in vals_list:
            # Backward compat: convert l10n_py_ruc to vat + identification type
            if vals.get("l10n_py_ruc") and not vals.get("vat"):
                ruc_num = vals.pop("l10n_py_ruc").strip()
                dv = str(RUCValidator._calculate_check_digit(ruc_num))
                vals["vat"] = f"{ruc_num}-{dv}"
                if ruc_type:
                    vals.setdefault("l10n_latam_identification_type_id", ruc_type.id)
            self._format_vat_py(vals)
        return super().create(vals_list)

    def write(self, values):
        if any(
            f in values
            for f in ["vat", "l10n_latam_identification_type_id", "country_id"]
        ):
            for record in self:
                vat_values = {
                    "vat": values.get("vat", record.vat),
                    "l10n_latam_identification_type_id": values.get(
                        "l10n_latam_identification_type_id",
                        record.l10n_latam_identification_type_id.id,
                    ),
                    "country_id": values.get("country_id", record.country_id.id),
                }
                formatted = self._format_vat_py(vat_values)
                if formatted:
                    values["vat"] = formatted
        return super().write(values)

    @api.model
    def format_vat_py(self, vat):
        """Keep already formatted Paraguayan RUC values in RUC-DV format.

        Odoo's base_vat falls back to python-stdnum's compact() for PY,
        which strips the hyphen from RUC numbers. This override prevents
        compacting values that are already in the local SET format.

        Do not add a DV here: base_vat only knows the country, not whether
        the document number is a RUC, CI, passport, or residence card.
        RUC auto-formatting is handled by _format_vat_py() when the LATAM
        identification type is explicitly RUC.
        """
        vat_clean = vat.strip() if vat else vat
        if vat_clean and "-" in vat_clean:
            return vat_clean
        return vat_clean

    @api.model
    def _format_ruc_vat(self, vat):
        """Return a Paraguayan RUC formatted as RUC-DV when possible."""
        if not vat:
            return vat

        vat_clean = vat.strip()
        if "-" in vat_clean:
            ruc_num = vat_clean.split("-", 1)[0]
        else:
            ruc_num = "".join(c for c in vat_clean if c.isdigit())

        if ruc_num and ruc_num.isdigit() and len(ruc_num) >= 6:
            dv = str(RUCValidator._calculate_check_digit(ruc_num))
            return f"{ruc_num}-{dv}"

        return vat_clean

    def _format_vat_py(self, vals):
        """Format vat for RUC type: append DV if missing or incorrect.

        For create: modifies vals in-place.
        For write: returns formatted vat or None.
        """
        ruc_type = self.env.ref("l10n_py_base.it_ruc", raise_if_not_found=False)
        if not ruc_type or not vals.get("vat"):
            return None

        id_type_id = vals.get("l10n_latam_identification_type_id")
        if isinstance(id_type_id, int):
            is_ruc = id_type_id == ruc_type.id
        elif hasattr(id_type_id, "id"):
            is_ruc = id_type_id.id == ruc_type.id
        else:
            is_ruc = False

        if not is_ruc:
            return None

        formatted = self._format_ruc_vat(vals["vat"])
        if formatted != vals["vat"]:
            vals["vat"] = formatted
            return formatted

        return formatted

    # ============== ONCHANGE METHODS ==============

    @api.onchange("l10n_latam_identification_type_id")
    def _onchange_l10n_py_identification_type(self):
        """Auto-set taxpayer type and doc_type based on identification type."""
        ruc_type = self.env.ref("l10n_py_base.it_ruc", raise_if_not_found=False)
        if not self.l10n_latam_identification_type_id:
            return

        if self.l10n_latam_identification_type_id == ruc_type:
            self.l10n_py_taxpayer_type = "1"
            self.l10n_py_doc_type = False
            self.l10n_py_doc_number = False
        else:
            type_map = self._get_identification_doc_type_map()
            doc_type = type_map.get(self.l10n_latam_identification_type_id.id)
            if doc_type:
                self.l10n_py_taxpayer_type = "2"
                self.l10n_py_doc_type = doc_type
                if self.vat:
                    self.l10n_py_doc_number = self.vat

    @api.onchange("vat")
    def _onchange_vat_l10n_py(self):
        """When vat changes for RUC type, auto-format with DV."""
        ruc_type = self.env.ref("l10n_py_base.it_ruc", raise_if_not_found=False)
        if ruc_type and self.l10n_latam_identification_type_id == ruc_type and self.vat:
            vat = self.vat.strip()
            if "-" in vat:
                ruc_num = vat.split("-", 1)[0]
            else:
                ruc_num = "".join(c for c in vat if c.isdigit())

            if ruc_num and ruc_num.isdigit() and len(ruc_num) >= 6:
                dv = str(RUCValidator._calculate_check_digit(ruc_num))
                self.vat = f"{ruc_num}-{dv}"
        elif self.vat and self.l10n_latam_identification_type_id:
            # Sync doc_number for non-RUC types
            type_map = self._get_identification_doc_type_map()
            if self.l10n_latam_identification_type_id.id in type_map:
                self.l10n_py_doc_number = self.vat

    @api.onchange("l10n_py_neighborhood_id")
    def _onchange_l10n_py_neighborhood_id(self):
        """Update city and zip code when neighborhood changes"""
        if self.l10n_py_neighborhood_id:
            if not self.city_id:
                self.city_id = self.l10n_py_neighborhood_id.city_id
            if not self.zip and self.l10n_py_neighborhood_id.zipcode:
                self.zip = self.l10n_py_neighborhood_id.zipcode

    @api.onchange("city_id")
    def _onchange_city_id(self):
        """Clear neighborhood if city changes and doesn't match"""
        if (
            self.l10n_py_neighborhood_id
            and self.city_id
            and self.l10n_py_neighborhood_id.city_id != self.city_id
        ):
            self.l10n_py_neighborhood_id = False

    @api.onchange("state_id")
    def _onchange_state_id_l10n_py(self):
        """Clear city and neighborhood if state changes and doesn't match"""
        if self.state_id:
            if self.city_id and self.city_id.state_id != self.state_id:
                self.city_id = False
                self.l10n_py_neighborhood_id = False
            elif self.l10n_py_neighborhood_id:
                nb_state = self.l10n_py_neighborhood_id.city_id.state_id
                if nb_state != self.state_id:
                    self.l10n_py_neighborhood_id = False

    @api.onchange("zip")
    def _onchange_zip_l10n_py(self):
        """Search neighborhood by zip code and auto-fill location"""
        if self.zip and self.country_id and self.country_id.code == "PY":
            zipcode = self.zip.strip()
            # Search exact match first, then by padded zipcode
            neighborhood = self.env["l10n_py.neighborhood"].search(
                [("zipcode", "=", zipcode)], limit=1
            )
            if not neighborhood:
                # Try with padding (e.g., "1001" -> "001001")
                zipcode_padded = zipcode.zfill(6)
                neighborhood = self.env["l10n_py.neighborhood"].search(
                    [("zipcode", "=", zipcode_padded)], limit=1
                )
            if not neighborhood:
                # Try prefix search (e.g., "1001" matches "001001")
                neighborhood = self.env["l10n_py.neighborhood"].search(
                    [("zipcode", "=like", f"%{zipcode}")], limit=1
                )
            if neighborhood:
                self.l10n_py_neighborhood_id = neighborhood
                self.city_id = neighborhood.city_id
                self.state_id = neighborhood.city_id.state_id

    # ============== VAT VALIDATION ==============

    def check_vat_py(self, vat):
        """Validate Paraguay RUC/VAT number.

        Only RUC numbers reach this hook (l10n_latam_base filters cedula,
        passport, and residence card before calling base_vat).

        Delegates to python-stdnum via RUCValidator for correct modulo 11
        check digit validation.
        """
        if not vat:
            return False
        is_valid, _error = RUCValidator.validate(vat)
        return is_valid

    # ============== HELPER METHODS ==============

    def _get_identification_doc_type_map(self):
        """Map identification type IDs to l10n_py_doc_type selection values."""
        result = {}
        for xml_id, doc_type in [
            ("l10n_py_base.it_ci", "1"),
            ("l10n_py_base.it_pasaporte", "2"),
            ("l10n_py_base.it_carnet_residencia", "3"),
        ]:
            rec = self.env.ref(xml_id, raise_if_not_found=False)
            if rec:
                result[rec.id] = doc_type
        return result

    @api.model
    def _formatting_address_fields(self):
        """Returns the list of address fields usable to format addresses."""
        return super()._formatting_address_fields() + ["l10n_py_neighborhood_name"]
