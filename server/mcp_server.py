import os, httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from core.config import settings

def _parse_csv_env(name: str) -> list[str]:
    value = os.getenv(name, "")
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


_default_allowed_hosts = [
    "127.0.0.1:*",
    "localhost:*",
    "[::1]:*",
    "mcpserver.fastapicloud.dev",
    "mcpserver.fastapicloud.dev:*",
]
_extra_allowed_hosts = _parse_csv_env("MCP_ALLOWED_HOSTS")

_default_allowed_origins = [
    "http://127.0.0.1:*",
    "http://localhost:*",
    "http://[::1]:*",
    "https://mcpserver.fastapicloud.dev",
]
_extra_allowed_origins = _parse_csv_env("MCP_ALLOWED_ORIGINS")
_stateless_http = _parse_bool_env("MCP_STATELESS_HTTP", True)

mcp = FastMCP(
    "finance-mcp",
    stateless_http=_stateless_http,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[*_default_allowed_hosts, *_extra_allowed_hosts],
        allowed_origins=[*_default_allowed_origins, *_extra_allowed_origins],
    ),
)


@mcp.tool()
async def lookup_vendor(name: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            "https://jsonplaceholder.typicode.com/users",
            params={"q": name},
        )

        # print(response.request.url, file=sys.stderr, flush=True)

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



@mcp.tool()
async def generate_sql_from_text(
    text: str,
    schema_context: str | None = None
) -> dict:

    async with httpx.AsyncClient(timeout=30) as client:

        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "system",
                        "content": "You convert text into SQL. Return only JSON."
                    },
                    {
                        "role": "user",
                        "content": f"""
                                        text:
                                        {text}

                                        schema_context:
                                        {schema_context}
                                        """
                    }
                ],
                "response_format": {"type": "json_object"}
            },
        )

        response.raise_for_status()
        result = response.json()

    return {
        "sql": result["choices"][0]["message"]["content"],
        "metadata": {}
    }