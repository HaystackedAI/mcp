import json
import logging
import time
import uuid
from typing import Any

import httpx

DEFAULT_TENANT_ID = "550e8400-e29b-41d4-a716-446655440000"
OPENAI_TIMEOUT_SECONDS = 300
logger = logging.getLogger(__name__)

DOCUMENT_TYPES = {
    "customer_invoice",
    "vendor_bill",
    "payment_voucher",
    "sales_receipt",
    "bank_statement",
    "creditcard_statement",
}

DOCUMENT_TYPE_ALIASES = {
    "invoice": "customer_invoice",
    "customer_invoice": "customer_invoice",
    "customer invoice": "customer_invoice",
    "bill": "vendor_bill",
    "vendor_bill": "vendor_bill",
    "vendor bill": "vendor_bill",
    "voucher": "payment_voucher",
    "payment_voucher": "payment_voucher",
    "payment voucher": "payment_voucher",
    "receipt": "sales_receipt",
    "sales_receipt": "sales_receipt",
    "sales receipt": "sales_receipt",
    "bankstatement": "bank_statement",
    "bank_statement": "bank_statement",
    "bank statement": "bank_statement",
    "credit_card_statement": "creditcard_statement",
    "credit card statement": "creditcard_statement",
    "creditcard_statement": "creditcard_statement",
    "creditcard statement": "creditcard_statement",
}

DOCUMENT_TYPE_TABLE_ROUTES = {
    "customer_invoice": "invoice",
    "vendor_bill": "invoice",
    "payment_voucher": "receipt",
    "sales_receipt": "receipt",
    "bank_statement": "bank_statement",
    "creditcard_statement": "bank_statement",
}


def _q(value: Any) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _normalize_doc_type(raw_value: Any) -> str:
    value = str(raw_value or "").strip().lower()
    return DOCUMENT_TYPE_ALIASES.get(value, DOCUMENT_TYPE_ALIASES.get(value.replace(" ", "_"), "unknown"))


def _route_for_doc_type(doc_type: str) -> str:
    return DOCUMENT_TYPE_TABLE_ROUTES.get(_normalize_doc_type(doc_type), "unknown")


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
    request_id = str(uuid.uuid4())
    started = time.perf_counter()
    logger.info(
        "OpenAI extraction started request_id=%s model=%s text_length=%s prompt_length=%s api_key_present=%s",
        request_id,
        model,
        len(text or ""),
        len(system_prompt or ""),
        bool(openai_api_key),
    )
    try:
        async with httpx.AsyncClient(timeout=OPENAI_TIMEOUT_SECONDS) as client:
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
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.info(
                "OpenAI extraction response request_id=%s model=%s status_code=%s elapsed_ms=%s body_preview=%r",
                request_id,
                model,
                response.status_code,
                elapsed_ms,
                response.text[:1000],
            )
            response.raise_for_status()
            payload = response.json()
            content = payload["choices"][0]["message"]["content"] or "{}"
    except httpx.HTTPStatusError as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.exception(
            "OpenAI extraction HTTP error request_id=%s model=%s status_code=%s elapsed_ms=%s body=%r",
            request_id,
            model,
            exc.response.status_code,
            elapsed_ms,
            exc.response.text[:2000],
        )
        raise
    except httpx.TimeoutException:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.exception(
            "OpenAI extraction timeout request_id=%s model=%s elapsed_ms=%s timeout_seconds=%s text_length=%s",
            request_id,
            model,
            elapsed_ms,
            OPENAI_TIMEOUT_SECONDS,
            len(text or ""),
        )
        raise
    except Exception:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.exception("OpenAI extraction failed request_id=%s model=%s elapsed_ms=%s", request_id, model, elapsed_ms)
        raise

    try:
        parsed = json.loads(content)
    except Exception:
        logger.exception(
            "OpenAI extraction JSON parse failed request_id=%s model=%s content_preview=%r",
            request_id,
            model,
            content[:1000],
        )
        return {"error": "model_did_not_return_json_rows", "raw": content, "metadata": {}}

    rows = parsed.get("rows", []) if isinstance(parsed, dict) else []
    if not isinstance(rows, list) or not rows:
        logger.error(
            "OpenAI extraction found no rows request_id=%s model=%s parsed_type=%s parsed_preview=%s",
            request_id,
            model,
            type(parsed).__name__,
            str(parsed)[:1000],
        )
        return {"error": "no_rows_extracted", "sql": "", "metadata": {}}

    logger.info("OpenAI extraction completed request_id=%s model=%s row_count=%s", request_id, model, len(rows))
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
    logger.info("Generating invoice SQL text_length=%s tenant_id=%s model=%s", len(text or ""), tenant_id, model)
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
        logger.error("Invoice SQL generation produced no statements row_count=%s", len(extracted["rows"]))
        return {"error": "no_valid_rows_for_insert", "sql": "", "metadata": {}}

    logger.info("Invoice SQL generated row_count=%s sql_length=%s", len(extracted["rows"]), len(sql))
    return {
        "sql": sql,
        "metadata": {
            "mode": "deterministic_insert",
            "doc_type": "customer_invoice",
            "table_route": "invoice",
            "row_count": len(extracted["rows"]),
        },
    }


