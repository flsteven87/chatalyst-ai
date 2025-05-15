"""
SQL 查詢執行引擎，負責安全地執行生成的 SQL 查詢和處理結果。
"""
import json
import time
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
import asyncio

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
import pandas as pd

from app.db.connection import get_db_session, DBConnection

# 設置日誌
logger = logging.getLogger(__name__)

class QueryExecutor:
    """
    SQL 查詢執行器，提供高級查詢操作。
    """
    
    @staticmethod
    async def execute_query(
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        save_history: bool = True,
        user_query: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str], float]:
        """
        執行 SQL 查詢並返回結果。

        Args:
            sql: SQL 查詢字串
            params: 參數化查詢的參數
            save_history: 是否保存查詢歷史
            user_query: 使用者的原始查詢，用於歷史記錄

        Returns:
            (查詢結果列表, 錯誤訊息, 執行時間)
        """
        start_time = time.time()
        error_message = None
        result_data = []
        
        # 預防空查詢
        if not sql or not sql.strip():
            return [], "查詢不能為空", 0.0
            
        try:
            async with get_db_session() as session:
                db_conn = DBConnection(session)
                result_data = await db_conn.execute_query(sql, params)
                
                # 保存查詢歷史
                if save_history:
                    await QueryExecutor._save_query_history(
                        session=session,
                        user_query=user_query or "",
                        sql=sql,
                        results=result_data,
                        execution_time=time.time() - start_time
                    )
                    
        except SQLAlchemyError as e:
            error_message = f"SQL 錯誤: {str(e)}"
            logger.error(f"SQL 執行錯誤: {e}", exc_info=True)
        except Exception as e:
            error_message = f"執行錯誤: {str(e)}"
            logger.error(f"查詢執行時發生未預期錯誤: {e}", exc_info=True)
        
        execution_time = time.time() - start_time
        return result_data, error_message, execution_time
    
    @staticmethod
    async def _save_query_history(
        session,
        user_query: str,
        sql: str,
        results: List[Dict[str, Any]],
        execution_time: float,
        error_message: Optional[str] = None
    ) -> None:
        """
        保存查詢歷史記錄。
        使用原始 SQL 查詢來保存歷史記錄，而不是 ORM 模型。

        Args:
            session: 資料庫會話
            user_query: 使用者的原始查詢
            sql: 執行的 SQL 查詢
            results: 查詢結果
            execution_time: 執行時間
            error_message: 如果有錯誤，則為錯誤訊息
        """
        try:
            # 檢查歷史表是否存在，如果不存在則創建
            await QueryExecutor._ensure_history_tables(session)
            
            # 插入查詢歷史記錄
            query_history_insert = text("""
                INSERT INTO query_history 
                (user_query, generated_sql, execution_time, error_message, created_at)
                VALUES (:user_query, :generated_sql, :execution_time, :error_message, datetime('now'))
                RETURNING id
            """)
            
            result = await session.execute(
                query_history_insert,
                {
                    "user_query": user_query,
                    "generated_sql": sql,
                    "execution_time": execution_time,
                    "error_message": error_message
                }
            )
            query_id = result.scalar_one()
            
            # 如果有結果且沒有錯誤，則保存結果
            if results and not error_message:
                result_json = json.dumps(results, ensure_ascii=False, default=str)
                
                result_insert = text("""
                    INSERT INTO query_results 
                    (query_id, result_data, row_count, created_at)
                    VALUES (:query_id, :result_data, :row_count, datetime('now'))
                """)
                
                await session.execute(
                    result_insert,
                    {
                        "query_id": query_id,
                        "result_data": result_json,
                        "row_count": len(results)
                    }
                )
            
            await session.commit()
            
        except Exception as e:
            logger.error(f"保存查詢歷史時出錯: {e}", exc_info=True)
            await session.rollback()
    
    @staticmethod
    async def _ensure_history_tables(session):
        """
        確保查詢歷史相關的表格存在，如果不存在則創建。
        
        Args:
            session: 資料庫會話
        """
        try:
            # 創建查詢歷史表
            create_history_table = text("""
                CREATE TABLE IF NOT EXISTS query_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_query TEXT NOT NULL,
                    generated_sql TEXT NOT NULL,
                    execution_time REAL,
                    error_message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 創建查詢結果表
            create_results_table = text("""
                CREATE TABLE IF NOT EXISTS query_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_id INTEGER NOT NULL,
                    result_data TEXT,
                    row_count INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (query_id) REFERENCES query_history (id) ON DELETE CASCADE
                )
            """)
            
            await session.execute(create_history_table)
            await session.execute(create_results_table)
            await session.commit()
            
        except Exception as e:
            logger.error(f"創建查詢歷史表時出錯: {e}", exc_info=True)
            await session.rollback()
    
    @staticmethod
    async def get_query_history(limit: int = 10) -> List[Dict[str, Any]]:
        """
        獲取最近的查詢歷史。

        Args:
            limit: 返回的歷史記錄數量

        Returns:
            查詢歷史記錄列表
        """
        try:
            async with get_db_session() as session:
                # 確保表格存在
                await QueryExecutor._ensure_history_tables(session)
                
                # 查詢歷史記錄
                query = text("""
                    SELECT h.id, h.user_query, h.generated_sql, h.execution_time, 
                           h.error_message, h.created_at, r.result_data
                    FROM query_history h
                    LEFT JOIN query_results r ON h.id = r.query_id
                    ORDER BY h.created_at DESC
                    LIMIT :limit
                """)
                
                result = await session.execute(query, {"limit": limit})
                records = result.fetchall()
                
                history_list = []
                for record in records:
                    history_data = {
                        "id": record.id,
                        "user_query": record.user_query,
                        "generated_sql": record.generated_sql,
                        "execution_time": record.execution_time,
                        "error_message": record.error_message,
                        "created_at": record.created_at,
                        "results": []
                    }
                    
                    # 處理結果數據
                    if record.result_data:
                        try:
                            result_json = json.loads(record.result_data)
                            history_data["results"] = result_json
                        except json.JSONDecodeError:
                            history_data["results"] = []
                    
                    history_list.append(history_data)
                
                return history_list
                
        except Exception as e:
            logger.error(f"獲取查詢歷史時出錯: {e}", exc_info=True)
            return []
            
    @staticmethod
    async def format_results_as_dataframe(results: List[Dict[str, Any]]) -> Optional[pd.DataFrame]:
        """
        將查詢結果格式化為 Pandas DataFrame。

        Args:
            results: 查詢結果列表

        Returns:
            格式化的 DataFrame 或 None (如果結果為空)
        """
        if not results:
            return None
            
        try:
            return pd.DataFrame(results)
        except Exception as e:
            logger.error(f"轉換結果為 DataFrame 時出錯: {e}", exc_info=True)
            return None 