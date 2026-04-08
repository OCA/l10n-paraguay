# Installation

## Prerequisites

### Required Modules
- `l10n_py_edi_base`: Electronic invoicing base module (must be installed first)
- All dependencies from base module

### FactPy Account
- Active FactPy account
- API credentials (Key and Secret)
- Test and/or production access

### Network Requirements
- Outbound HTTPS access (port 443)
- Access to FactPy API endpoints:
  - Test: `https://api.test.factpy.com`
  - Production: `https://api.factpy.com`

## Installation Steps

### Step 1: Install Base Module

If not already installed:
1. Install `l10n_py_edi_base`
2. Configure base EDI settings
3. Verify base module works

### Step 2: Install FactPy Connector

1. Go to **Apps**
2. Click **Update Apps List**
3. Search for "Paraguay - FactPy EDI Connector"
4. Click **Install**

### Step 3: Verify Installation

Check that:
- FactPy connector menu appears
- No installation errors in logs
- Module status is "Installed"

## Post-Installation Configuration

### Step 1: Create FactPy Account

If you don't have a FactPy account:
1. Visit FactPy website
2. Sign up for account
3. Complete verification
4. Request API credentials

### Step 2: Obtain API Credentials

From FactPy:
1. Login to FactPy portal
2. Go to API settings
3. Generate or retrieve:
   - API Key
   - API Secret
4. Save credentials securely

### Step 3: Configure Connector

1. Go to **Facturación Electrónica > Configuration > FactPy Connector**
2. Create connector record
3. Enter API credentials
4. Set environment (Test/Production)
5. Click **Test Connection**
6. Save if successful

### Step 4: Set as Active Provider

1. Go to **Settings > Companies**
2. Edit company
3. Set **EDI Provider** = "FactPy"
4. Save

## Testing Installation

### Test 1: Connection Test

1. In FactPy connector
2. Click **Test Connection**
3. Expected result: "Connection successful"

### Test 2: Send Test Invoice

1. Create test invoice
2. Confirm it
3. Click **Send EDI**
4. Check logs for FactPy response
5. Verify in FactPy portal

### Test 3: Status Update

1. Wait a few seconds
2. Click **Update EDI Status**
3. Verify status changes to "Approved" (in test)

### Test 4: Download Documents

1. Click **Download EDI PDF**
2. Verify PDF downloads
3. Click **Download EDI XML**
4. Verify XML downloads

## Production Setup

### Before Going Live

1. ✅ Complete all testing
2. ✅ Verify all data is accurate
3. ✅ Train users
4. ✅ Backup database
5. ✅ Get production credentials from FactPy
6. ✅ Verify FactPy has activated your production RUC

### Switch to Production

1. Update connector configuration:
   - Change environment to "Production"
   - Enter production API credentials
   - Update base URL (automatic)
2. Test connection
3. Send first production invoice
4. Monitor closely

## Security Configuration

### User Permissions

Configure who can access FactPy settings:
1. Go to **Settings > Users & Companies > Users**
2. Edit user
3. Assign groups:
   - **Electronic Invoicing / User**: Can send documents
   - **Electronic Invoicing / Manager**: Can configure FactPy

### Credential Security

Best practices:
- Limit who can view connector settings
- Don't share API credentials
- Use strong passwords for Odoo users
- Regular credential rotation
- Audit access logs

## Firewall Configuration

### Required Outbound Access

Allow outbound HTTPS to:
- `api.factpy.com` (production)
- `api.test.factpy.com` (test)
- Port 443 (HTTPS)

### Testing Connectivity

From server command line:
```bash
curl https://api.test.factpy.com/health
```

Expected: Status 200 or similar health check response

## Multi-Server Setup

### Load Balanced Environment

If using multiple Odoo servers:
1. Install module on all servers
2. Configure connector on each
3. Use same FactPy credentials
4. Ensure scheduled jobs run on only one server

### Database Replication

For replicated databases:
- Master: Full configuration
- Replicas: Read-only, no sending

## Scheduled Jobs Configuration

### Enable Automatic Jobs

1. Go to **Settings > Technical > Automation > Scheduled Actions**
2. Find FactPy-related jobs:
   - "FactPy: Check Document Status"
   - "FactPy: Retry Failed Documents"
3. Enable and configure frequency

### Recommended Frequency

- Status check: Every 5-10 minutes
- Retry failed: Every 30 minutes

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
ping api.factpy.com
curl https://api.factpy.com
```

**Check credentials**:
1. Verify API Key is correct
2. Verify API Secret is correct
3. No extra spaces
4. Correct environment

**Firewall issues**:
1. Check outbound HTTPS allowed
2. Verify no proxy blocking
3. Check SSL certificate validation

### FactPy Menu Not Appearing

**Refresh browser**:
1. Hard refresh (Ctrl+Shift+R)
2. Clear cache
3. Logout and login

**Check permissions**:
1. User must have EDI permissions
2. Module must be fully installed
3. Restart Odoo if needed

## Upgrade Instructions

### Upgrading from Previous Version

1. Backup database
2. Update module files
3. Go to **Apps**
4. Find module
5. Click **Upgrade**
6. Test functionality

### Breaking Changes

Check changelog for:
- API changes
- Configuration migrations
- Data migrations

## Uninstallation

**Warning**: Uninstalling will:
- Disable FactPy integration
- Remove connector configurations
- Keep historical data but make it inaccessible

To uninstall:
1. Switch to different EDI provider first
2. Or disable EDI entirely
3. Then uninstall module

## Support

### Installation Issues

Contact:
- FactPy support: support@factpy.com
- Odoo community forums
- Module maintainers

### Documentation

- This guide
- FactPy API documentation
- Base module documentation

## Checklist

Installation complete when:
- [ ] Module installed successfully
- [ ] FactPy connector configured
- [ ] Connection test successful
- [ ] Test invoice sent and approved
- [ ] PDF/XML download working
- [ ] Scheduled jobs enabled
- [ ] Users trained
- [ ] Production credentials ready (for go-live)

