"""
PostgreSQL database connector for chatalyst_ai.
"""
import logging
import psycopg
import pandas as pd
# Updated import: Use DATABASE_CONFIG directly from settings
from config.settings import DATABASE_CONFIG 

logger = logging.getLogger(__name__)

class PostgreSQLConnector:
    """
    PostgreSQL database connector class for handling database operations.
    """
    def __init__(self, config_kwargs: dict | None = None):
        """
        Initialize the connector with configuration.
        
        Args:
            config_kwargs (dict, optional): Database connection keyword arguments. 
                                       Defaults to DATABASE_CONFIG from settings.py.
        """
        # Prioritize passed config, then DATABASE_CONFIG from settings
        if config_kwargs:
            self.config_kwargs = config_kwargs
        else:
            self.config_kwargs = DATABASE_CONFIG # Use DATABASE_CONFIG directly
            
        self.connection = None
        # self.cursor = None # Cursor is typically method-local
    
    def connect(self) -> bool:
        """
        Establish connection to the PostgreSQL database.
        
        Returns:
            bool: True if connection successful, False otherwise.
        """
        try:
            conn_kwargs = self.config_kwargs.copy()
            
            # psycopg v3 expects dbname, ensure it's present from Pydantic model or legacy dict
            if 'database' in conn_kwargs and 'dbname' not in conn_kwargs:
                conn_kwargs['dbname'] = conn_kwargs.pop('database')
            
            if 'port' in conn_kwargs and isinstance(conn_kwargs['port'], str):
                conn_kwargs['port'] = int(conn_kwargs['port'])
            
            logger.info(f"Attempting to connect to PostgreSQL with: { {k: v for k, v in conn_kwargs.items() if k != 'password'} }") # Log without password
            self.connection = psycopg.connect(**conn_kwargs)
            # self.connection.row_factory = psycopg.rows.dict_row # dict_row is default for cursor with execute
            logger.info("Successfully connected to PostgreSQL database.")
            return True
        except psycopg.Error as e: # Catch psycopg specific errors
            logger.error(f"Error connecting to PostgreSQL database: {e}")
            logger.debug(f"Connection arguments used (excluding password): {{k: v for k, v in conn_kwargs.items() if k != 'password'}}")
            self.connection = None # Ensure connection is None on failure
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to PostgreSQL database: {e}")
            self.connection = None
            return False
    
    def disconnect(self):
        """
        Close the database connection.
        """
        if self.connection and not self.connection.closed:
            self.connection.close()
            logger.info("Disconnected from PostgreSQL database.")
        self.connection = None
    
    def execute_query(self, query: str, params: tuple | dict | None = None) -> pd.DataFrame | None:
        """
        Execute a SQL query and return results as a pandas DataFrame.
        
        Args:
            query (str): SQL query to execute.
            params (tuple or dict, optional): Parameters for the query. Defaults to None.
            
        Returns:
            pandas.DataFrame: Query results as DataFrame or None if an error occurs.
        """
        try:
            if not self.connection or self.connection.closed:
                logger.info("Connection is not active. Attempting to reconnect.")
                if not self.connect():
                    logger.error("Failed to establish database connection for query execution.")
                    return None
            
            # Ensure self.connection is not None after attempting to connect
            if not self.connection:
                 logger.error("Database connection is None even after connect attempt.")
                 return None

            with self.connection.cursor(row_factory=psycopg.rows.dict_row) as cur:
                logger.debug(f"Executing query: {query} with params: {params}")
                cur.execute(query, params)
                
                # Check if query is a SELECT or similar that returns rows
                if cur.description:
                    rows = cur.fetchall()
                    df = pd.DataFrame(rows) if rows else pd.DataFrame()
                    logger.info(f"Query executed successfully, returned {len(df)} rows.")
                    return df
                else:
                    # For non-SELECT queries (INSERT, UPDATE, DELETE), commit changes
                    self.connection.commit()
                    logger.info(f"Non-SELECT query executed successfully. Rows affected: {cur.rowcount}")
                    # Return a status or row count for non-SELECT might be useful
                    return pd.DataFrame([{"status": "Query executed successfully", "rows_affected": cur.rowcount}])
                
        except psycopg.Error as e: # Catch psycopg specific errors
            logger.error(f"Database error executing query: {query} - {e}")
            if self.connection and not self.connection.closed:
                try:
                    self.connection.rollback()
                    logger.info("Transaction rolled back due to error.")
                except psycopg.Error as rb_e:
                    logger.error(f"Error during rollback: {rb_e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error executing query: {query} - {e}")
            return None
    
    def get_schema_info(self) -> dict:
        """
        Get database schema information (tables, columns, data types, nullability).
        
        Returns:
            dict: Schema information organized by table_name. 
                  Each table has a list of column_info dicts.
                  Returns empty dict if an error occurs or no tables found.
        """
        schema_info = {}
        tables_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name;
        """
        try:
            tables_df = self.execute_query(tables_query)
            
            if tables_df is None or tables_df.empty:
                logger.warning("No tables found in 'public' schema or error fetching tables.")
                return {}

            for _, row in tables_df.iterrows():
                table_name = row['table_name']
                columns_query = """
                SELECT column_name, data_type, udt_name, is_nullable,
                       column_default, character_maximum_length, numeric_precision, numeric_scale
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position;
                """
                columns_df = self.execute_query(columns_query, (table_name,))
                
                if columns_df is not None and not columns_df.empty:
                    schema_info[table_name] = columns_df.to_dict('records')
                else:
                    logger.warning(f"No columns found for table '{table_name}' or error fetching columns.")
                    schema_info[table_name] = [] # Add empty list if no columns
            
            logger.info(f"Successfully retrieved schema for {len(schema_info)} tables.")
            return schema_info
        except Exception as e:
            logger.error(f"Error getting schema info: {e}")
            return {} 