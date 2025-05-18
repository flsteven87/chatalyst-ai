"""Base Agent 實作，提供共用的 Agent 設定。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Type

from pydantic import BaseModel, Field
from pydantic_ai import Agent


@dataclass
class BaseDeps:
    """基本的 Agent 依賴項。"""

    connection: Any
    schema_info: Dict[str, Any]


class AgentOutput(BaseModel):
    """通用的 Agent 輸出模型。"""

    message: str = Field(description="Agent 回應內容")


class BaseAgent(Agent):
    """所有專用 Agent 的基礎類別。"""

    def __init__(
        self,
        model: str = "pydantic-ai",
        *,
        system_prompt: str = "",
        deps_type: Type[BaseDeps] = BaseDeps,
        output_type: Type[BaseModel] = AgentOutput,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            model,
            deps_type=deps_type,
            output_type=output_type,
            system_prompt=system_prompt,
            **kwargs,
        )

