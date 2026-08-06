from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any

class AIQueryRequest(BaseModel):
    message: str = Field(..., description="User query in natural language")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Active context metadata")

class AIQueryResponse(BaseModel):
    intent: str
    confidence: float
    data: Optional[Dict[str, Any]] = None
    answer: str
