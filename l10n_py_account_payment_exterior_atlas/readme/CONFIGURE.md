On the company's own bank account (``res.partner.bank``), enable "Banco
Atlas" and fill in its credentials (see
``l10n_py_account_payment_atlas``'s CONFIGURE.md).

``codigo_motivo`` (Código de Motivo) must be one of the values from the
bank's own catalog, fetched via ``GET
/exterior/motivos_transferencia`` -- these values are NOT hardcoded
anywhere in this module, and this module does not implement fetching that
catalog automatically. Consult the bank's documentation or a previous
successful call for the valid current values before filling this field by
hand.

Similarly, ``beneficiario_pais`` (Código País Beneficiario) and
``beneficiario_ciudad`` (Código Ciudad Beneficiario) are plain numeric
codes from the bank's own catalogs (``GET /exterior/paises``, ``GET
/exterior/ciudades/{pais}``), not a friendly dropdown -- this module does
not implement fetching those catalogs either. The user must fill in the
correct bank-side numeric code directly.
