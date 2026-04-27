from contextlib import asynccontextmanager

from fastapi import FastAPI

from server.mcp_server import mcp


def create_app() -> FastAPI:
    mcp.settings.streamable_http_path = "/"
    mcp_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        async with mcp.session_manager.run():
            yield

    app = FastAPI(title="Finance MCP Server", lifespan=lifespan)
    app.mount("/mcp", mcp_app)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
