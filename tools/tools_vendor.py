# server/tools_vendor.py
from server.tools import tool


# {
#     "tool": "get_vendor_candidates",
#     "args": {
#       "vendor_raw": "AWS"
#     }
#   }

@tool("get_vendor_candidates")
def get_vendor_candidates(vendor_raw: str):
    return [{"vendor_id": "v1", "name": "AWS"}]