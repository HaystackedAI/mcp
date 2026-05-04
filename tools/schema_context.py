INVOICE_RLS_TABLE = "s_sqlalchemy.invoices_rls"
INVOICE_RLS_SCHEMA_CONTEXT_VERSION = "invoice_rls_v1"

CUSTOMER_INVOICE_SCHEMA_CONTEXT = """
Document type: customer_invoice
Target table: s_sqlalchemy.invoices_rls
Source model: tools/schema/m_invoice_rls.py, InvoiceDB

Use the source text to extract invoice-level data. Return JSON only; do not write SQL.

Extraction fields:
- description: concise customer name, invoice number, or invoice memo
- amount: total invoice amount
- date: invoice issue date in YYYY-MM-DD format
- due_date: due date in YYYY-MM-DD format; use date when missing
- subtotal: subtotal before tax/discount; use amount when missing
- tax_amount: tax amount; use 0 when missing
- customer_name: customer name when visible
- invoice_number: source invoice number when visible
- line_items: array of source line items when visible, otherwise []

Important table mapping:
- inv_rec: "invoice"
- issue_date: date
- due_date: due_date
- invoice_prefix: "INV-"
- invoice_sequence: generated integer unique per tenant
- customer_id: generated UUID until customer matching exists
- customer_snapshot: JSONB object with customer_name and invoice_number when available
- line_items: JSONB array from extracted line_items
- subtotal: extracted subtotal
- discounted_subtotal: subtotal after discount; use subtotal when no discount
- tax_amount: extracted tax_amount
- total_amount: extracted amount
- balance_due: extracted amount
- status: "draft"
- payment_status: "pending"
- mark_as_sent: false
- auto_apply: false

Do not insert invoice_number because it is a computed column.
""".strip()


def get_schema_context(doc_type: str) -> tuple[str, str]:
    if doc_type == "customer_invoice":
        return CUSTOMER_INVOICE_SCHEMA_CONTEXT, INVOICE_RLS_SCHEMA_CONTEXT_VERSION
    return "", ""
