"""
配置管理模組，用於處理環境變數和應用程式設定
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 應用程式路徑
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# 確保資料目錄存在
os.makedirs(DATA_DIR, exist_ok=True)

# 應用程式設定
APP_ENV = os.getenv("APP_ENV", "development")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# 資料庫設定
DB_TYPE = os.getenv("DB_TYPE", "sqlite")
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", str(DATA_DIR / "chatalyst.db"))

# PostgreSQL 設定
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "")
PG_DB = os.getenv("PG_DB", "chatalyst")

# AI 模型設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "pydantic-ai")
AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.1"))

# 資料庫連接字串
def get_db_url() -> str:
    """獲取資料庫連接字串"""
    if DB_TYPE == "postgresql":
        return f"postgresql+psycopg://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"
    else:
        return f"sqlite+aiosqlite:///{SQLITE_DB_PATH}" 