1. On **Contabilidad > Configuración > Empresas**, set the **Umbral
   SPI/LBTR SIPAP** field (mandatory before generating a file with this
   exporter; there is no default value).
2. On the destination banks (``res.bank``) of your beneficiaries, set
   **Formato de Exportación SIPAP** to ``iso20022`` to route batch files
   through this exporter (see ``l10n_py_account_batch_payment``'s
   README for the rest of the framework configuration).
