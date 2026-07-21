# Installation

## Prerequisites

### Required Modules
- `l10n_py_edi_base`: Electronic invoicing base module (must be installed first)
- All dependencies from base module

### FacturaSend Account
- Active FacturaSend account
- API credentials (API Key and Tenant ID)
- Test and/or production access

### Network Requirements
- Outbound HTTPS access (port 443)
- Access to FacturaSend API endpoints:
  - Test: `https://api.test.facturasend.com.py`
  - Production: `https://api.facturasend.com.py`
- Inbound HTTPS access (for webhooks - optional but recommended)

## Installation Steps

### Step 1: Install Base Module

If not already installed:
1. Install `l10n_py_edi_base`
2. Configure base EDI settings
3. Verify base module works

### Step 2: Install FacturaSend Connector

1. Go to **Apps**
2. Click **Update Apps List**
3. Search for "Paraguay - FacturaSend EDI Connector"
4. Click **Install**

### Step 3: Verify Installation

Check that:
- FacturaSend connector menu appears
- No installation errors in logs
- Module status is "Installed"

## Post-Installation Configuration

### Step 1: Create FacturaSend Account

If you don't have a FacturaSend account:
1. Visit FacturaSend website (facturasend.com.py)
2. Sign up for account
3. Complete verification
4. Request API credentials

### Step 2: Obtain API Credentials

From FacturaSend:
1. Login to FacturaSend portal
2. Go to API settings
3. Generate or retrieve:
   - API Key
   - Tenant ID
4. Save credentials securely

### Step 3: Configure Connector

1. Go to **Facturación Electrónica > Configuration > FacturaSend Connector**
2. Create connector record
3. Enter API credentials
4. Set environment (Test/Production)
5. Click **Test Connection**
6. Save if successful

### Step 4: Set as Active Provider

1. Go to **Settings > Companies**
2. Edit company
3. Set **EDI Provider** = "FacturaSend"
4. Save

### Step 5: Configure Webhooks (Recommended)

1. In Odoo connector, copy webhook URL
2. Login to FacturaSend portal
3. Go to Webhook configuration
4. Add webhook URL
5. Generate webhook secret
6. Copy secret to Odoo connector
7. Test webhook delivery

## Testing Installation

### Test 1: Connection Test

1. In FacturaSend connector
2. Click **Test Connection**
3. Expected result: "Connection successful"

### Test 2: Send Test Invoice

1. Create test invoice
2. Confirm it
3. Click **Send EDI**
4. Check logs for FacturaSend response
5. Verify in FacturaSend portal

### Test 3: Status Update

#### With Webhooks
1. Status should update automatically
2. Check webhook delivery in FacturaSend portal
3. Verify status in Odoo updates immediately

#### Without Webhooks
1. Wait for scheduled job or click **Update EDI Status**
2. Verify status changes to "Approved" (in test)

### Test 4: Download Documents

1. Click **Download EDI PDF**
2. Verify PDF downloads
3. Click **Download EDI XML**
4. Verify XML downloads

### Test 5: Webhook Test (if configured)

1. In FacturaSend portal, trigger test webhook
2. Check Odoo logs for webhook receipt
3. Verify webhook validation passes

## Production Setup

### Before Going Live

1. ✅ Complete all testing
2. ✅ Verify all data is accurate
3. ✅ Train users
4. ✅ Backup database
5. ✅ Get production credentials from FacturaSend
6. ✅ Verify FacturaSend has activated your production RUC and Tenant
7. ✅ Configure production webhooks
8. ✅ Test webhook delivery in production

### Switch to Production

1. Update connector configuration:
   - Change environment to "Production"
   - Enter production API Key and Tenant ID
   - Update base URL (automatic)
   - Update webhook URL if different
2. Test connection
3. Configure production webhooks in FacturaSend portal
4. Test webhook delivery
5. Send first production invoice
6. Monitor closely

## Security Configuration

### User Permissions

Configure who can access FacturaSend settings:
1. Go to **Settings > Users & Companies > Users**
2. Edit user
3. Assign groups:
   - **Electronic Invoicing / User**: Can send documents
   - **Electronic Invoicing / Manager**: Can configure FacturaSend

### Credential Security

Best practices:
- Limit who can view connector settings
- Don't share API credentials or Tenant IDs
- Use strong passwords for Odoo users
- Regular credential rotation
- Audit access logs

### Webhook Security

For webhook security:
- Use HTTPS for webhook endpoint
- Validate webhook secret
- Verify request signatures
- Log all webhook calls
- Monitor for unusual activity

## Firewall Configuration

### Required Outbound Access

Allow outbound HTTPS to:
- `api.facturasend.com.py` (production)
- `api.test.facturasend.com.py` (test)
- Port 443 (HTTPS)

