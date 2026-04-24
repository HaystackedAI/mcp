# server/app.py
from fastapi import FastAPI
from server.routes import router
from server.tools import register_all_tools

def create_app():
    app = FastAPI(title="MCP Server SDK")

    register_all_tools(app)
    app.include_router(router)

    return app