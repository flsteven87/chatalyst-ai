"""
SQL validation module for Vanna AI generated queries.
"""
import logging
from typing import Tuple, Set

logger = logging.getLogger(__name__)


class SQLValidator:
    """
    Validates generated SQL queries against database schema.
    """
    
    def __init__(self, schema_manager):
        """
        Initialize SQL validator.
        
        Args:
            schema_manager: SchemaManager instance
        """
        self.schema_manager = schema_manager
        self._invalid_patterns = {
            'conversion_rate',  # Common hallucination
            'revenue',          # Often assumed but may not exist
            'clicks',           # Common assumption
            'impressions',      # Common assumption
            'created_by',       # User assumption
            'user_id',          # User assumption
            'tags',             # Classification assumption
            'priority',         # Ordering assumption
            'budget',           # Financial assumption
            'success_rate',     # Metric assumption
            'participant_count' # Count assumption
        }
    
    def validate_sql(self, sql: str, question: str) -> Tuple[bool, str]:
        """
        Validate generated SQL against known schema.
        
        Args:
            sql: Generated SQL query
            question: Original question
            
        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            if not self._is_basic_sql_valid(sql):
                return False, "Invalid SQL structure"
            
            if self._contains_error_message(sql):
                return False, "AI returned error message instead of SQL"
            
            validation_error = self._check_column_validity(sql)
            if validation_error:
                return False, validation_error
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating SQL: {e}")
            return True, None  # Allow if validation fails
    
    def _is_basic_sql_valid(self, sql: str) -> bool:
        """Check basic SQL structure."""
        if not sql or not isinstance(sql, str):
            return False
        
        sql_lower = sql.lower().strip()
        return any(keyword in sql_lower for keyword in ['select', 'insert', 'update', 'delete'])
    
    def _contains_error_message(self, sql: str) -> bool:
        """Check if SQL contains error messages."""
        sql_lower = sql.lower().strip()
        error_indicators = [
            "無法根據現有資料庫結構生成此查詢",
            "sorry", "error", "unable", "cannot", "無法", "失敗"
        ]
        return any(indicator in sql_lower for indicator in error_indicators)
    
    def _check_column_validity(self, sql: str) -> str:
        """
        Check if SQL contains invalid column names.
        
        Returns:
            str: Error message if invalid columns found, None otherwise
        """
        sql_lower = sql.lower()
        
        # For complex CTE queries, use more lenient validation
        if 'with ' in sql_lower and 'as (' in sql_lower:
            return self._validate_cte_query(sql_lower)
        
        # Get all valid column names
        all_columns = self.schema_manager.get_all_column_names()
        all_columns_lower = {col.lower() for col in all_columns}
        
        # Extract aliases from SELECT clause to avoid false positives
        select_aliases = self._extract_select_aliases(sql)
        
        # Check for known invalid patterns, but exclude aliases
        for pattern in self._invalid_patterns:
            if pattern in sql_lower and pattern not in all_columns_lower:
                # Check if this is an alias in SELECT clause
                if pattern not in select_aliases:
                    # Only flag if it appears in contexts other than SELECT alias or ORDER BY
                    if self._is_invalid_column_usage(sql_lower, pattern, select_aliases):
                        return f"Column '{pattern}' does not exist in schema"
        
        return None
    
    def _validate_cte_query(self, sql_lower: str) -> str:
        """
        Validate CTE queries with more lenient rules.
        
        Args:
            sql_lower: Lowercase SQL string
            
        Returns:
            str: Error message if invalid, None otherwise
        """
        # For CTE queries, only check for obvious invalid patterns
        # that are not likely to be aliases or calculated fields
        strict_invalid_patterns = {
            'clicks',           # Definitely doesn't exist
            'impressions',      # Definitely doesn't exist
            'ctr',             # Definitely doesn't exist
            'roas',            # Definitely doesn't exist
            'created_by',      # User assumption
            'user_id',         # User assumption
            'tags',            # Classification assumption
            'priority',        # Ordering assumption
            'budget',          # Financial assumption
            'participant_count' # Count assumption
        }
        
        # Get all valid column names
        all_columns = self.schema_manager.get_all_column_names()
        all_columns_lower = {col.lower() for col in all_columns}
        
        # Only check for strict invalid patterns
        for pattern in strict_invalid_patterns:
            if pattern in sql_lower and pattern not in all_columns_lower:
                # Check if it's used in a context that suggests it's a column reference
                # rather than an alias
                if self._is_likely_column_reference(sql_lower, pattern):
                    return f"Column '{pattern}' does not exist in schema"
        
        return None
    
    def _is_likely_column_reference(self, sql_lower: str, pattern: str) -> bool:
        """
        Check if pattern is likely a column reference rather than an alias.
        
        Args:
            sql_lower: Lowercase SQL string
            pattern: Pattern to check
            
        Returns:
            bool: True if likely a column reference
        """
        import re
        
        # Look for patterns like "table.column" or "WHERE column ="
        column_ref_patterns = [
            rf'\w+\.{pattern}\b',  # table.column
            rf'where\s+{pattern}\s*[=<>]',  # WHERE column =
            rf'and\s+{pattern}\s*[=<>]',    # AND column =
            rf'or\s+{pattern}\s*[=<>]',     # OR column =
            rf'on\s+\w+\.{pattern}\s*=',    # ON table.column =
        ]
        
        for regex_pattern in column_ref_patterns:
            if re.search(regex_pattern, sql_lower):
                return True
        
        return False
    
    def _extract_select_aliases(self, sql: str) -> set:
        """
        Extract aliases from SELECT clause.
        
        Args:
            sql: SQL query string
            
        Returns:
            set: Set of aliases found in SELECT clause
        """
        aliases = set()
        sql_lower = sql.lower()
        
        try:
            # Find SELECT clause
            select_start = sql_lower.find('select')
            from_start = sql_lower.find('from')
            
            if select_start != -1 and from_start != -1:
                select_clause = sql_lower[select_start + 6:from_start].strip()
                
                # Split by comma and look for 'as' keyword
                parts = select_clause.split(',')
                for part in parts:
                    part = part.strip()
                    if ' as ' in part:
                        alias = part.split(' as ')[-1].strip()
                        aliases.add(alias)
                    elif ' ' in part and not any(func in part for func in ['count', 'sum', 'avg', 'round', 'nullif']):
                        # Simple alias without 'as' keyword
                        words = part.split()
                        if len(words) >= 2:
                            aliases.add(words[-1])
        
        except Exception as e:
            logger.debug(f"Error extracting aliases: {e}")
        
        return aliases
    
    def _is_invalid_column_usage(self, sql_lower: str, pattern: str, select_aliases: set) -> bool:
        """
        Check if pattern usage is invalid (not as an alias or in ORDER BY).
        
        Args:
            sql_lower: Lowercase SQL string
            pattern: Pattern to check
            select_aliases: Set of SELECT aliases
            
        Returns:
            bool: True if usage is invalid
        """
        # If it's a SELECT alias, it's valid
        if pattern in select_aliases:
            return False
        
        # Check if it only appears in ORDER BY (which is valid for aliases)
        import re
        
        # Find all occurrences of the pattern
        pattern_positions = []
        start = 0
        while True:
            pos = sql_lower.find(pattern, start)
            if pos == -1:
                break
            pattern_positions.append(pos)
            start = pos + 1
        
        # Check if all occurrences are in valid contexts
        order_by_pos = sql_lower.find('order by')
        
        for pos in pattern_positions:
            # Check if this occurrence is in ORDER BY clause
            if order_by_pos != -1 and pos > order_by_pos:
                continue  # Valid usage in ORDER BY
            
            # Check if this occurrence is in SELECT clause as alias
            select_pos = sql_lower.find('select')
            from_pos = sql_lower.find('from')
            if select_pos != -1 and from_pos != -1 and select_pos < pos < from_pos:
                continue  # Valid usage in SELECT as alias
            
            # If we reach here, it's an invalid usage
            return True
        
        return False
    
    def get_column_suggestions(self, invalid_column: str) -> list:
        """
        Get suggestions for invalid column names.
        
        Args:
            invalid_column: The invalid column name
            
        Returns:
            list: List of suggested valid column names
        """
        all_columns = self.schema_manager.get_all_column_names()
        suggestions = []
        
        # Simple similarity matching
        invalid_lower = invalid_column.lower()
        for col in all_columns:
            if invalid_lower in col.lower() or col.lower() in invalid_lower:
                suggestions.append(col)
        
        return suggestions[:3]  # Return top 3 suggestions 