# ChataLyst AI: SQL 自然語言處理項目

## 專案概述

ChataLyst AI 是一個透過自然語言對話來生成並執行 SQL 查詢的應用程式。使用者可以用自然語言提出問題，系統將轉換為 SQL 查詢，在目標資料庫中執行，並以易於理解的方式回應結果。

## 技術架構

### 核心元件

1. **Pydantic AI Agent 系統**
   - 使用 Pydantic AI 建構 Agent 處理自然語言輸入和 SQL 生成
   - 定義明確的輸入/輸出類型和依賴關係
   - 利用 Pydantic 模型驗證 SQL 和資料庫相關的結構化資料

2. **LangGraph 工作流程管理**
   - 使用 Pydantic Graph 建立明確的對話和 SQL 生成流程
   - 透過 `BaseNode` 實現的節點定義查詢理解、SQL 生成和結果處理過程
   - 提供節點狀態可視化和工作流程監控

3. **資料庫互動系統**
   - 初期連接到 SQLite 資料庫 (POC 階段)
   - 安全執行生成的 SQL 查詢
   - 處理查詢結果結構化
   - 準備 PostgreSQL 遷移路徑

4. **對話式使用者介面**
   - 以 Streamlit 實現的互動式網頁介面
   - 顯示生成的 SQL 供確認
   - 以視覺化方式呈現查詢結果
   - 提供對話歷史記錄查看

### Agent 架構設計

我們將使用 Pydantic AI 的 `Agent` 類別和依賴注入系統，並結合 `output_type` 的類型驗證功能：

```python
from dataclasses import dataclass
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

@dataclass
class DBContext:
    """資料庫上下文，作為 Agent 的依賴注入"""
    connection: Any  # SQLite/PostgreSQL 連接
    schema_info: dict  # 資料庫結構信息

class SQLOutput(BaseModel):
    """SQL 生成器的輸出模型"""
    sql_query: str = Field(description="生成的 SQL 查詢")
    explanation: str = Field(description="查詢的自然語言解釋")
    confidence: float = Field(description="SQL 準確性信心分數", ge=0, le=1)

sql_generator = Agent(
    'pydantic-ai',
    deps_type=DBContext,
    output_type=SQLOutput,
    system_prompt="把使用者自然語言轉換為 SQL 查詢..."
)
```

### 工作流程設計

使用 Pydantic Graph 建立工作流程：

```python
from dataclasses import dataclass, field
from pydantic_graph import BaseNode, End, Graph, GraphRunContext

@dataclass
class ChataLystState:
    """整體工作流程狀態"""
    user_query: str = ""
    db_context: DBContext = None
    sql_query: str = None
    query_result: Any = None
    conversation_history: list = field(default_factory=list)

@dataclass
class ParseQuery(BaseNode[ChataLystState]):
    """解析使用者查詢的節點"""
    async def run(self, ctx: GraphRunContext[ChataLystState]) -> GenerateSQL:
        # 使用 Pydantic AI 理解查詢
        return GenerateSQL()

@dataclass
class GenerateSQL(BaseNode[ChataLystState]):
    """生成 SQL 查詢的節點"""
    async def run(self, ctx: GraphRunContext[ChataLystState]) -> ExecuteSQL | RefineQuery:
        # 使用 SQL Generator Agent 生成 SQL
        if confidence > threshold:
            return ExecuteSQL()
        else:
            return RefineQuery()

# 其他節點...
```

### 資料流程

```
使用者輸入 → ParseQuery 節點 → GenerateSQL 節點 → [ValidationNode] → 
ExecuteSQL 節點 → FormatResults 節點 → 使用者回應
```

## 技術選擇

### 核心框架與依賴

- **Python 3.12**: 主要開發語言
- **SQLAlchemy**: 資料庫操作與連接管理
- **Pydantic**: 資料驗證和 schema 定義
- **Pydantic AI**: 建構智能 Agent 和工具函數
- **Pydantic Graph**: 基於 Pydantic AI 的工作流程管理
- **Streamlit**: 使用者介面 (POC 階段)
- **SQLite**: 資料庫後端 (POC 階段)
- **PostgreSQL**: 資料庫後端 (產品階段)

### 開發工具

