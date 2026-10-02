# Usage

## Sending Documents via FacturaSend

### Automatic Sending

If auto-send is configured:
1. Create invoice
2. Confirm invoice
3. System automatically sends to FacturaSend
4. FacturaSend processes and sends to SET
5. Status updates automatically (via webhook or polling)

### Manual Sending

1. Confirm invoice
2. Click **Send EDI** button
3. System sends to FacturaSend
4. Wait for processing
5. Check status

## Document Flow

```
Odoo Invoice → FacturaSend API → FacturaSend Platform → SET SIFEN → Approval
```

Typical timeline:
- Odoo to FacturaSend: Immediate
- FacturaSend processing: 1-5 seconds
- SET processing: 5-30 seconds
- Total: Usually under 1 minute

With webhooks enabled:
- Status updates arrive in real-time
- No waiting for polling

## Monitoring FacturaSend Operations

### Check EDI Status

1. Open invoice
2. View **EDI Status** field
3. Possible statuses:
   - **To Send**: Ready to send
   - **Sending**: Being sent to FacturaSend
   - **Sent**: Received by FacturaSend
   - **Processing**: FacturaSend processing
   - **Approved**: Approved by SET
   - **Rejected**: Rejected by SET
   - **Error**: Error occurred

### View FacturaSend Logs

1. Go to **Facturación Electrónica > EDI Logs**
2. Filter by document
3. View:
   - Request sent to FacturaSend
   - Response from FacturaSend
   - SET response (via FacturaSend)
   - Webhook notifications
   - Error messages if any

## Status Synchronization

### Automatic Updates (Webhook)

If webhooks are configured:
- FacturaSend pushes updates to Odoo
- Instant status changes
- No polling needed
- Most efficient method

### Automatic Updates (Polling)

If webhooks not available:
- Scheduled job runs every X minutes
- Checks pending documents
- Queries FacturaSend for status
- Updates Odoo records
- Downloads PDF/XML when approved

### Manual Update

To manually check status:
1. Open invoice
2. Click **Update EDI Status**
3. System queries FacturaSend immediately
4. Status updates

## Downloading Documents

### Download from FacturaSend

Once approved by SET:

**Download PDF**:
1. Click **Download EDI PDF**
2. System fetches from FacturaSend
3. PDF includes official KUDE and QR code

**Download XML**:
1. Click **Download EDI XML**
2. System fetches from FacturaSend
3. Official SET-signed XML

### Automatic Download

Configure automatic download:
1. Enable in company settings
2. PDF/XML download automatically on approval
3. Stored in Odoo attachments
4. Available for customer portal

## Cancelling Documents

### Via FacturaSend

1. Open approved invoice
2. Click **Cancel EDI**
3. Select cancellation reason
4. Click **Confirm**
5. System sends cancellation to FacturaSend
6. FacturaSend forwards to SET
7. Status updates to "Cancelled"

### Cancellation Limitations

- Only approved documents can be cancelled
- Must be within SET's allowed timeframe
- Valid reason required
- Cannot undo cancellation

## Error Handling

### Common FacturaSend Errors

**"Document validation failed"**
- Issue: Document data doesn't meet SET requirements
- Solution: Check FacturaSend error details, fix data, resend

**"RUC not authorized"**
- Issue: Company RUC not registered with FacturaSend
- Solution: Contact FacturaSend to activate RUC

**"Timbrado invalid"**
- Issue: Timbrado not recognized by SET
- Solution: Verify timbrado number, update if needed

**"Tenant limit exceeded"**
- Issue: Exceeded tenant quota
- Solution: Upgrade plan or contact FacturaSend

**"Rate limit exceeded"**
- Issue: Too many requests to FacturaSend API
- Solution: Wait and retry, contact FacturaSend for limit increase

### Automatic Retry

For transient errors:
- System automatically retries
- Exponential backoff between retries
- Maximum retry attempts configured
- Manual retry always available

### Manual Retry

For failed documents:
1. Fix underlying issue
2. Click **Retry EDI**
3. System resends to FacturaSend

## FacturaSend Dashboard Integration

