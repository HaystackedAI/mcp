import os
import sys
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP

# Ensure project root is importable when this file is launched directly
# (e.g., `mcp run server/mcp_server.py:mcp`).
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import settings

mcp = FastMCP("finance-mcp")


def _require_api_base(env_var: str) -> str:
    value = str(getattr(settings, env_var, "") or "").strip()
    if not value:
        raise ValueError(
            f"{env_var} is not set. Add it in MCP Inspector -> Environment Variables."
        )
    if not value.startswith(("http://", "https://")):
        raise ValueError(
            f"{env_var} must start with http:// or https://. Current value: {value!r}"
        )
    return value.rstrip("/")


def _build_url(env_var: str, path: str) -> str:
    return f"{_require_api_base(env_var)}{path}"


def _require_full_url(env_var: str) -> str | None:
    value = str(getattr(settings, env_var, "") or "").strip()
    if not value:
        return None
    if not value.startswith(("http://", "https://")):
        raise ValueError(
            f"{env_var} must start with http:// or https://. Current value: {value!r}"
        )
    return value


def _resolve_endpoint(full_url_env: str, base_env: str, path: str) -> str:
    full_url = _require_full_url(full_url_env)
    if full_url:
        return full_url
    return _build_url(base_env, path)


@mcp.resource(
    "finance://server/info",
    name="Server Info",
    description="Basic info and available MCP tools/resources.",
)
def server_info() -> dict:
    return {
        "server": "finance-mcp",
        "tools": ["lookup_vendor", "query_bank", "ocr_extract"],
        "resources": [
            "finance://server/info",
            "finance://config/env",
            "finance://tool/{tool_name}/example",
        ],
    }


@mcp.resource(
    "finance://config/env",
    name="Environment Config",
    description="Shows whether required upstream API base URLs are configured.",
)
def env_config() -> dict:
    required = ["VENDOR_API", "BANK_API", "OCR_API"]
    optional = ["VENDOR_SEARCH_URL", "BANK_TRANSACTIONS_URL", "OCR_URL"]
    values = {key: str(getattr(settings, key, "") or "").strip() for key in required}
    optional_values = {
        key: str(getattr(settings, key, "") or "").strip() for key in optional
    }
    return {
        "configured": {key: bool(values[key]) for key in required},
        "valid_with_protocol": {
            key: values[key].startswith(("http://", "https://")) for key in required
        },
        "current_values": values,
        "optional_overrides": {
            "configured": {key: bool(optional_values[key]) for key in optional},
            "valid_with_protocol": {
                key: optional_values[key].startswith(("http://", "https://"))
                for key in optional
            },
            "current_values": optional_values,
        },
    }


@mcp.resource(
    "finance://tool/{tool_name}/example",
    name="Tool Input Example",
    description="Returns example payloads for each MCP tool.",
)
def tool_example(tool_name: str) -> dict:
    examples = {
        "lookup_vendor": {"name": "Acme Inc"},
        "query_bank": {"amount": 123.45, "date": "2026-04-01"},
        "ocr_extract": {"file_url": "https://example.com/sample.pdf"},
    }
    if tool_name not in examples:
        return {
            "error": "Unknown tool",
            "valid_tools": sorted(examples.keys()),
        }
    return {"tool": tool_name, "example_input": examples[tool_name]}


@mcp.resource(
    "finance://config/public-testing",
    name="Public Testing Config",
    description="Ready-to-use public endpoint config for MCP Inspector.",
)
def public_testing_config() -> dict:
    return {
        "note": (
            "Use per-tool URL overrides for public testing. "
            "These do not require VENDOR_API/BANK_API/OCR_API."
        ),
        "environment_variables": {
            "VENDOR_SEARCH_URL": "https://jsonplaceholder.typicode.com/users",
            "BANK_TRANSACTIONS_URL": "https://httpbin.org/anything/transactions",
            "OCR_URL": "https://postman-echo.com/post",
        },
    }


@mcp.tool()
async def lookup_vendor(name: str) -> dict:
    url = _resolve_endpoint("VENDOR_SEARCH_URL", "VENDOR_API", "/vendors/search")
    query = name.strip().lower()
    if not query:
        return {"found": False}

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

    candidates = []
    if isinstance(data, list):
        candidates = data
    elif isinstance(data, dict):
        if isinstance(data.get("users"), list):
            candidates = data["users"]
        elif isinstance(data.get("data"), list):
            candidates = data["data"]

    if not candidates:
        return {"found": False}

    matched_vendor = None
    for vendor in candidates:
        haystacks = [
            str(vendor.get("name", "")),
            str(vendor.get("username", "")),
            str(vendor.get("email", "")),
            str(vendor.get("company", {}).get("name", "")),
            f"{vendor.get('firstName', '')} {vendor.get('lastName', '')}",
        ]
        if any(query in h.lower() for h in haystacks if h):
            matched_vendor = vendor
            break

    if not matched_vendor:
        return {"found": False}

    vendor = matched_vendor
    normalized_name = vendor.get("name")
    if not normalized_name:
        first = str(vendor.get("firstName", "")).strip()
        last = str(vendor.get("lastName", "")).strip()
        normalized_name = (f"{first} {last}").strip() or "Unknown"

    return {
        "found": True,
        "vendor_id": vendor.get("id"),
        "normalized_name": normalized_name,
        "confidence": vendor.get("score", 0.8),
    }


@mcp.tool()
async def query_bank(amount: float, date: str) -> dict:
    url = _resolve_endpoint("BANK_TRANSACTIONS_URL", "BANK_API", "/transactions")
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            url,
            params={"amount": amount, "date": date},
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and isinstance(payload.get("transactions"), list):
            return {"matches": payload["transactions"]}
        return {"matches": payload}


@mcp.tool()
async def ocr_extract(file_url: str) -> dict:
    url = _resolve_endpoint("OCR_URL", "OCR_API", "/ocr")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            url,
            json={"file_url": file_url},
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and isinstance(payload.get("text"), str):
            return payload
        echoed = None
        if isinstance(payload, dict):
            echoed_json = payload.get("json")
            if isinstance(echoed_json, dict):
                echoed = echoed_json.get("file_url")
        return {
            "provider": "public-test",
            "file_url": echoed or file_url,
            "text": "",
            "confidence": 0.0,
            "raw_response": payload,
        }
