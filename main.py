from fastapi import FastAPI
from mcp.server import Server
from mcp.server.fastapi import create_app

# import tools
from tools.vendor import lookup_vendor
from tools.bank import query_bank
from tools.erp import query_erp
from tools.ocr import ocr_extract

# MCP server
mcp_server = Server("finance-mcp-server")

# Register tools
@mcp_server.tool()
async def tool_lookup_vendor(name: str) -> dict:
    return await lookup_vendor(name)


@mcp_server.tool()
async def tool_query_bank(amount: float, date: str) -> dict:
    return await query_bank(amount, date)


@mcp_server.tool()
async def tool_query_erp(vendor_id: str) -> dict:
    return await query_erp(vendor_id)


@mcp_server.tool()
async def tool_ocr_extract(file_url: str) -> dict:
    return await ocr_extract(file_url)


# FastAPI wrapper
app: FastAPI = create_app(mcp_server)


# Optional health check
@app.get("/health")
async def health():
    return {"status": "ok"}