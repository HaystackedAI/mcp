import httpx
from core.config import settings

async def query_bank(amount: float, date: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{settings.BANK_API}/transactions",
            params={"amount": amount, "date": date}
        )
        resp.raise_for_status()
        data = resp.json()

    return {"matches": data}