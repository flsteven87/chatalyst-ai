"""
Schema management module for Vanna AI training.
"""
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class SchemaManager:
    """
    Manages database schema information and DDL generation for Vanna AI training.
    """
    
    def __init__(self, db_connector):
        """
        Initialize schema manager.
        
        Args:
            db_connector: Database connector instance
        """
        self.db_connector = db_connector
        self._schema_cache = None
    
    def get_schema_info(self) -> Dict:
        """
        Get cached schema information.
        
        Returns:
            dict: Schema information organized by table name
        """
        if self._schema_cache is None:
            self._schema_cache = self.db_connector.get_schema_info()
        return self._schema_cache
    
    def generate_enhanced_ddl(self, table_name: str, columns: List[Dict]) -> str:
        """
        Generate enhanced DDL with detailed column information and constraints.
        
        Args:
            table_name: Name of the table
            columns: List of column dictionaries with column details
            
        Returns:
            str: Enhanced DDL statement with comments
        """
        ddl = f"-- Table: {table_name}\n"
        ddl += f"CREATE TABLE {table_name} (\n"
        column_defs = []
        
        for column in columns:
            column_name = column.get('column_name', '')
            data_type = column.get('data_type', 'text')
            is_nullable = column.get('is_nullable', 'YES').upper()
            column_default = column.get('column_default', '')
            
            nullable_str = "NULL" if is_nullable == "YES" else "NOT NULL"
            
            # Normalize data types
            data_type = self._normalize_data_type(data_type, column)
            
            column_def = f"    {column_name} {data_type} {nullable_str}"
            
            # Add default value if exists
            if column_default and column_default != 'NULL':
                column_def += f" DEFAULT {column_default}"
            
            # Add comments for important columns
            column_def += self._get_column_comment(column_name, data_type)
            
            column_defs.append(column_def)
        
        ddl += ",\n".join(column_defs)
        ddl += "\n);"
        
        # Add table-specific notes
        ddl += self._get_table_notes(table_name)
        
        return ddl
    
    def generate_table_documentation(self, table_name: str, columns: List[Dict]) -> str:
        """
        Generate detailed table documentation for training.
        
        Args:
            table_name: Name of the table
            columns: List of column dictionaries
            
        Returns:
            str: Table documentation string
        """
        doc = f"Table: {table_name}\n"
        doc += f"Columns: {', '.join([col['column_name'] for col in columns])}\n"
        
        # Add specific documentation for key tables
        table_docs = {
            'experiments': self._get_experiments_doc(),
            'shops': self._get_shops_doc(),
            'storewide_views': self._get_storewide_views_doc()
        }
        
        if table_name in table_docs:
            doc += table_docs[table_name]
        
        return doc
    
    def get_all_column_names(self) -> set:
        """
        Get all column names from all tables.
        
        Returns:
            set: Set of all column names
        """
        schema_info = self.get_schema_info()
        all_columns = set()
        
        for table_name, columns in schema_info.items():
            for col in columns:
                all_columns.add(col['column_name'])
        
        return all_columns
    
    def _normalize_data_type(self, data_type: str, column: Dict) -> str:
        """Normalize PostgreSQL data types for better readability."""
        if data_type == 'character varying':
            max_length = column.get('character_maximum_length')
            return f"VARCHAR({max_length})" if max_length else "VARCHAR"
        elif data_type == 'timestamp with time zone':
            return "TIMESTAMPTZ"
        elif data_type == 'timestamp without time zone':
            return "TIMESTAMP"
        return data_type
    
    def _get_column_comment(self, column_name: str, data_type: str) -> str:
        """Get appropriate comment for column."""
        # Identify key columns for special handling
        if column_name in ['id', 'experiment_id']:
            return f"{column_name}: Primary/Foreign key identifier"
        elif column_name == 'store_name':
            return f"{column_name}: Store identification field"
        elif 'jsonb' in data_type.lower():
            return " -- JSONB column for flexible configuration"
        return ""
    
    def _get_table_notes(self, table_name: str) -> str:
        """Get table-specific notes."""
        # Special table descriptions
        special_descriptions = {
            'experiments': "\n-- Main experiments table with unified ID system\n-- Use experiments.id for all PostgreSQL table joins\n-- experiment_goal: Defines calculation metric (conversion_rate, average_order_value, revenue_per_visitor)",
            'experiment_daily_metrics': "\n-- Precomputed daily metrics for fast analytics\n-- IMPORTANT: Uses is_control_group for control group identification\n-- Join: experiments.id = experiment_daily_metrics.experiment_id\n-- Contains: views, orders, sales_revenue for uplift calculations\n-- PRIORITY: Always use this table instead of raw event tables",
            'experiment_groups': "\n-- Individual test groups within experiments\n-- IMPORTANT: Uses is_control_group (unified with experiment_daily_metrics)\n-- Join: experiments.id = experiment_groups.experiment_id"
        }
        return special_descriptions.get(table_name, "")
    
    def _get_experiments_doc(self) -> str:
        """Get experiments table documentation."""
        return """
Key columns:
- id: Primary key for PostgreSQL joins
- store_name: Shopify store domain
- experiment_name: Human readable experiment name
- experiment_type: Type of test (price-test, url-redirect-test, etc.)
- status: Current state (Active, Paused, Completed, Draft)
- type_metadata: JSONB with experiment-specific configuration
- filter_conditions: JSONB with trigger and filter rules
"""
    
    def _get_shops_doc(self) -> str:
        """Get shops table documentation."""
        return """
Key columns:
- shopify_domain: Primary store identifier
- name: Store display name
- country, province, city: Geographic information
- pricing_plan: Current subscription plan
- views: JSONB with monthly view statistics
- apps: JSONB with installed app information
"""
    
    def _get_storewide_views_doc(self) -> str:
        """Get storewide_views table documentation."""
        return """
Key columns:
- experiment_id: Links to experiments.id (NOT experiments.id)
- session_id: User session identifier
- device_type: mobile, desktop, tablet
- search_params: JSONB with UTM and tracking parameters
""" 