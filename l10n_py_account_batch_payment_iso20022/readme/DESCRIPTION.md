Generic ISO 20022 (pain.001.001.09) exporter plugged into the SIPAP
batch payment framework provided by ``l10n_py_account_batch_payment``.

**This exporter implements the generic ISO 20022 pain.001.001.09
schema. Acceptance of this exact file by any specific Paraguayan bank's
home banking portal is NOT confirmed and must be verified with that bank
before use in production.** SIPAP standardizes bank-to-BCP communication
in ISO 20022, but a company's own bank often expects its own proprietary
layout on its corporate home banking channel — this module does not
implement any such proprietary layout.

The file classifies each transaction as SPI (Sistema de Pagos
Inmediatos) or LBTR (Liquidación Bruta en Tiempo Real) based on
``res.company.l10n_py_sipap_spi_lbtr_threshold``. This threshold has **no
default value** — the real cutoff must be confirmed with the Banco
Central del Paraguay; generation fails with an explicit error while it
is unset, rather than silently assuming a value.
