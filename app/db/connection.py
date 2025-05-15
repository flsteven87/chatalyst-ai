"""
資料庫連接管理模組，負責建立和管理資料庫連接。
提供抽象層以支援 SQLite 和 PostgreSQL 資料庫。
"""
import asyncio
import logging
from typing import AsyncGenerator, Dict, Optional, Any
from contextlib import asynccontextmanager

import sqlalchemy
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy import inspect

from app.config import get_db_url, DEBUG

# 設置日誌
logger = logging.getLogger(__name__)

# 建立異步引擎
engine = create_async_engine(
    get_db_url(),
    echo=DEBUG,  # 在開發模式下顯示 SQL 查詢
)

# 建立異步 session 工廠
async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    """
    初始化資料庫連接。
    在應用程式啟動時調用。
    """
    async with engine.begin() as conn:
        # 檢查連接是否正常
        await conn.execute(sqlalchemy.text("SELECT 1"))
    
    logger.info("資料庫連接初始化完成")


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    提供資料庫 session 的上下文管理器。
    使用 async with 語法獲取 session。
    
    範例:
        async with get_db_session() as session:
            result = await session.execute(query)
    """
    session = async_session_factory()
    try:
        yield session
    finally:
        await session.close()


class DBConnection:
    """
    資料庫連接類，提供資料庫操作的抽象層。
    這個類可以被用來作為 Agent 的依賴注入。
    """
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> list:
        """
        執行 SQL 查詢並返回結果。
        
        Args:
            query: SQL 查詢字串
            params: 查詢參數字典
            
        Returns:
            查詢結果列表
        """
        try:
            params = params or {}
            # 使用 SQLAlchemy 的參數化查詢防止 SQL 注入
            stmt = sqlalchemy.text(query)
            result = await self.session.execute(stmt, params)
            return [dict(row._mapping) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"查詢執行錯誤: {e}")
            await self.session.rollback()
            raise
    
    async def get_schema_info(self) -> Dict[str, Any]:
        """
        獲取資料庫 schema 信息。
        使用 SQLAlchemy 的 inspect 來獲取資料庫表和列的信息。
        
        Returns:
            包含表格和列信息的字典
        """
        schema_info = {
            "tables": {}
        }
        
        try:
            # 使用 SQLAlchemy 的 inspect 來獲取資料庫 schema 信息
            inspector = inspect(engine)
            
            # 獲取所有表名
            table_names = await asyncio.to_thread(inspector.get_table_names)
            
            # 獲取每個表的詳細信息
            for table_name in table_names:
                # 獲取表的列信息
                columns = await asyncio.to_thread(inspector.get_columns, table_name)
                primary_keys = await asyncio.to_thread(inspector.get_pk_constraint, table_name)
                foreign_keys = await asyncio.to_thread(inspector.get_foreign_keys, table_name)
                
                schema_info["tables"][table_name] = {
                    "columns": {
                        col["name"]: {
                            "type": str(col["type"]),
                            "nullable": col.get("nullable", True),
                            "primary_key": col["name"] in primary_keys.get("constrained_columns", []),
                            "foreign_keys": []
                        }
                        for col in columns
                    },
                    "foreign_keys": foreign_keys
                }
                
                # 處理外鍵信息
                for fk in foreign_keys:
                    for col_name in fk.get("constrained_columns", []):
                        if col_name in schema_info["tables"][table_name]["columns"]:
                            target = f"{fk.get('referred_table')}.{fk.get('referred_columns')[0]}"
                            schema_info["tables"][table_name]["columns"][col_name]["foreign_keys"].append(target)
            
        except Exception as e:
            logger.error(f"獲取數據庫 schema 時出錯: {e}", exc_info=True)
            
        return schema_info 