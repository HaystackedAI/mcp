from server.tools import tool


@tool("extract_document")
def extract_document(file_url: str):
    return {
        "text": "extracted text",
        "vendor_raw": "AMAZON AWS",
        "amount": 120,
        "doc_type": "invoice"
    }