"""對話相關的 Pydantic 模型。"""
from typing import List, Literal
from pydantic import BaseModel, Field

__all__ = ["Message", "Conversation"]

class Message(BaseModel):
    """單則對話訊息"""

    role: Literal["user", "agent"] = Field(description="訊息角色")
    content: str = Field(description="訊息內容")

class Conversation(BaseModel):
    """對話歷史紀錄"""

    messages: List[Message] = Field(default_factory=list, description="訊息列表")

