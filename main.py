from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
import httpx
import os

mcp = FastMCP("finance-mcp")

# -------------------------
# TOOL: Vendor lookup
# -------------------------
@mcp.tool()
async def lookup_vendor(name: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"{os.getenv('VENDOR_API')}/vendors/search",
            params={"q": name}
        )
        r.raise_for_status()
        data = r.json()

    if not data:
        return {"found": False}

    v = data[0]
    return {
        "found": True,
        "vendor_id": v["id"],
        "normalized_name": v["name"],
        "confidence": v.get("score", 0.0)
    }


# -------------------------
# TOOL: Bank matching
# -------------------------
@mcp.tool()
async def query_bank(amount: float, date: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"{os.getenv('BANK_API')}/transactions",
            params={"amount": amount, "date": date}
        )
        r.raise_for_status()
        return {"matches": r.json()}


# -------------------------
# TOOL: OCR
# -------------------------
@mcp.tool()
async def ocr_extract(file_url: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{os.getenv('OCR_API')}/ocr",
            json={"file_url": file_url}
        )
        r.raise_for_status()
        return r.json()


# -------------------------
# FastAPI wrapper (remote deployment)
# -------------------------
app = FastAPI()

# mount MCP into FastAPI
app.mount("/mcp", mcp.sse_app())


@app.get("/health")
async def health():
    return {"status": "ok"}