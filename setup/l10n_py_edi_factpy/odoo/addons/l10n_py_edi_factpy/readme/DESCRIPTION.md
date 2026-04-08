# Paraguay - FactPy EDI Connector

This module provides integration with FactPy service for electronic invoicing in Paraguay, enabling seamless communication between Odoo and SET (Subsecretaría de Estado de Tributación) through the FactPy platform.

## Features

### FactPy API Integration
- **Document Sending**: Automatic transmission of invoices to FactPy
- **Status Checking**: Real-time status updates from FactPy
- **Document Cancellation**: Cancel documents through FactPy
- **PDF Download**: Retrieve official PDF from FactPy
- **XML Download**: Get SET-compliant XML files

### Automatic Operations
- **Error Handling**: Intelligent retry mechanism for failed transmissions
- **Logging**: Complete audit trail of all FactPy operations
- **Status Sync**: Automatic synchronization with FactPy status
- **Batch Processing**: Efficient handling of multiple documents

### Configuration Management
- **Credential Storage**: Secure storage of API credentials
- **Environment Support**: Separate test and production environments
- **Multi-company**: Support for multiple companies with different credentials

## FactPy Service

FactPy is a certified EDI provider for Paraguay that:
- Connects directly to SET's SIFEN system
- Validates documents before submission
- Provides reliable document transmission
- Offers technical support
- Maintains compliance with SET regulations

## Dependencies

- `l10n_py_edi_base`: Electronic invoicing base module
- All dependencies from base module

## Related Modules

Alternative EDI connector:
- `l10n_py_edi_facturasend`: FacturaSend connector

