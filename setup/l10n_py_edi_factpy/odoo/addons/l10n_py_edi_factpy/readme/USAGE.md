# Usage

## Sending Documents via FactPy

### Automatic Sending

If auto-send is configured:
1. Create invoice
2. Confirm invoice
3. System automatically sends to FactPy
4. FactPy processes and sends to SET
5. Status updates automatically

### Manual Sending

1. Confirm invoice
2. Click **Send EDI** button
3. System sends to FactPy
4. Wait for processing
5. Check status

## Document Flow

```
Odoo Invoice → FactPy API → FactPy Platform → SET SIFEN → Approval
```

Typical timeline:
- Odoo to FactPy: Immediate
- FactPy processing: 1-5 seconds
- SET processing: 5-30 seconds
- Total: Usually under 1 minute

## Monitoring FactPy Operations

### Check EDI Status

1. Open invoice
2. View **EDI Status** field
3. Possible statuses:
   - **To Send**: Ready to send
   - **Sending**: Being sent to FactPy
   - **Sent**: Received by FactPy
   - **Processing**: FactPy processing
   - **Approved**: Approved by SET
   - **Rejected**: Rejected by SET
   - **Error**: Error occurred

### View FactPy Logs

1. Go to **Facturación Electrónica > EDI Logs**
2. Filter by document
3. View:
   - Request sent to FactPy
   - Response from FactPy
   - SET response (via FactPy)
   - Error messages if any

## Status Synchronization

### Automatic Updates

Scheduled job runs every X minutes:
- Checks pending documents
- Queries FactPy for status
- Updates Odoo records
- Downloads PDF/XML when approved

### Manual Update

To manually check status:
1. Open invoice
2. Click **Update EDI Status**
3. System queries FactPy immediately
4. Status updates

## Downloading Documents

### Download from FactPy

Once approved by SET:

**Download PDF**:
1. Click **Download EDI PDF**
2. System fetches from FactPy
3. PDF includes official KUDE and QR code

**Download XML**:
1. Click **Download EDI XML**
2. System fetches from FactPy
3. Official SET-signed XML

### Automatic Download

Configure automatic download:
1. Enable in company settings
2. PDF/XML download automatically on approval
3. Stored in Odoo attachments

## Cancelling Documents

### Via FactPy

1. Open approved invoice
2. Click **Cancel EDI**
3. Select cancellation reason
4. Click **Confirm**
5. System sends cancellation to FactPy
6. FactPy forwards to SET
7. Status updates to "Cancelled"

### Cancellation Limitations

- Only approved documents can be cancelled
- Must be within SET's allowed timeframe
- Valid reason required
- Cannot undo cancellation

## Error Handling

### Common FactPy Errors

**"Document validation failed"**
- Issue: Document data doesn't meet SET requirements
- Solution: Check FactPy error details, fix data, resend

**"RUC not authorized"**
- Issue: Company RUC not registered with FactPy
- Solution: Contact FactPy to activate RUC

**"Timbrado invalid"**
- Issue: Timbrado not recognized by SET
- Solution: Verify timbrado number, update if needed

**"Rate limit exceeded"**
- Issue: Too many requests to FactPy API
- Solution: Wait and retry, contact FactPy for limit increase

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
3. System resends to FactPy

## FactPy Dashboard Integration

### Accessing FactPy Portal

1. Login to FactPy web portal
2. View all documents from your company
3. See real-time status
4. Download documents directly
5. View statistics and reports

### Cross-Reference

Documents in Odoo link to FactPy:
- FactPy Document ID stored in Odoo
- Use ID to find document in FactPy portal
- Useful for troubleshooting

## Best Practices

### Before Sending

1. **Verify Data**: Check all fiscal data is complete
2. **Test First**: Always test in test environment
3. **Check Timbrado**: Ensure timbrado is valid
4. **Verify Customer**: Customer RUC must be correct

### During Operation

1. **Monitor Logs**: Regularly check EDI logs
2. **Update Status**: Keep status current
3. **Handle Errors**: Address errors promptly
4. **Backup Documents**: Download and store PDF/XML

### Performance Optimization

1. **Batch Operations**: Send multiple documents together
2. **Off-Peak**: Send during off-peak hours for better performance
3. **Status Updates**: Don't update too frequently (respect rate limits)

## Bulk Operations

### Sending Multiple Invoices

1. Go to invoice list
2. Select multiple invoices
3. Action > **Send EDI**
4. System sends all via FactPy
5. Monitor progress in logs

### Updating Multiple Statuses

1. Select invoices
2. Action > **Update EDI Status**
3. System queries FactPy for all

**Note**: Be mindful of rate limits

## Reporting

### FactPy Reports

Available in FactPy portal:
- Documents sent per period
- Success/failure rates
- Processing times
- Error summaries

### Odoo Reports

Filter invoices by:
- EDI Status
- FactPy responses
- Date ranges
- Errors

## Troubleshooting

### Document Not Appearing in FactPy

1. Check EDI logs for send confirmation
2. Verify FactPy credentials
3. Check internet connection
4. Review error messages
5. Try manual retry

### Status Not Updating

1. Check scheduled job is running
2. Manually trigger status update
3. Verify FactPy connection
4. Check FactPy portal directly

### PDF/XML Download Fails

1. Verify document is approved
2. Check FactPy has document
3. Retry download
4. Download from FactPy portal as fallback

## Support and Resources

### FactPy Support

- Portal: support.factpy.com
- Email: support@factpy.com
- Phone: [FactPy support number]
- Hours: [Support hours]

### Documentation

- FactPy API docs: docs.factpy.com
- Module documentation: This guide
- SET documentation: www.set.gov.py

### Community

- Odoo community forums
- GitHub issues
- User groups

