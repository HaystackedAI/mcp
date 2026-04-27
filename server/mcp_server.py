import os

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("finance-mcp")


@mcp.tool()
async def lookup_vendor(name: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{os.getenv('VENDOR_API')}/vendors/search",
            params={"q": name},
        )
        response.raise_for_status()
        data = response.json()

    if not data:
        return {"found": False}

    vendor = data[0]
    return {
        "found": True,
        "vendor_id": vendor["id"],
        "normalized_name": vendor["name"],
        "confidence": vendor.get("score", 0.0),
    }


@mcp.tool()
async def query_bank(amount: float, date: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{os.getenv('BANK_API')}/transactions",
            params={"amount": amount, "date": date},
        )
        response.raise_for_status()
        return {"matches": response.json()}


@mcp.tool()
async def ocr_extract(file_url: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{os.getenv('OCR_API')}/ocr",
            json={"file_url": file_url},
        )
        response.raise_for_status()
        return response.json()
