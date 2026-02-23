from pydantic import BaseModel
from typing import Optional, Dict, Any

class TaskResponse(BaseModel):
    task_id: str
    status: str

class TaskStatus(BaseModel):
    task_id: str
    status: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
