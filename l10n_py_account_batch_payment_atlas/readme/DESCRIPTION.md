The first real (non-file) SIPAP batch payment exporter for Banco Atlas:
dispatches ``account.payment.order`` batches directly to the bank's
``Pago a Proveedores`` REST API instead of generating a file for manual
upload, with automatic SPI/LBTR routing based on the official BCP limit
(Gs. 5.000.000 per SPI transfer, PYG only -- Resolución 1/2023 §50.01).

No webhook exists on this API: confirmation of a pending payment relies on
a scheduled polling job.
