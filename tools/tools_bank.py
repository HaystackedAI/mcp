# server/tools_bank.py
from server.tools import tool


# {
#     "tool": "query_bank_transactions",
#     "args": {
#       "amount": 100,
#       "date": "2026-01-01",
#       "vendor_hint": "AWS"
#     }
#   }

@tool("query_bank_transactions")
def query_bank_transactions(amount: float, date: str, vendor_hint: str):
    return [{"txn_id": "t4441", "amount": amount}]