### Accessing FacturaSend Portal

1. Login to FacturaSend web portal
2. Select your tenant
3. View all documents from your company
4. See real-time status
5. Download documents directly
6. View statistics and reports
7. Configure webhooks

### Cross-Reference

Documents in Odoo link to FacturaSend:
- FacturaSend Document ID stored in Odoo
- Use ID to find document in FacturaSend portal
- Useful for troubleshooting

## Webhook Management

### Verifying Webhook Status

1. Go to **Facturación Electrónica > Configuration > FacturaSend Connector**
2. Check **Webhook Status**
3. View last webhook received
4. Test webhook delivery

### Webhook Issues

If webhooks stop working:
1. Check webhook URL is accessible
2. Verify webhook secret matches
3. Check FacturaSend webhook logs
4. Re-save webhook configuration
5. Test webhook delivery

## Best Practices

### Before Sending

1. **Verify Data**: Check all fiscal data is complete
2. **Test First**: Always test in test environment
3. **Check Timbrado**: Ensure timbrado is valid
4. **Verify Customer**: Customer RUC must be correct

### During Operation

1. **Enable Webhooks**: For real-time updates
2. **Monitor Logs**: Regularly check EDI logs
3. **Handle Errors**: Address errors promptly
4. **Backup Documents**: Download and store PDF/XML

### Performance Optimization

1. **Use Webhooks**: Reduces API calls and faster updates
2. **Batch Operations**: Send multiple documents together
3. **Off-Peak**: Send during off-peak hours for better performance
4. **Status Updates**: Let webhooks handle updates, avoid frequent manual checks

## Bulk Operations

### Sending Multiple Invoices

1. Go to invoice list
2. Select multiple invoices
3. Action > **Send EDI**
4. System sends all via FacturaSend
5. Monitor progress in logs
6. Webhook updates status for each

### Updating Multiple Statuses

1. Select invoices
2. Action > **Update EDI Status**
3. System queries FacturaSend for all

**Note**: With webhooks, manual updates rarely needed

## Reporting

### FacturaSend Reports

Available in FacturaSend portal:
- Documents sent per period
- Success/failure rates
- Processing times
- Error summaries
- Tenant usage statistics
- Billing information

### Odoo Reports

Filter invoices by:
- EDI Status
- FacturaSend responses
- Date ranges
- Errors
- Tenant (for multi-tenant setups)

## Multi-Tenant Operations

### For Service Providers

If managing multiple tenants:
1. Switch company in Odoo
2. System automatically uses correct tenant
3. Each tenant's data isolated
4. Reports per tenant available

### Tenant Analytics

View per tenant:
- Document volume
- Success rates
- Error patterns
- Cost allocation

## Troubleshooting

### Document Not Appearing in FacturaSend

1. Check EDI logs for send confirmation
2. Verify FacturaSend credentials
3. Check Tenant ID is correct
4. Verify internet connection
5. Review error messages
6. Try manual retry

### Status Not Updating

**With webhooks**:
1. Check webhook is configured
2. Verify webhook URL is accessible
3. Test webhook delivery
4. Check FacturaSend webhook logs

**Without webhooks**:
1. Check scheduled job is running
2. Manually trigger status update
3. Verify FacturaSend connection
4. Check FacturaSend portal directly

### PDF/XML Download Fails

1. Verify document is approved
2. Check FacturaSend has document
3. Retry download
4. Download from FacturaSend portal as fallback

### Webhook Validation Failed

1. Check webhook secret matches
2. Verify request signature
3. Review webhook logs
4. Re-configure webhook in FacturaSend

## Support and Resources

### FacturaSend Support

- Portal: support.facturasend.com.py
- Email: soporte@facturasend.com.py
- Phone: [FacturaSend support number]
- Hours: [Support hours]
- Documentation: docs.facturasend.com.py

### Documentation

- FacturaSend API docs: docs.facturasend.com.py/api
- Module documentation: This guide
- SET documentation: www.set.gov.py

### Community

- Odoo community forums
- GitHub issues
- User groups
- FacturaSend user community

