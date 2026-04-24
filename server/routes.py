# server/routes.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
from server.executor import executor

router = APIRouter()

class ExecuteRequest(BaseModel):
    tool: str
    args: Dict[str, Any] = {}

@router.post("/execute")
def execute(req: ExecuteRequest):
    return executor.run(req.tool, req.args)