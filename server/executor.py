# server/executor.py
from server.registry import registry

class ToolExecutor:
    def register(self, name, fn):
        registry[name] = fn

    def run(self, name, args):
        if name not in registry:
            return {"error": "unknown_tool"}
        return registry[name](**args)

executor = ToolExecutor()