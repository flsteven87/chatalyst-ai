"""
SQLite 到 PostgreSQL 資料遷移腳本。
此腳本用於將 SQLite 資料庫中的資料遷移到 PostgreSQL 資料庫。
"""
import asyncio
import logging
import os
from typing import Dict, Any, List
import sqlite3
from pathlib import Path
import glob

import psycopg
from psycopg.rows import dict_row
from sqlalchemy import create_engine, text, MetaData, Table, Column, inspect
from sqlalchemy.engine import Engine

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """資料庫遷移工具類"""
    
    def __init__(
        self,
        sqlite_path: str,
        pg_host: str,
        pg_port: int,
        pg_database: str,
        pg_user: str,
        pg_password: str
    ):
        self.sqlite_path = sqlite_path
        self.pg_dsn = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
        self.sqlite_conn = None
        self.pg_conn = None
        
    async def connect(self) -> None:
        """建立資料庫連接"""
        try:
            # SQLite 連接
            logger.info(f"連接到 SQLite 資料庫: {self.sqlite_path}")
            self.sqlite_conn = sqlite3.connect(self.sqlite_path)
            self.sqlite_conn.row_factory = sqlite3.Row
            
            # PostgreSQL 連接
            logger.info(f"連接到 PostgreSQL 資料庫: {self.pg_dsn}")
            self.pg_conn = await psycopg.AsyncConnection.connect(
                self.pg_dsn,
                row_factory=dict_row
            )
            logger.info("資料庫連接建立成功")
        except Exception as e:
            logger.error(f"資料庫連接失敗: {e}")
            raise
            
    async def close(self) -> None:
        """關閉資料庫連接"""
        if self.sqlite_conn:
            self.sqlite_conn.close()
        if self.pg_conn:
            await self.pg_conn.close()
            
    def get_sqlite_tables(self) -> List[str]:
        """獲取 SQLite 資料庫中的所有表格名稱"""
        cursor = self.sqlite_conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"找到以下表格: {tables}")
        return tables
        
    def get_sqlite_schema(self, table: str) -> List[Dict[str, Any]]:
        """獲取指定表格的結構信息"""
        cursor = self.sqlite_conn.cursor()
        cursor.execute(f"PRAGMA table_info({table})")
        schema = [dict(row) for row in cursor.fetchall()]
        logger.info(f"表格 {table} 的結構: {schema}")
        return schema
        
    def get_sqlite_data(self, table: str) -> List[Dict[str, Any]]:
        """獲取指定表格的所有資料"""
        cursor = self.sqlite_conn.cursor()
        cursor.execute(f"SELECT * FROM {table}")
        columns = [description[0] for description in cursor.description]
        data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        logger.info(f"從表格 {table} 讀取了 {len(data)} 筆記錄")
        return data
        
    async def create_pg_table(self, table: str, schema: List[Dict[str, Any]]) -> None:
        """在 PostgreSQL 中建立表格"""
        # 建立建表 SQL
        columns = []
        for col in schema:
            # 轉換 SQLite 類型到 PostgreSQL 類型
            pg_type = self._convert_type(col['type'])
            null_str = "NULL" if col['notnull'] == 0 else "NOT NULL"
            pk_str = "PRIMARY KEY" if col['pk'] == 1 else ""
            columns.append(f"{col['name']} {pg_type} {null_str} {pk_str}")
            
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {table} (
            {', '.join(columns)}
        )
        """
        
        async with self.pg_conn.cursor() as cur:
            await cur.execute(create_sql)
        await self.pg_conn.commit()
        logger.info(f"表格 {table} 建立成功")
        
    async def migrate_table_data(self, table: str, data: List[Dict[str, Any]]) -> None:
        """遷移表格資料"""
        if not data:
            logger.info(f"表格 {table} 沒有資料需要遷移")
            return
            
        # 準備插入語句
        columns = data[0].keys()
        placeholders = [f"%({col})s" for col in columns]
        insert_sql = f"""
        INSERT INTO {table} ({', '.join(columns)})
        VALUES ({', '.join(placeholders)})
        """
        
        async with self.pg_conn.cursor() as cur:
            await cur.executemany(insert_sql, data)
        await self.pg_conn.commit()
        logger.info(f"表格 {table} 資料遷移成功，共 {len(data)} 筆記錄")
        
    def _convert_type(self, sqlite_type: str) -> str:
        """轉換 SQLite 資料類型到 PostgreSQL 資料類型"""
        type_mapping = {
            'INTEGER': 'INTEGER',
            'REAL': 'DOUBLE PRECISION',
            'TEXT': 'TEXT',
            'BLOB': 'BYTEA',
            'BOOLEAN': 'BOOLEAN',
            'DATETIME': 'TIMESTAMP',
            'DATE': 'DATE',
            'TIME': 'TIME',
        }
        
        # 將類型轉換為大寫並移除括號內容
        base_type = sqlite_type.upper().split('(')[0]
        return type_mapping.get(base_type, 'TEXT')

async def main():
    """主要遷移流程"""
    # 搜尋 data 目錄下的所有 SQLite 資料庫檔案
    data_dir = Path("/app/data")
    sqlite_files = glob.glob(str(data_dir / "*.sqlite"))
    
    if not sqlite_files:
        logger.warning("在 data 目錄下沒有找到 .sqlite 檔案")
        return
        
    logger.info(f"找到以下 SQLite 檔案: {sqlite_files}")
    
    # 遷移每個找到的資料庫
    for sqlite_file in sqlite_files:
        logger.info(f"開始遷移資料庫: {sqlite_file}")
        migrator = DatabaseMigrator(
            sqlite_path=sqlite_file,
            pg_host=os.getenv('PG_HOST', 'postgres'),
            pg_port=int(os.getenv('PG_PORT', 5432)),
            pg_database=os.getenv('PG_DATABASE', 'chatalyst'),
            pg_user=os.getenv('PG_USER', 'postgres'),
            pg_password=os.getenv('PG_PASSWORD', 'postgres')
        )
        
        try:
            await migrator.connect()
            
            # 獲取所有表格
            tables = migrator.get_sqlite_tables()
            
            for table in tables:
                # 獲取表格結構
                schema = migrator.get_sqlite_schema(table)
                
                # 在 PostgreSQL 中建立表格
                await migrator.create_pg_table(table, schema)
                
                # 獲取並遷移資料
                data = migrator.get_sqlite_data(table)
                await migrator.migrate_table_data(table, data)
                
        except Exception as e:
            logger.error(f"遷移過程中發生錯誤: {e}")
            raise
        finally:
            await migrator.close()
            
if __name__ == "__main__":
    asyncio.run(main()) 