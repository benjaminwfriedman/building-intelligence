from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ChatMessage(BaseModel):
    id: str
    diagram_id: str
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    confidence: Optional[float] = None

class ChatRequest(BaseModel):
    message: str
    diagram_id: str

class WebSocketMessage(BaseModel):
    type: str  # 'message', 'status', 'error'
    content: str
    message_id: Optional[str] = None