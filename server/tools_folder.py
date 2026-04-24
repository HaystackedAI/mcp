from fastapi import FastAPI
from server.executor import ToolExecutor

executor = ToolExecutor()


def tool(name: str):
    def decorator(fn):
        executor.register(name, fn)
        return fn
    return decorator


def register_all_tools(app: FastAPI):

    @app.post("/execute")
    def execute(payload: dict):
        return executor.run(
            payload["tool"],
            payload.get("args", {})
        )