from server.tools import tool


@tool("write_invoice")
def write_invoice(payload: dict):
    return {"status": "invoice_written", "payload": payload}


@tool("write_receipt")
def write_receipt(payload: dict):
    return {"status": "receipt_written", "payload": payload}


@tool("write_bank_statement")
def write_bank_statement(payload: dict):
    return {"status": "bank_written", "payload": payload}


@tool("log_unmatched_case")
def log_unmatched_case(payload: dict):
    return {"status": "logged", "payload": payload}