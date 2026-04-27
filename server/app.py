from fastapi import FastAPI

from server.mcp_server import mcp


def create_app() -> FastAPI:
    app = FastAPI(title="Finance MCP Server")
    mcp.settings.streamable_http_path = "/"
    app.mount("/mcp", mcp.streamable_http_app())

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    test_vendors = [
        {"id": "v_100", "name": "Acme Supplies", "score": 0.97},
        {"id": "v_101", "name": "Globex Corporation", "score": 0.92},
        {"id": "v_102", "name": "Initech Services", "score": 0.88},
        {"id": "v_103", "name": "Umbrella Logistics", "score": 0.85},
    ]

    test_transactions = [
        {
            "id": "tx_9001",
            "amount": 123.45,
            "date": "2026-04-01",
            "description": "Office supplies payment",
        },
        {
            "id": "tx_9002",
            "amount": 2500.00,
            "date": "2026-04-01",
            "description": "Monthly rent",
        },
        {
            "id": "tx_9003",
            "amount": 987.65,
            "date": "2026-04-02",
            "description": "Consulting invoice settlement",
        },
    ]

    @app.get("/test-api/vendors/search")
    async def test_vendor_search(q: str = "") -> list[dict]:
        needle = q.strip().lower()
        if not needle:
            return test_vendors
        return [vendor for vendor in test_vendors if needle in vendor["name"].lower()]

    @app.get("/test-api/transactions")
    async def test_transactions_search(amount: float, date: str) -> list[dict]:
        tolerance = 5.0
        return [
            txn
            for txn in test_transactions
            if txn["date"] == date and abs(float(txn["amount"]) - amount) <= tolerance
        ]

    @app.post("/test-api/ocr")
    async def test_ocr(payload: dict) -> dict:
        file_url = str(payload.get("file_url", ""))
        sample_text = (
            "Invoice #INV-2026-0041\nVendor: Acme Supplies\nTotal: 123.45 USD"
        )
        return {
            "provider": "local-test-api",
            "file_url": file_url,
            "text": sample_text,
            "confidence": 0.98,
        }

    return app