- **Python 虛擬環境**: 依賴管理
- **Pytest**: 單元測試和整合測試
- **Black**: 程式碼格式化
- **Ruff**: 代碼檢查
- **pre-commit**: 提交前檢查

## 專案結構

```
chatalyst-ai/
├── app/                      # 主應用程式
│   ├── __init__.py
│   ├── main.py               # 應用程式入口點
│   ├── config.py             # 配置管理
│   ├── schemas/              # Pydantic models
│   │   ├── __init__.py
│   │   ├── sql_output.py     # SQL 相關輸出模型
│   │   └── conversation.py   # 對話相關模型
│   ├── core/                 # 核心功能
│   │   ├── __init__.py
│   │   ├── agents/           # Pydantic AI Agents
│   │   │   ├── __init__.py
│   │   │   ├── dialogue.py   # 對話處理 Agent
│   │   │   └── sql_gen.py    # SQL 生成 Agent
│   │   ├── graph/            # Pydantic Graph 工作流程
│   │   │   ├── __init__.py
│   │   │   ├── state.py      # 工作流程狀態定義
│   │   │   ├── nodes.py      # 流程節點定義
│   │   │   └── workflow.py   # 主工作流程定義
│   │   ├── tools/            # Agent 工具函數
│   │   │   ├── __init__.py
│   │   │   ├── schema_tools.py  # 資料庫 schema 相關工具
│   │   │   ├── sql_validator.py # SQL 驗證工具 
│   │   │   └── sql_formatter.py # SQL 格式化工具
│   │   └── response_formatter.py  # 回應格式化
│   ├── db/                   # 資料庫相關
│   │   ├── __init__.py
│   │   ├── connection.py     # 資料庫連接管理
│   │   └── query_executor.py # SQL 查詢執行
│   └── ui/                   # 使用者介面 (Streamlit)
│       ├── __init__.py
│       ├── app.py            # Streamlit 主應用
│       ├── pages/            # Streamlit 頁面
│       └── components/       # UI 組件
├── tests/                    # 測試
│   ├── __init__.py
│   ├── conftest.py           # 測試配置
│   ├── test_agents.py        # Agent 相關測試
│   ├── test_graph.py         # 工作流程測試
│   ├── test_sql_gen.py       # SQL 生成測試
│   └── test_query_executor.py # 查詢執行測試
├── docs/                     # 文件
├── requirements.txt          # 依賴清單
├── README.md                 # 專案說明
├── PLANNING.md               # 本文件
└── TASK.md                   # 任務列表
```

## 開發準則

### 程式碼風格

- 遵循 PEP 8 標準
- 使用 Google 風格的 docstrings
- 為所有函數和類別添加型別提示
- 單檔案不超過 500 行程式碼
- 模組化設計，單一職責原則

### Pydantic AI 最佳實踐

- 使用 `deps_type` 和 `output_type` 實現型別安全的 Agent
- 使用裝飾器 `@agent.tool` 定義 Agent 工具函數
- 利用 `RunContext` 在工具函數中訪問依賴
- 為 Agent 實現適當的測試，使用 `TestModel` 模擬 LLM 回應

### 錯誤處理

- 使用適當的異常處理
- 詳細錯誤訊息並日誌記錄
- 用戶友好的錯誤回應
- 使用 `ModelRetry` 處理可重試的 Agent 錯誤

### 安全性考量

- SQL 注入防護
- 參數化查詢
- 資料庫認證安全存儲
- 最小權限原則

## 擴展考量

- 從 SQLite 遷移至 PostgreSQL
- 增加資料庫 schema 探索功能
- 支援複雜的 JOIN 和子查詢
- 查詢歷史記錄和管理功能
- Agent 行為分析和優化，利用 Pydantic Graph 可視化

## 測試策略

- 使用 Pydantic AI 的 `TestModel` 進行 Agent 單元測試
- 使用 `FunctionModel` 模擬特定 Agent 行為
- 整合測試驗證完整流程
- 工作流程圖測試和可視化
- SQL 生成測試與預期輸出比對
- 使用測試資料庫進行查詢執行測試

## 評估指標

- 查詢準確率：生成的 SQL 符合使用者意圖的比例
- 轉換時間：從自然語言到 SQL 的轉換時間
- Agent 決策品質：正確理解使用者意圖的比例
- 使用者滿意度：使用者回饋與評分
- 成功執行率：成功執行的查詢比例 