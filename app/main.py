"""
ChataLyst AI 主應用程式入口點，用於初始化資料庫連接並提供核心功能。
"""
import asyncio
import logging
import os
from pathlib import Path

from app.config import DATA_DIR, DEBUG
from app.db.connection import init_db

# 設置日誌
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

async def initialize_application():
    """
    初始化應用程式，設置資料庫連接和其他必要的組件。
    """
    logger.info("正在初始化 ChataLyst AI 應用程式...")
    
    # 確保資料目錄存在
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # 確保 SQLite 資料庫目錄存在
    db_path = Path(os.getenv("SQLITE_DB_PATH", str(DATA_DIR / "chatalyst.db")))
    db_dir = db_path.parent
    os.makedirs(db_dir, exist_ok=True)
    
    # 初始化資料庫連接
    try:
        logger.info("正在初始化資料庫連接...")
        await init_db()
        logger.info("資料庫連接初始化完成")
    except Exception as e:
        logger.error(f"資料庫連接初始化失敗: {e}", exc_info=True)
        raise
    
    logger.info("ChataLyst AI 應用程式初始化完成")
    return True

def run_initialization():
    """
    運行初始化過程。
    這是一個同步函數，可以從任何地方調用。
    """
    asyncio.run(initialize_application())

if __name__ == "__main__":
    """
    直接運行此腳本時，執行初始化過程。
    """
    run_initialization() 