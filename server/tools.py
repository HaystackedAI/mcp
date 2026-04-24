# server/tools.py
from server.executor import executor

def tool(name):
    def wrap(fn):
        executor.register(name, fn)
        return fn
    return wrap

def register_all_tools(app):

    from tools.tools_document import extract_document
    from tools.tools_vendor import get_vendor_candidates
    from tools.tools_growthzone import query_erp_invoices
    from tools.tools_bank import query_bank_transactions
    from tools.tools_write import (
        write_invoice,
        write_receipt,
        write_bank_statement,
        log_unmatched_case
    )