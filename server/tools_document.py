# server/tools_document.py
from server.tools import tool

@tool("extract_document")
def extract_document(file_url: str):
    return {"doc_type": "invoice", "vendor_raw": "AWS", "amount": 100}