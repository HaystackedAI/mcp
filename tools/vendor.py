from server.tools import tool


@tool("get_vendor_candidates")
def get_vendor_candidates(vendor_raw: str):
    return [
        {"vendor_id": "v1", "name": "Amazon AWS"},
        {"vendor_id": "v2", "name": "Microsoft"}
    ]