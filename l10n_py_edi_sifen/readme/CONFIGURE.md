1. Go to **Settings > Companies** and upload the PKCS12 (.pfx) certificate
   in the "Certificado Digital (SIFEN)" section.

2. Go to **Accounting > Facturación Electrónica > Conectores** and create a
   new connector:
   - Provider: **SIFEN Directo**
   - Environment: **Pruebas** or **Producción**
   - Company: select the company

3. Click **Probar Conexión** to verify the mTLS connection with SIFEN.

4. Once uploaded, the certificate's expiration date is read automatically
   and shown next to a status badge (**Válido** / **Por vencer** /
   **Vencido**, the last two triggering at 30 days before expiry). A
   daily scheduled action keeps this status current even if nobody opens
   the company record.
