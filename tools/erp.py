import httpx
from core.config import settings

async def query_erp(vendor_id: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{settings.ERP_API}/invoices",
            params={"vendor_id": vendor_id}
        )
        resp.raise_for_status()

    return resp.json()