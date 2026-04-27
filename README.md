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





User
 ↓
Frontend (chat/UI)
 ↓
AI Agent (LLM runtime)
     ↓
     MCP client calls "list_tools"
     ↓
     receives tool list (lookup_vendor, query_bank, ocr_extract)
     ↓
     tool list + user prompt go into LLM context
     ↓
LLM decides tool call
     ↓
MCP client sends:
   call tool lookup_vendor(name=...)
 ↓
MCP SERVER (your server/mcp_server.py process)
     ↓
     lookup_vendor()  ← @mcp.tool
     ↓
     httpx call
     ↓
External API / DB (this is your real backend system)
     ↓
result returned to MCP server
     ↓
MCP client receives result
     ↓
LLM consumes result
     ↓
LLM decides:
   - final answer OR
   - next tool call
     ↓
Frontend
 ↓
User

Environment notes for deployed MCP endpoint:

- `MCP_ALLOWED_HOSTS`: comma-separated host allowlist for MCP transport security (examples: `mcpserver.fastapicloud.dev,mcpserver.fastapicloud.dev:*`)
- `MCP_ALLOWED_ORIGINS`: comma-separated origin allowlist (examples: `https://mcpserver.fastapicloud.dev`)

If your platform gives a new hostname, add it to these env vars and redeploy.






 mcp dev server/mcp_server.py:mcp

 npx -y @modelcontextprotocol/inspector --transport http --server-url https://mcpserver.fastapicloud.dev/mcp/
