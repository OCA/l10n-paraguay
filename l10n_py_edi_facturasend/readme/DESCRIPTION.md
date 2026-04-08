# Paraguay - FacturaSend EDI Connector

This module provides integration with FacturaSend service for electronic invoicing in Paraguay, enabling seamless communication between Odoo and SET (Subsecretaría de Estado de Tributación) through the FacturaSend platform.

## Features

### FacturaSend API Integration
- **Document Sending**: Automatic transmission of invoices to FacturaSend
- **Status Checking**: Real-time status updates from FacturaSend
- **Document Cancellation**: Cancel documents through FacturaSend
- **PDF Download**: Retrieve official PDF from FacturaSend
- **XML Download**: Get SET-compliant XML files

### Automatic Operations
- **Error Handling**: Intelligent retry mechanism for failed transmissions
- **Logging**: Complete audit trail of all FacturaSend operations
- **Status Sync**: Automatic synchronization with FacturaSend status
- **Batch Processing**: Efficient handling of multiple documents

### Configuration Management
- **Credential Storage**: Secure storage of API credentials
- **Environment Support**: Separate test and production environments
- **Multi-company**: Support for multiple companies with different credentials
- **Tenant Management**: Multi-tenant support for service providers

## FacturaSend Service

FacturaSend is a certified EDI provider for Paraguay that:
- Connects directly to SET's SIFEN system
- Validates documents before submission
- Provides reliable document transmission
- Offers cloud-based management
- Maintains compliance with SET regulations

## Dependencies

- `l10n_py_edi_base`: Electronic invoicing base module
- All dependencies from base module

## Related Modules

Alternative EDI connector:
- `l10n_py_edi_factpy`: FactPy connector