async def generate_receipt_insert_sql(
    *,
    text: str,
    tenant_id: str | None,
    openai_api_key: str | None,
    model: str = "gpt-4o",
) -> dict:
    logger.info("Generating receipt SQL text_length=%s tenant_id=%s model=%s", len(text or ""), tenant_id, model)
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
        logger.error("Receipt SQL generation produced no statements row_count=%s", len(extracted["rows"]))
        return {"error": "no_valid_rows_for_insert", "sql": "", "metadata": {}}

    logger.info("Receipt SQL generated row_count=%s sql_length=%s", len(extracted["rows"]), len(sql))
    return {
        "sql": sql,
        "metadata": {
            "mode": "deterministic_insert",
            "doc_type": "sales_receipt",
            "table_route": "receipt",
            "row_count": len(extracted["rows"]),
        },
    }


async def generate_bank_statement_insert_sql(
    *,
    text: str,
    tenant_id: str | None,
    openai_api_key: str | None,
    model: str = "gpt-4o",
) -> dict:
    logger.info("Generating bank statement SQL text_length=%s tenant_id=%s model=%s", len(text or ""), tenant_id, model)
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
        logger.error("Bank statement SQL generation produced no statements row_count=%s", len(extracted["rows"]))
        return {"error": "no_valid_rows_for_insert", "sql": "", "metadata": {}}

    logger.info("Bank statement SQL generated row_count=%s sql_length=%s", len(extracted["rows"]), len(sql))
    return {
        "sql": sql,
        "metadata": {
            "mode": "deterministic_insert",
            "doc_type": "bank_statement",
            "table_route": "bank_statement",
            "row_count": len(extracted["rows"]),
        },
    }


async def generate_customer_invoice_insert_sql(
    *,
    text: str,
    tenant_id: str | None,
    openai_api_key: str | None,
    schema_context: str | None = None,
    model: str = "gpt-4o",
) -> dict:
    return await generate_invoice_insert_sql(
        text=text,
        schema_context=schema_context,
        tenant_id=tenant_id,
        openai_api_key=openai_api_key,
        model=model,
    )


async def generate_vendor_bill_insert_sql(
    *,
    text: str,
    tenant_id: str | None,
    openai_api_key: str | None,
    model: str = "gpt-4o",
) -> dict:
    logger.info("Generating vendor bill SQL text_length=%s tenant_id=%s model=%s", len(text or ""), tenant_id, model)
    extracted = await _extract_rows_with_openai(
        text=text,
        openai_api_key=openai_api_key,
        model=model,
        system_prompt=(
            "Extract vendor bill rows from text and return JSON only. "
            "Use description for the bill issuer, bill number, or memo. "
            'Format: {"rows":[{"description":"...","amount":123.45,"date":"YYYY-MM-DD"}]}'
        ),
    )
    if "rows" not in extracted:
        return extracted

    sql = _build_invoice_insert_sql(extracted["rows"], tenant_id or DEFAULT_TENANT_ID)
    if not sql:
        logger.error("Vendor bill SQL generation produced no statements row_count=%s", len(extracted["rows"]))
        return {"error": "no_valid_rows_for_insert", "sql": "", "metadata": {}}

    logger.info("Vendor bill SQL generated row_count=%s sql_length=%s", len(extracted["rows"]), len(sql))
    return {
        "sql": sql,
        "metadata": {
            "mode": "deterministic_insert",
            "doc_type": "vendor_bill",
            "table_route": "invoice",
            "row_count": len(extracted["rows"]),
        },
    }


