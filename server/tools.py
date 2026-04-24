# server/tools.py
from server.executor import executor

def tool(name):
    def wrap(fn):
        executor.register(name, fn)
        return fn
    return wrap

def register_all_tools(app):

    from server.tools_document import extract_document
    from server.tools_vendor import get_vendor_candidates
    from server.tools_growthzone import query_erp_invoices
    from server.tools_bank import query_bank_transactions
    from server.tools_write import (
        write_invoice,
        write_receipt,
        write_bank_statement,
        log_unmatched_case
    )