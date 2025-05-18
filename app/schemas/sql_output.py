"""SQL 生成相關的 Pydantic 模型。"""
from pydantic import BaseModel, Field

__all__ = ["SQLOutput"]

class SQLOutput(BaseModel):
    """LLM 產生 SQL 查詢的輸出模型。"""

    sql_query: str = Field(description="生成的 SQL 查詢")
    explanation: str | None = Field(default=None, description="查詢的自然語言解釋")
    confidence: float = Field(
        default=1.0, description="SQL 準確性信心分數", ge=0.0, le=1.0
    )