async def generate_payment_voucher_insert_sql(
    *,
    text: str,
    tenant_id: str | None,
    openai_api_key: str | None,
    model: str = "gpt-4o",
) -> dict:
    logger.info("Generating payment voucher SQL text_length=%s tenant_id=%s model=%s", len(text or ""), tenant_id, model)
    extracted = await _extract_rows_with_openai(
        text=text,
        openai_api_key=openai_api_key,
        model=model,
        system_prompt=(
            "Extract payment voucher rows from text and return JSON only. "
            "Use vendor_name for the payee and receipt_no for the voucher or payment reference number. "
            'Format: {"rows":[{"receipt_no":"...","vendor_name":"...","currency":"CAD","amount_total":123.45,"receipt_date":"YYYY-MM-DD","raw_text":"..."}]}'
        ),
    )
    if "rows" not in extracted:
        return extracted

    sql = _build_receipt_insert_sql(extracted["rows"], tenant_id or DEFAULT_TENANT_ID)
    if not sql:
        logger.error("Payment voucher SQL generation produced no statements row_count=%s", len(extracted["rows"]))
        return {"error": "no_valid_rows_for_insert", "sql": "", "metadata": {}}

    logger.info("Payment voucher SQL generated row_count=%s sql_length=%s", len(extracted["rows"]), len(sql))
    return {
        "sql": sql,
        "metadata": {
            "mode": "deterministic_insert",
            "doc_type": "payment_voucher",
            "table_route": "receipt",
            "row_count": len(extracted["rows"]),
        },
    }


async def generate_sales_receipt_insert_sql(
    *,
    text: str,
    tenant_id: str | None,
    openai_api_key: str | None,
    model: str = "gpt-4o",
) -> dict:
    return await generate_receipt_insert_sql(
        text=text,
        tenant_id=tenant_id,
        openai_api_key=openai_api_key,
        model=model,
    )


async def generate_creditcard_statement_insert_sql(
    *,
    text: str,
    tenant_id: str | None,
    openai_api_key: str | None,
    model: str = "gpt-4o",
) -> dict:
    logger.info("Generating credit card statement SQL text_length=%s tenant_id=%s model=%s", len(text or ""), tenant_id, model)
    extracted = await _extract_rows_with_openai(
        text=text,
        openai_api_key=openai_api_key,
        model=model,
        system_prompt=(
            "Extract credit card statement transaction rows from text and return JSON only. "
            "Use account_name for the card/account label, counterparty for merchant/payee, and txn_type for debit/credit/fee/payment. "
            'Format: {"rows":[{"account_name":"...","counterparty":"...","txn_type":"...","amount":123.45,"balance":456.78,"txn_date":"YYYY-MM-DD","raw_text":"..."}]}'
        ),
    )
    if "rows" not in extracted:
        return extracted

    sql = _build_bank_statement_insert_sql(extracted["rows"], tenant_id or DEFAULT_TENANT_ID)
    if not sql:
        logger.error("Credit card statement SQL generation produced no statements row_count=%s", len(extracted["rows"]))
        return {"error": "no_valid_rows_for_insert", "sql": "", "metadata": {}}

    logger.info("Credit card statement SQL generated row_count=%s sql_length=%s", len(extracted["rows"]), len(sql))
    return {
        "sql": sql,
        "metadata": {
            "mode": "deterministic_insert",
            "doc_type": "creditcard_statement",
            "table_route": "bank_statement",
            "row_count": len(extracted["rows"]),
        },
    }


