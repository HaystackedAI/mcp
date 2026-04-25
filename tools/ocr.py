import httpx
from core.config import settings

async def ocr_extract(file_url: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.OCR_API}/ocr",
            json={"file_url": file_url}
        )
        resp.raise_for_status()

    return resp.json()