# server/tools_growthzone.py
from server.tools import tool

@tool("query_erp_invoices")
def query_erp_invoices(vendor_id: str):
    return [{"invoice_id": "i1", "amount": 100}]