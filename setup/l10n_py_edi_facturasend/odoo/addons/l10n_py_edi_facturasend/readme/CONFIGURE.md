# Configuration

## Prerequisites

Before configuring the module:
1. Create an account with FacturaSend
2. Obtain API credentials (API Key and Tenant ID)
3. Have test and/or production credentials ready

## Initial Configuration

### Step 1: Set EDI Provider

1. Go to **Settings > General Settings > Companies**
2. Edit your company
3. In **Electronic Invoicing** tab:
   - Set **EDI Provider** = "FacturaSend"
   - Set **Environment** (Test or Production)
4. Save

### Step 2: Configure FacturaSend Connector

1. Go to **Facturación Electrónica > Configuration > FacturaSend Connector**
2. Click **Create** or edit existing connector
3. Fill in configuration:

#### Basic Information
- **Name**: "FacturaSend - [Company Name]"
- **Company**: Select your company
- **Environment**: Test or Production

#### API Credentials
- **API Key**: Your FacturaSend API key
- **Tenant ID**: Your FacturaSend tenant identifier
- **Base URL**: Automatically set based on environment
  - Test: `https://api.test.facturasend.com.py`
  - Production: `https://api.facturasend.com.py`

4. Click **Test Connection** to verify credentials
5. Save

## Environment Configuration

### Test Environment

For testing:
1. Set **Environment** = "Test"
2. Use test credentials from FacturaSend
3. Test URL: `https://api.test.facturasend.com.py`
4. Documents will be sent to SET's test environment
5. No legal validity

### Production Environment

For production:
1. Set **Environment** = "Production"
2. Use production credentials from FacturaSend
3. Production URL: `https://api.facturasend.com.py`
4. Documents sent to SET's production system
5. Legally valid documents

**Important**: Test thoroughly in test environment before switching to production!

## Advanced Settings

### Timeout Configuration

Set API timeout (optional):
- **Connection Timeout**: Default 30 seconds
- **Read Timeout**: Default 60 seconds

Adjust if you have connection issues.

### Retry Configuration

Configure automatic retries:
- **Max Retries**: Number of retry attempts (default: 3)
- **Retry Delay**: Seconds between retries (default: 60)

### Webhook Configuration

Enable real-time status updates:
1. **Webhook URL**: Odoo's webhook endpoint
2. **Webhook Secret**: For validating webhook calls
3. Configure in FacturaSend portal

### Logging

Enable detailed logging:
1. **Debug Mode**: Enable for detailed API logs
2. **Log Requests**: Log all API requests
3. **Log Responses**: Log all API responses

**Warning**: Debug mode generates large logs. Use only for troubleshooting.

## Multi-Company Setup

For multiple companies:
1. Create separate connector for each company
2. Each with its own Tenant ID
3. System automatically uses correct connector per company

## Tenant Configuration

FacturaSend uses multi-tenancy:
- Each company has unique Tenant ID
- Tenant ID isolates data
- One API key can manage multiple tenants

### Service Provider Setup

If you're a service provider managing multiple clients:
1. Create connector for each client company
2. Use same API key, different Tenant IDs
3. Each client's data remains isolated

## Credential Security

### Best Practices
- Never share API credentials
- Use different credentials for test/production
- Rotate credentials periodically
- Limit access to connector configuration

### Storing Credentials
- Credentials are encrypted in database
- Only users with "Electronic Invoicing / Manager" can view
- Use Odoo's security groups

## Testing Configuration

### Test Connection

After configuration:
1. Click **Test Connection** button
2. System verifies:
   - API credentials are valid
   - Tenant ID is valid
   - Connection to FacturaSend is successful
   - API version compatibility
3. Success message confirms configuration

### Send Test Document

1. Create a test invoice
2. Confirm it
3. Send to EDI
4. Check **EDI Logs** for FacturaSend API responses
5. Verify document appears in FacturaSend dashboard

## FacturaSend Dashboard

Access FacturaSend web dashboard:
1. Login to FacturaSend portal
2. Select your tenant
3. View all documents sent from Odoo
4. Check status, download documents
5. Configure webhooks
6. View analytics

## Webhook Setup

For real-time updates:

1. In FacturaSend portal:
   - Go to Webhook settings
   - Set webhook URL to: `https://[your-odoo]/l10n_py_edi/webhook/facturasend`
   - Save webhook secret

2. In Odoo connector:
   - Enter webhook secret
   - Enable webhook
   - Test webhook delivery

Benefits:
- Instant status updates
- No polling required
- Reduced API calls

## Troubleshooting Configuration

### "Invalid Credentials" Error

Solutions:
1. Verify API Key is correct
2. Verify Tenant ID is correct
3. Check for extra spaces in credentials
4. Ensure environment matches credentials (test vs production)
5. Verify FacturaSend account is active

### "Tenant Not Found" Error

Solutions:
1. Verify Tenant ID format
2. Check tenant is active in FacturaSend
3. Ensure API key has access to tenant
4. Contact FacturaSend support

### "Connection Timeout" Error

Solutions:
1. Check internet connection
2. Verify firewall allows outbound HTTPS
3. Increase timeout values
4. Check FacturaSend service status

### "API Version Mismatch" Error

Solutions:
1. Update module to latest version
2. Check FacturaSend API version
3. Contact FacturaSend support if persistent

## Support

For configuration issues:
- Check FacturaSend documentation
- Contact FacturaSend support
- Check module documentation
- Review Odoo logs

