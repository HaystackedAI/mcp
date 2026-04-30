import json
import uuid
from typing import Any

import httpx

DEFAULT_TENANT_ID = "550e8400-e29b-41d4-a716-446655440000"


def _q(value: Any) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _normalize_doc_type(raw_value: Any) -> str:
    value = str(raw_value or "").strip().lower().replace(" ", "_")
    if value in {"invoice", "receipt", "bank_statement"}:
        return value
    return "unknown"


def _coerce_confidence(raw_value: Any) -> float:
    try:
        value = float(raw_value)
    except Exception:
        return 0.0
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return value


async def _extract_rows_with_openai(
    *,
    text: str,
    openai_api_key: str | None,
    model: str,
    system_prompt: str,
) -> dict:
    async with httpx.AsyncClient(timeout=239) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"text:\n{text}"},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0,
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

    return {"rows": rows}


def _build_invoice_insert_sql(rows: list[dict[str, Any]], tenant_id: str) -> str:
    statements: list[str] = []
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
            {_q(tenant_id)}::uuid, {_q(invoice_id)}::uuid, {_q(desc)}, {amount}, {_q(date_str)}
            );
            """.strip()
        statements.append(stmt)

    return "\n".join(statements)


def _build_receipt_insert_sql(rows: list[dict[str, Any]], tenant_id: str) -> str:
    statements: list[str] = []

    for row in rows:
        if not isinstance(row, dict):
            continue

        receipt_id = str(uuid.uuid4())
        receipt_no = str(row.get("receipt_no") or f"RCT-{str(receipt_id)[:8]}")
        vendor_name = str(row.get("vendor_name") or "Unknown Vendor")
        currency = str(row.get("currency") or "CAD")
        date_str = str(row.get("receipt_date") or "2026-04-28")
        raw_text = str(row.get("raw_text") or "")
        try:
            amount = float(row.get("amount_total", 0) or 0)
        except Exception:
            amount = 0.0

        stmt = f"""
            INSERT INTO s_sqlalchemy.b_receipt (
            tenant_id, id, receipt_no, vendor_name, currency, amount_total, receipt_date, raw_text,
            status, description, value, date_time, is_deleted, is_flag
            ) VALUES (
            {_q(tenant_id)}::uuid, {_q(receipt_id)}::uuid, {_q(receipt_no)}, {_q(vendor_name)}, {_q(currency)},
            {amount}, {_q(date_str)}, {_q(raw_text)},
            'active', {_q(vendor_name)}, {amount}, {_q(date_str)}, false, false
            );
            """.strip()
        statements.append(stmt)

    return "\n".join(statements)


def _build_bank_statement_insert_sql(rows: list[dict[str, Any]], tenant_id: str) -> str:
    statements: list[str] = []

    for row in rows:
        if not isinstance(row, dict):
            continue

        bs_id = str(uuid.uuid4())
        account_name = str(row.get("account_name") or "Main Account")
        counterparty = str(row.get("counterparty") or "Unknown")
        txn_type = str(row.get("txn_type") or "unknown")
        date_str = str(row.get("txn_date") or "2026-04-28")
        raw_text = str(row.get("raw_text") or "")
        try:
            amount = float(row.get("amount", 0) or 0)
        except Exception:
            amount = 0.0
        try:
            balance = float(row.get("balance", 0) or 0)
        except Exception:
            balance = 0.0

        stmt = f"""
            INSERT INTO s_sqlalchemy.b_bs (
            tenant_id, id, account_name, counterparty, txn_type, amount, balance, txn_date, raw_text,
            status, description, value, date_time, is_deleted, is_flag
            ) VALUES (
            {_q(tenant_id)}::uuid, {_q(bs_id)}::uuid, {_q(account_name)}, {_q(counterparty)}, {_q(txn_type)},
            {amount}, {balance}, {_q(date_str)}, {_q(raw_text)},
            'active', {_q(counterparty)}, {amount}, {_q(date_str)}, false, false
            );
            """.strip()
        statements.append(stmt)

    return "\n".join(statements)


async def generate_invoice_insert_sql(
    *,
    text: str,
    schema_context: str | None,
    tenant_id: str | None,
    openai_api_key: str | None,
    model: str = "gpt-4o",
) -> dict:
    _ = schema_context
    extracted = await _extract_rows_with_openai(
        text=text,
        openai_api_key=openai_api_key,
        model=model,
        system_prompt=(
            "Extract invoice rows from text and return JSON only. "
            'Format: {"rows":[{"description":"...","amount":123.45,"date":"YYYY-MM-DD"}]}'
        ),
    )
    if "rows" not in extracted:
        return extracted

    sql = _build_invoice_insert_sql(extracted["rows"], tenant_id or DEFAULT_TENANT_ID)
    if not sql:
        return {"error": "no_valid_rows_for_insert", "sql": "", "metadata": {}}

    return {"sql": sql, "metadata": {"mode": "deterministic_insert", "doc_type": "invoice", "row_count": len(extracted["rows"])}}


async def generate_receipt_insert_sql(
    *,
    text: str,
    tenant_id: str | None,
    openai_api_key: str | None,
    model: str = "gpt-4o",
) -> dict:
    extracted = await _extract_rows_with_openai(
        text=text,
        openai_api_key=openai_api_key,
        model=model,
        system_prompt=(
            "Extract receipt rows from text and return JSON only. "
            'Format: {"rows":[{"receipt_no":"...","vendor_name":"...","currency":"CAD","amount_total":123.45,"receipt_date":"YYYY-MM-DD","raw_text":"..."}]}'
        ),
    )
    if "rows" not in extracted:
        return extracted

    sql = _build_receipt_insert_sql(extracted["rows"], tenant_id or DEFAULT_TENANT_ID)
    if not sql:
        return {"error": "no_valid_rows_for_insert", "sql": "", "metadata": {}}

    return {"sql": sql, "metadata": {"mode": "deterministic_insert", "doc_type": "receipt", "row_count": len(extracted["rows"])}}


async def generate_bank_statement_insert_sql(
    *,
    text: str,
    tenant_id: str | None,
    openai_api_key: str | None,
    model: str = "gpt-4o",
) -> dict:
    extracted = await _extract_rows_with_openai(
        text=text,
        openai_api_key=openai_api_key,
        model=model,
        system_prompt=(
            "Extract bank statement rows from text and return JSON only. "
            'Format: {"rows":[{"account_name":"...","counterparty":"...","txn_type":"...","amount":123.45,"balance":456.78,"txn_date":"YYYY-MM-DD","raw_text":"..."}]}'
        ),
    )
    if "rows" not in extracted:
        return extracted

    sql = _build_bank_statement_insert_sql(extracted["rows"], tenant_id or DEFAULT_TENANT_ID)
    if not sql:
        return {"error": "no_valid_rows_for_insert", "sql": "", "metadata": {}}

    return {"sql": sql, "metadata": {"mode": "deterministic_insert", "doc_type": "bank_statement", "row_count": len(extracted["rows"])}}


async def classify_text_type_from_text(
    *,
    text: str,
    openai_api_key: str | None,
    model: str = "gpt-4o-mini",
) -> dict:
    async with httpx.AsyncClient(timeout=239) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Classify the input text into one of: invoice, receipt, bank_statement, unknown. "
                            "Return JSON with keys: doc_type, confidence, reason. "
                            "Confidence must be a float between 0 and 1."
                        ),
                    },
                    {"role": "user", "content": f"Text to classify:\n{text}"},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0,
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"] or "{}"

    try:
        parsed = json.loads(content)
    except Exception:
        return {
            "doc_type": "unknown",
            "confidence": 0.0,
            "reason": "model_did_not_return_valid_json",
            "raw": content,
        }

    if not isinstance(parsed, dict):
        return {
            "doc_type": "unknown",
            "confidence": 0.0,
            "reason": "model_json_not_object",
            "raw": content,
        }

    return {
        "doc_type": _normalize_doc_type(parsed.get("doc_type")),
        "confidence": _coerce_confidence(parsed.get("confidence")),
        "reason": str(parsed.get("reason") or "").strip(),
    }
