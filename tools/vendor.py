import httpx
from core.config import settings

async def lookup_vendor(name: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{settings.VENDOR_API}/vendors/search",
            params={"q": name}
        )
        resp.raise_for_status()
        data = resp.json()

    # normalize response
    if not data:
        return {"found": False}

    top = data[0]
    return {
        "found": True,
        "vendor_id": top["id"],
        "normalized_name": top["name"],
        "confidence": top.get("score", 0.0)
    }