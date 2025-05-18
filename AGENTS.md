# ChataLyst AI Agent 設計與操作指南

本文檔定義了 ChataLyst AI 專案中 Agent 系統的設計原則、行為規範與開發指引，適用於整個專案的 AI 代理設計與實現。

## 專案架構概述

ChataLyst AI 是基於 Pydantic AI 和 LangGraph 技術構建的自然語言到 SQL 查詢轉換系統。Agent 系統是整個應用的核心，負責理解使用者意圖、生成 SQL 並執行查詢。

```
app/
├── core/
│   ├── agents/        # Agent 實現
│   ├── graph/         # 工作流程定義
│   └── tools/         # Agent 工具函數
├── db/                # 資料庫連接與查詢
├── schemas/           # Pydantic 模型
└── ui/                # Streamlit 介面
```

## Agent 設計規範

### 1. Agent 類別結構
所有 Agent 必須繼承 `BaseAgent` 類別，並遵循以下設計模式：

```python
from app.core.agents.base import BaseAgent
from app.schemas.db_context import DBContext
from pydantic import BaseModel, Field

class CustomAgentOutput(BaseModel):
    """自定義 Agent 輸出模型。"""
    result: str = Field(description="結果描述")
    confidence: float = Field(description="置信度", ge=0, le=1)

class CustomAgent(BaseAgent):
    """自定義 Agent 實現。"""
    def __init__(self):
        super().__init__(
            deps_type=DBContext,
            output_type=CustomAgentOutput,
            system_prompt="明確的系統提示...",
        )
```

### 2. 依賴注入規範
- 使用 `deps_type` 明確定義 Agent 所需的依賴
- Agent 不應包含直接的資料庫操作，應透過依賴注入獲取資料庫連接
- 所有依賴物件應為不可變類型，確保線程安全

### 3. 工具函數設計
Agent 工具函數使用裝飾器 `@agent.tool` 定義：

```python
@agent.tool
def schema_analyzer(schema_info: Dict[str, Any], ctx: RunContext) -> str:
    """分析資料庫 schema 並提供結構化信息。
    
    Args:
        schema_info: 資料庫 schema 信息
        ctx: 運行上下文
        
    Returns:
        結構化的 schema 描述
    """
    # 實現邏輯
    return result
```

- 每個工具函數必須包含完整的 docstring
- 所有參數必須有明確的型別提示
- 工具函數應有單一職責，避免過於複雜的功能組合

## Agent 行為準則

### 1. SQL 生成安全性
- 使用參數化查詢避免 SQL 注入
- 對使用者輸入進行驗證和清理
- 限制生成 SQL 的權限（預設只讀）

### 2. 錯誤處理與恢復
- 使用 `ModelRetry` 處理可重試的錯誤
- 提供清晰的錯誤信息給使用者
- 實現漸進式增強策略，從簡單查詢開始

### 3. 上下文管理
- 維護對話歷史，理解上下文依賴的查詢
- 保留最近的查詢結果供後續參考
- 允許使用者澄清和調整之前的查詢

## 測試規範

### 1. Agent 單元測試
- 使用 `TestModel` 模擬 LLM 的回應
- 設計測試案例覆蓋典型使用場景
- 測試異常處理和錯誤恢復機制

```python
import pytest
from pydantic_ai.testing import TestModel

def test_sql_generation():
    # 設置測試模型
    test_model = TestModel().with_response({
        "sql_query": "SELECT * FROM users;",
        "explanation": "查詢所有使用者",
        "confidence": 0.9
    })
    
    # 建立 Agent 使用測試模型
    agent = SQLGeneratorAgent(model=test_model)
    
    # 執行測試
    result = agent.run("顯示所有使用者", db_context)
    
    assert result.sql_query == "SELECT * FROM users;"
    assert result.confidence > 0.8
```

### 2. 集成測試
- 測試 Agent 與工作流程的集成
- 驗證跨節點的狀態傳遞
- 模擬完整對話流程的執行

## 工作流程定義

ChataLyst AI 使用 LangGraph 定義 Agent 工作流程：

```python
@dataclass
class ChataLystState:
    """ChataLyst 工作流程狀態。"""
    user_query: str = ""
    db_context: DBContext = None
    sql_query: str = None
    query_result: Any = None
    conversation_history: list = field(default_factory=list)

@dataclass
class ParseQuery(BaseNode[ChataLystState]):
    """解析使用者查詢節點。"""
    async def run(self, ctx: GraphRunContext[ChataLystState]) -> GenerateSQL:
        # 實現邏輯
        return GenerateSQL()
```

- 節點應具有明確的輸入和輸出類型
- 狀態變更應透過返回值進行，避免直接修改
- 複雜邏輯應該委派給 Agent 而非在節點中實現

## 程式碼風格準則

### 1. 命名規範
- 使用 `snake_case` 命名函數和變數
- 使用 `PascalCase` 命名類別和型別
- 使用 `UPPER_CASE` 命名常數

### 2. 文檔規範
- 所有類別和公開函數必須有 Google 風格的 docstring
- 所有方法必須有明確的返回型別提示
- 複雜邏輯必須附帶說明註解

### 3. 結構規範
- 單一檔案不超過 500 行程式碼
- 單一函數不超過 50 行程式碼
- 保持類別的單一責任原則

## 提交與版本控制

- 提交訊息應描述「做了什麼」而不是「怎麼做的」
- 標記已完成的任務到 TASK.md
- 保持配置檔案與實現邏輯的分離

## Agent 開發最佳實踐

1. **漸進式開發**：先開發基本功能，再擴展複雜功能
2. **明確的測試案例**：為每個 Agent 定義明確的成功與失敗案例
3. **關注使用者體驗**：提供清晰的錯誤訊息和建議
4. **效能優化**：避免不必要的資料庫查詢和模型調用
5. **安全第一**：所有輸入和輸出必須經過驗證和清理

---

本文檔適用於 ChataLyst AI 專案的所有 Agent 相關開發，請嚴格遵循以上規範和最佳實踐。 