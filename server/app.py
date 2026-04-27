from fastapi import FastAPI

from server.mcp_server import mcp


def create_app() -> FastAPI:
    app = FastAPI(title="Finance MCP Server")
    app.mount("/mcp", mcp.sse_app())

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
