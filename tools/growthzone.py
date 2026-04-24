from server.tools import tool


@tool("query_erp_invoices")
def query_erp_invoices(vendor_id: str):
    return [{"invoice_id": "inv1", "amount": 120, "vendor_id": vendor_id}]