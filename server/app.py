from fastapi import FastAPI
from server.tools import register_all_tools


def create_app():
    app = FastAPI(title="MCP Server SDK")

    register_all_tools(app)

    return app