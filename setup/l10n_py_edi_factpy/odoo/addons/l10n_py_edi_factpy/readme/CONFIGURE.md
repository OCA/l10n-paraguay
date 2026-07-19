# Configuration

## Prerequisites

Before configuring the module:
1. Create an account with FactPy
2. Obtain API credentials (API Key and Secret)
3. Have test and/or production credentials ready

## Initial Configuration

### Step 1: Set EDI Provider

1. Go to **Settings > General Settings > Companies**
2. Edit your company
3. In **Electronic Invoicing** tab:
   - Set **EDI Provider** = "FactPy"
   - Set **Environment** (Test or Production)
4. Save

### Step 2: Configure FactPy Connector

1. Go to **Facturación Electrónica > Configuration > FactPy Connector**
2. Click **Create** or edit existing connector
3. Fill in configuration:

#### Basic Information
- **Name**: "FactPy - [Company Name]"
- **Company**: Select your company
- **Environment**: Test or Production

#### API Credentials
- **API Key**: Your FactPy API key
- **API Secret**: Your FactPy API secret
- **Base URL**: Automatically set based on environment
  - Test: `https://api.test.factpy.com`
  - Production: `https://api.factpy.com`

4. Click **Test Connection** to verify credentials
5. Save

## Environment Configuration

### Test Environment

For testing:
1. Set **Environment** = "Test"
2. Use test credentials from FactPy
3. Test URL: `https://api.test.factpy.com`
4. Documents will be sent to SET's test environment
5. No legal validity

### Production Environment

For production:
1. Set **Environment** = "Production"
2. Use production credentials from FactPy
3. Production URL: `https://api.factpy.com`
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

### Logging

Enable detailed logging:
1. **Debug Mode**: Enable for detailed API logs
2. **Log Requests**: Log all API requests
3. **Log Responses**: Log all API responses

**Warning**: Debug mode generates large logs. Use only for troubleshooting.

## Multi-Company Setup

For multiple companies:
1. Create separate connector for each company
2. Each with its own credentials
3. System automatically uses correct connector per company

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
   - Connection to FactPy is successful
   - API version compatibility
3. Success message confirms configuration

### Send Test Document

1. Create a test invoice
2. Confirm it
3. Send to EDI
4. Check **EDI Logs** for FactPy API responses
5. Verify document appears in FactPy dashboard

## FactPy Dashboard

Access FactPy web dashboard:
1. Login to FactPy portal
2. View all documents sent from Odoo
3. Check status, download documents
4. Useful for troubleshooting

## Troubleshooting Configuration

### "Invalid Credentials" Error

Solutions:
1. Verify API Key and Secret are correct
2. Check for extra spaces in credentials
3. Ensure environment matches credentials (test vs production)
4. Verify FactPy account is active

### "Connection Timeout" Error

Solutions:
1. Check internet connection
2. Verify firewall allows outbound HTTPS
3. Increase timeout values
4. Check FactPy service status

### "API Version Mismatch" Error

Solutions:
1. Update module to latest version
2. Check FactPy API version
3. Contact FactPy support if persistent

## Support

For configuration issues:
- Check FactPy documentation
- Contact FactPy support
- Check module documentation
- Review Odoo logs

