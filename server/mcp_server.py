import os, httpx, json, uuid
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
    schema_context: str | None = None,
    tenant_id: str | None = None,
) -> dict:
    # Step 1: extract structured rows (description, amount, date) from text.
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
                        "content": (
                            "Extract invoice rows from text and return JSON only. "
                            'Format: {"rows":[{"description":"...","amount":123.45,"date":"YYYY-MM-DD"}]}'
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"text:\n{text}\n\nschema_context:\n{schema_context}",
                    },
                ],
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"] or "{}"

    try:
        parsed = json.loads(content)
    except Exception:
        return {"error": "model_did_not_return_json_rows", "raw": content, "metadata": {}}

    rows = parsed.get("rows", []) if isinstance(parsed, dict) else []
    if not isinstance(rows, list) or not rows:
        return {"error": "no_rows_extracted", "sql": "", "metadata": {}}

    tid = tenant_id or "550e8400-e29b-41d4-a716-446655440000"

    def _q(value) -> str:
        return "'" + str(value).replace("'", "''") + "'"

    statements = []
    seq_seed = int(str(uuid.uuid4().int)[0:6]) * 1000
    for i, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        desc = row.get("description") or "Imported from text"
        date_str = row.get("date") or "2026-04-28"
        try:
            amount = float(row.get("amount", 0) or 0)
        except Exception:
            amount = 0.0

        invoice_id = str(uuid.uuid4())
        customer_id = str(uuid.uuid4())
        invoice_sequence = seq_seed + i

        stmt = f"""
INSERT INTO s_sqlalchemy.a_invoices (
  inv_rec, issue_date, due_date, invoice_prefix, invoice_sequence, customer_id,
  subtotal, total1, total2, total3, total4, total5, total6, total7, total8, total9,
  discount_rate, discount_flat_amount, discounted_subtotal, tax_amount, total_amount,
  amount_credited, amount_paid, balance_due, status, payment_status, mark_as_sent, auto_apply,
  tenant_id, id, description, value, date_time
) VALUES (
  'invoice', {_q(date_str)}, {_q(date_str)}, 'TXT-', {invoice_sequence}, {_q(customer_id)}::uuid,
  {amount}, 0, 0, 0, 0, 0, 0, 0, 0, 0,
  0, 0, {amount}, 0, {amount},
  0, 0, {amount}, 'processing', 'pending', false, false,
  {_q(tid)}::uuid, {_q(invoice_id)}::uuid, {_q(desc)}, {amount}, {_q(date_str)}
);
""".strip()
        statements.append(stmt)

    if not statements:
        return {"error": "no_valid_rows_for_insert", "sql": "", "metadata": {}}

    return {
        "sql": "\n".join(statements),
        "metadata": {"mode": "deterministic_insert", "row_count": len(statements)},
    }
