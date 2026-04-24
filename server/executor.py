class ToolExecutor:
    def __init__(self):
        self.tools = {}

    def register(self, name, fn):
        self.tools[name] = fn

    def run(self, name, args):
        if name not in self.tools:
            return {"error": "unknown_tool", "tool": name}

        return self.tools[name](**args)