async def generate_insert_sql_for_doc_type(
    *,
    doc_type: str,
    text: str,
    schema_context: str | None = None,
    tenant_id: str | None,
    openai_api_key: str | None,
    model: str = "gpt-4o",
) -> dict:
    normalized_doc_type = _normalize_doc_type(doc_type)
    if normalized_doc_type == "customer_invoice":
        return await generate_customer_invoice_insert_sql(
            text=text,
            schema_context=schema_context,
            tenant_id=tenant_id,
            openai_api_key=openai_api_key,
            model=model,
        )
    if normalized_doc_type == "vendor_bill":
        return await generate_vendor_bill_insert_sql(
            text=text,
            tenant_id=tenant_id,
            openai_api_key=openai_api_key,
            model=model,
        )
    if normalized_doc_type == "payment_voucher":
        return await generate_payment_voucher_insert_sql(
            text=text,
            tenant_id=tenant_id,
            openai_api_key=openai_api_key,
            model=model,
        )
    if normalized_doc_type == "sales_receipt":
        return await generate_sales_receipt_insert_sql(
            text=text,
            tenant_id=tenant_id,
            openai_api_key=openai_api_key,
            model=model,
        )
    if normalized_doc_type == "bank_statement":
        return await generate_bank_statement_insert_sql(
            text=text,
            tenant_id=tenant_id,
            openai_api_key=openai_api_key,
            model=model,
        )
    if normalized_doc_type == "creditcard_statement":
        return await generate_creditcard_statement_insert_sql(
            text=text,
            tenant_id=tenant_id,
            openai_api_key=openai_api_key,
            model=model,
        )

    return {
        "error": "unsupported_doc_type",
        "sql": "",
        "metadata": {"doc_type": "unknown", "table_route": "unknown"},
    }


async def classify_text_type_from_text(
    *,
    text: str,
    openai_api_key: str | None,
    model: str = "gpt-4o-mini",
) -> dict:
    request_id = str(uuid.uuid4())
    started = time.perf_counter()
    logger.info(
        "OpenAI classification started request_id=%s model=%s text_length=%s api_key_present=%s",
        request_id,
        model,
        len(text or ""),
        bool(openai_api_key),
    )
    try:
        async with httpx.AsyncClient(timeout=OPENAI_TIMEOUT_SECONDS) as client:
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
                                "Classify the input text into one of: "
                                "customer_invoice, vendor_bill, payment_voucher, sales_receipt, "
                                "bank_statement, creditcard_statement, unknown. "
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
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.info(
                "OpenAI classification response request_id=%s model=%s status_code=%s elapsed_ms=%s body_preview=%r",
                request_id,
                model,
                response.status_code,
                elapsed_ms,
                response.text[:1000],
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"] or "{}"
    except Exception:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.exception("OpenAI classification failed request_id=%s model=%s elapsed_ms=%s", request_id, model, elapsed_ms)
        raise

    try:
        parsed = json.loads(content)
    except Exception:
        logger.exception(
            "OpenAI classification JSON parse failed request_id=%s model=%s content_preview=%r",
            request_id,
            model,
            content[:1000],
        )
        return {
            "doc_type": "unknown",
            "confidence": 0.0,
            "reason": "model_did_not_return_valid_json",
            "raw": content,
        }

    if not isinstance(parsed, dict):
        logger.error(
            "OpenAI classification JSON was not an object request_id=%s model=%s parsed_type=%s",
            request_id,
            model,
            type(parsed).__name__,
        )
        return {
            "doc_type": "unknown",
            "confidence": 0.0,
            "reason": "model_json_not_object",
            "raw": content,
        }

    result = {
        "doc_type": _normalize_doc_type(parsed.get("doc_type")),
        "confidence": _coerce_confidence(parsed.get("confidence")),
        "reason": str(parsed.get("reason") or "").strip(),
    }
    result["table_route"] = _route_for_doc_type(result["doc_type"])
    logger.info("OpenAI classification completed request_id=%s model=%s result=%s", request_id, model, result)
    return result
