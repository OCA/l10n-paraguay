1. On **Contacts > Configuration > Banks** (``res.bank``), set the
   **Código de Banco SIPAP** and, once an exporter module is installed,
   the **Formato de Exportación SIPAP** (e.g. ``iso20022``) for each bank
   that will receive a batch file.
2. On a bank account (``res.partner.bank``), optionally set the **Tipo
   de Alias CAS** and **Alias CAS** (phone/email/RUC/CI) if the
   beneficiary is to be identified by an alias instead of a full account
   number.
3. Create an **Account Payment Method Line** on the relevant bank
   journal using the **SIPAP Batch File** payment method (Accounting >
   Configuration > Payment Methods).

## Access rights on rollout

``account_payment_order`` (a dependency of this module) overrides the
core Odoo access rule for bank accounts (``res.partner.bank``) and
banks (``res.bank``): creating either now requires the **Accounting /
Payments** group (``account_payment_order.group_account_payment``)
instead of the generic **Contact Creation** group. By default only
administrators belong to this group.

**This means any accounting user who could previously register a
supplier/customer bank account, or add a new bank, loses that ability
as soon as this module is installed**, until explicitly added to
**Accounting / Payments**. When rolling this module out to a client,
add the relevant accounting users to that group as part of the
go-live checklist — do not assume the existing "Contact Creation"
group still covers it.
