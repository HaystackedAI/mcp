from server.tools import tool


@tool("query_bank_transactions")
def query_bank_transactions(amount: float, date: str, vendor_hint: str):
    return [{
        "txn_id": "t1",
        "amount": amount,
        "date": date,
        "description": vendor_hint
    }]