### Required Inbound Access (for webhooks)

Allow inbound HTTPS from FacturaSend:
- Port 443 (HTTPS)
- To webhook endpoint: `/l10n_py_edi/webhook/facturasend`
- From FacturaSend IP ranges (contact FacturaSend for list)

### Testing Connectivity

**Outbound**:
```bash
curl https://api.test.facturasend.com.py/health
```

**Inbound** (webhooks):
1. Use FacturaSend portal test webhook function
2. Check Odoo receives it
3. Verify in logs

## Multi-Server Setup

### Load Balanced Environment

If using multiple Odoo servers:
1. Install module on all servers
2. Configure connector on each
3. Use same FacturaSend credentials
4. Ensure scheduled jobs run on only one server
5. Configure webhooks to reach load balancer
6. Ensure sticky sessions for webhook handling

### Database Replication

For replicated databases:
- Master: Full configuration, handles webhooks
- Replicas: Read-only, no sending, no webhook handling

## Scheduled Jobs Configuration

### Enable Automatic Jobs

1. Go to **Settings > Technical > Automation > Scheduled Actions**
2. Find FacturaSend-related jobs:
   - "FacturaSend: Check Document Status"
   - "FacturaSend: Retry Failed Documents"
3. Enable and configure frequency

### Recommended Frequency

**With webhooks**:
- Status check: Every 30-60 minutes (backup)
- Retry failed: Every 30 minutes

**Without webhooks**:
- Status check: Every 5-10 minutes
- Retry failed: Every 30 minutes

## Multi-Tenant Setup

### Service Provider Configuration

If managing multiple clients:
1. Create separate Odoo company for each client
2. Create connector for each company
3. Use same API Key, different Tenant IDs
4. Each tenant isolated in FacturaSend
5. Separate billing per tenant

### Switching Between Tenants

Users can:
1. Switch Odoo company
2. System automatically uses correct tenant
3. No manual tenant selection needed

## Troubleshooting Installation

### Module Won't Install

**Check dependencies**:
```bash
# Verify l10n_py_edi_base is installed
```

**Check logs**:
1. Odoo server logs
2. Look for Python errors
3. Check database connection

### Connection Test Fails

**Verify network**:
```bash
ping api.facturasend.com.py
curl https://api.facturasend.com.py
```

**Check credentials**:
1. Verify API Key is correct
2. Verify Tenant ID is correct
3. No extra spaces
4. Correct environment

**Firewall issues**:
1. Check outbound HTTPS allowed
2. Verify no proxy blocking
3. Check SSL certificate validation

### FacturaSend Menu Not Appearing

**Refresh browser**:
1. Hard refresh (Ctrl+Shift+R)
2. Clear cache
3. Logout and login

**Check permissions**:
1. User must have EDI permissions
2. Module must be fully installed
3. Restart Odoo if needed

### Webhooks Not Working

**Check accessibility**:
```bash
# From external network
curl https://your-odoo.com/l10n_py_edi/webhook/facturasend
```

**Verify configuration**:
1. Webhook URL is correct
2. Webhook secret matches
3. Firewall allows inbound HTTPS
4. SSL certificate is valid

**Test from FacturaSend**:
1. Use portal test function
2. Check Odoo logs
3. Verify response code

## Upgrade Instructions

### Upgrading from Previous Version

1. Backup database
2. Update module files
3. Go to **Apps**
4. Find module
5. Click **Upgrade**
6. Re-test webhook configuration
7. Test functionality

### Breaking Changes

Check changelog for:
- API changes
- Webhook format changes
- Configuration migrations
- Data migrations

## Uninstallation

**Warning**: Uninstalling will:
- Disable FacturaSend integration
- Remove connector configurations
- Remove webhook configurations
- Keep historical data but make it inaccessible

To uninstall:
1. Switch to different EDI provider first
2. Or disable EDI entirely
3. Remove webhook in FacturaSend portal
4. Then uninstall module

## Support

### Installation Issues

Contact:
- FacturaSend support: soporte@facturasend.com.py
- Odoo community forums
- Module maintainers

### Documentation

- This guide
- FacturaSend API documentation: docs.facturasend.com.py
- Base module documentation
- Webhook documentation

## Checklist

Installation complete when:
- [ ] Module installed successfully
- [ ] FacturaSend connector configured
- [ ] Connection test successful
- [ ] Webhooks configured and tested
- [ ] Test invoice sent and approved
- [ ] Status updated via webhook or polling
- [ ] PDF/XML download working
- [ ] Scheduled jobs enabled (if not using webhooks)
- [ ] Users trained
- [ ] Production credentials ready (for go-live)
- [ ] Production webhooks configured
- [ ] Security reviewed

