Here is a biz requirement:

User uploads a file (text PDF, scanned image PDF, CSV, or regular image) -> system applies different preprocessing based on file type:

- Text PDF -> extract text directly
- Image PDF (scanned) -> OCR first
- CSV -> parse directly, skip LLM entirely (because it's already structured data)
- Image -> OCR or use 4o vision

Then OpenAI API 4o decides if it's an invoice, receipt, bankstatement, or others.

- If invoice -> goes to invoice table
- If receipt -> goes to receipt table
- If bankstatement -> goes to bankstatement table
- If others -> goes to log table (metadata only)

If classification confidence is low (<70%) -> ask user to confirm before proceeding.

If invoice amount > $10,000 -> submit for manager approval before saving.

Need MCP to unify all preprocessing tools so other services can call them.

Need Agent (LangGraph) to handle the decision workflow (confidence check, approval routing, user feedback loop).