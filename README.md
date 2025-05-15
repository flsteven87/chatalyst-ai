# ChataLyst AI

ChataLyst AI 是一個自然語言驅動的 SQL 查詢生成與執行系統，讓使用者能夠通過對話方式與資料庫互動。

## 專案概述

本專案旨在建立一個橋接自然語言與資料庫查詢的平台，使非技術使用者能夠通過簡單的問題獲取資料洞察。透過整合 LLM Agent 技術，ChataLyst AI 可以理解使用者的意圖，生成相應的 SQL 查詢，執行這些查詢，並以易於理解的方式傳達結果。

### 主要功能

- 🤖 **LLM Agent 對話**：以 Agent 為基礎處理自然語言輸入
- 🔍 **SQL 生成**：透過 Agent 生成精確的 SQL 查詢
- 🛢️ **資料庫支援**：連接到 SQLite (POC) 和 PostgreSQL (未來)
- 📊 **結果可視化**：以圖表和表格呈現查詢結果
- 💬 **對話式介面**：維持上下文感知的對話流程
- 📈 **Agent 行為監控**：使用 LangGraph 追蹤與分析 Agent 行為

## 技術堆疊

- **後端**: Python 3.12, FastAPI (視需求), SQLAlchemy
- **資料庫**: SQLite (POC 階段), PostgreSQL (未來)
- **AI/ML**: Pydantic AI, LangGraph
- **前端**: Streamlit
- **工具**: Pytest, Black, Ruff

## 快速開始

### 前置條件

- Python 3.12
- SQLite

### 安裝

1. 克隆專案儲存庫
   ```bash
   git clone https://github.com/yourusername/chatalyst-ai.git
   cd chatalyst-ai
   ```

2. 建立虛擬環境並安裝依賴
   ```bash
   python -m venv venv
   source venv/bin/activate  # 在 Windows 上使用 venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. 配置環境變數
   ```bash
   cp .env.example .env
   # 編輯 .env 檔案設定您的資料庫和 API 密鑰
   ```

### 運行

#### Streamlit 介面
```bash
streamlit run app/ui/app.py
```

## 開發

關於專案詳細的開發計劃和架構，請參閱:
- [專案規劃](PLANNING.md)
- [任務清單](TASK.md)

## 測試

執行單元測試:
```bash
pytest
```

## 貢獻

歡迎貢獻！請參閱 [CONTRIBUTING.md](CONTRIBUTING.md) 了解詳情。

## 授權

本專案採用 [MIT 授權](LICENSE)。
