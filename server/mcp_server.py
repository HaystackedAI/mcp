import logging
import os
import time

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from core.config import settings
from tools.invoice_ingest import (
    classify_text_type_from_text,
    generate_bank_statement_insert_sql,
    generate_invoice_insert_sql,
    generate_receipt_insert_sql,
)

logger = logging.getLogger(__name__)


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
    async with httpx.AsyncClient(timeout=239) as client:
        response = await client.post(
            f"{os.getenv('OCR_API')}/ocr",
            json={"file_url": file_url},
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def classify_text_type(text: str) -> dict:
    started = time.perf_counter()
    logger.info("MCP tool classify_text_type started text_length=%s api_key_present=%s", len(text or ""), bool(settings.OPENAI_API_KEY))
    try:
        result = await classify_text_type_from_text(
            text=text,
            openai_api_key=settings.OPENAI_API_KEY,
        )
    except Exception:
        logger.exception("MCP tool classify_text_type failed elapsed_ms=%s", int((time.perf_counter() - started) * 1000))
        raise
    logger.info("MCP tool classify_text_type completed elapsed_ms=%s result=%s", int((time.perf_counter() - started) * 1000), result)
    return result


@mcp.tool()
async def generate_invoice_sql(text: str, tenant_id: str | None = None) -> dict:
    started = time.perf_counter()
    logger.info(
        "MCP tool generate_invoice_sql started text_length=%s tenant_id=%s api_key_present=%s",
        len(text or ""),
        tenant_id,
        bool(settings.OPENAI_API_KEY),
    )
    try:
        result = await generate_invoice_insert_sql(
            text=text,
            schema_context=None,
            tenant_id=tenant_id,
            openai_api_key=settings.OPENAI_API_KEY,
        )
    except Exception:
        logger.exception("MCP tool generate_invoice_sql failed elapsed_ms=%s", int((time.perf_counter() - started) * 1000))
        raise
    logger.info(
        "MCP tool generate_invoice_sql completed elapsed_ms=%s result_keys=%s sql_length=%s",
        int((time.perf_counter() - started) * 1000),
        sorted(result.keys()) if isinstance(result, dict) else None,
        len(result.get("sql", "")) if isinstance(result, dict) else None,
    )
    return result


@mcp.tool()
async def generate_receipt_sql(text: str, tenant_id: str | None = None) -> dict:
    started = time.perf_counter()
    logger.info(
        "MCP tool generate_receipt_sql started text_length=%s tenant_id=%s api_key_present=%s",
        len(text or ""),
        tenant_id,
        bool(settings.OPENAI_API_KEY),
    )
    try:
        result = await generate_receipt_insert_sql(
            text=text,
            tenant_id=tenant_id,
            openai_api_key=settings.OPENAI_API_KEY,
        )
    except Exception:
        logger.exception("MCP tool generate_receipt_sql failed elapsed_ms=%s", int((time.perf_counter() - started) * 1000))
        raise
    logger.info(
        "MCP tool generate_receipt_sql completed elapsed_ms=%s result_keys=%s sql_length=%s",
        int((time.perf_counter() - started) * 1000),
        sorted(result.keys()) if isinstance(result, dict) else None,
        len(result.get("sql", "")) if isinstance(result, dict) else None,
    )
    return result


@mcp.tool()
async def generate_bank_statement_sql(text: str, tenant_id: str | None = None) -> dict:
    started = time.perf_counter()
    logger.info(
        "MCP tool generate_bank_statement_sql started text_length=%s tenant_id=%s api_key_present=%s",
        len(text or ""),
        tenant_id,
        bool(settings.OPENAI_API_KEY),
    )
    try:
        result = await generate_bank_statement_insert_sql(
            text=text,
            tenant_id=tenant_id,
            openai_api_key=settings.OPENAI_API_KEY,
        )
    except Exception:
        logger.exception("MCP tool generate_bank_statement_sql failed elapsed_ms=%s", int((time.perf_counter() - started) * 1000))
        raise
    logger.info(
        "MCP tool generate_bank_statement_sql completed elapsed_ms=%s result_keys=%s sql_length=%s result_preview=%s",
        int((time.perf_counter() - started) * 1000),
        sorted(result.keys()) if isinstance(result, dict) else None,
        len(result.get("sql", "")) if isinstance(result, dict) else None,
        str(result)[:1000],
    )
    return result


@mcp.tool()
async def generate_sql_from_text(
    text: str,
    schema_context: str | None = None,
    tenant_id: str | None = None,
) -> dict:
    _ = schema_context
    return await generate_invoice_insert_sql(
        text=text,
        schema_context=None,
        tenant_id=tenant_id,
        openai_api_key=settings.OPENAI_API_KEY,
    )
