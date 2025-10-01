"""
SQL Executor Service

Executes validated SQL queries against the MySQL database.
Integrates with the existing app_state MySQL connection pool.
"""

import logging
import time
from typing import Optional, List, Dict, Any

from ..models.response_models import (
    SQLExecutionResult,
    SQLExecutionError,
    ExecutionConfig
)

logger = logging.getLogger(__name__)


class SQLExecutorService:
    """Service for executing SQL queries against MySQL database"""
    
    def __init__(self, config: Optional[ExecutionConfig] = None):
        """
        Initialize SQL Executor Service
        
        Args:
            config: Execution configuration, uses defaults if None
        """
        self.config = config or ExecutionConfig()
    
    def execute_sql(self, sql_query: str, app_state) -> SQLExecutionResult:
        """
        Execute SQL query against MySQL database
        
        Args:
            sql_query: Validated SQL query to execute
            app_state: Application state with MySQL connection
            
        Returns:
            SQLExecutionResult with data or error
        """
        start_time = time.time()
        connection = None
        cursor = None
        
        try:
            # Validate inputs
            if not sql_query or not sql_query.strip():
                return SQLExecutionResult(
                    success=False,
                    error="Empty SQL query provided"
                )
            
            if not app_state:
                return SQLExecutionResult(
                    success=False,
                    error="App state not provided"
                )
            
            # Get MySQL connection from app_state
            connection = app_state.get_mysql_connection()
            if not connection:
                return SQLExecutionResult(
                    success=False,
                    error="MySQL connection not available"
                )
            
            logger.debug(f"[SQL_EXECUTOR] Executing query: {sql_query[:100]}...")
            
            # Create cursor
            cursor = connection.cursor(dictionary=True)
            
            # Set query timeout if supported
            if hasattr(cursor, '_connection'):
                cursor._connection.autocommit = True
            
            # Execute the query
            logger.info("Starting SQL execution")
            cursor.execute(sql_query)
            logger.info("SQL execution completed")
            
            # Fetch results
            if cursor.description:
                # Query returns data (SELECT)
                rows = cursor.fetchall()
                
                # Apply row limit
                if len(rows) > self.config.max_rows:
                    logger.warning(f"[SQL_EXECUTOR] Result truncated to {self.config.max_rows} rows")
                    rows = rows[:self.config.max_rows]
                
                # Extract column information
                columns = [desc[0] for desc in cursor.description]
                data_types = self._extract_column_types(cursor.description)
                
                # Convert data for JSON serialization
                serializable_data = self._make_serializable(rows)
                
                execution_time_ms = (time.time() - start_time) * 1000
                
                return SQLExecutionResult(
                    success=True,
                    data=serializable_data,
                    row_count=len(rows),
                    execution_time_ms=execution_time_ms,
                    query_executed=sql_query,
                    columns=columns,
                    data_types=data_types
                )
            else:
                # Query doesn't return data (INSERT, UPDATE, DELETE)
                affected_rows = cursor.rowcount
                execution_time_ms = (time.time() - start_time) * 1000
                
                return SQLExecutionResult(
                    success=True,
                    data=[],
                    row_count=affected_rows,
                    execution_time_ms=execution_time_ms,
                    query_executed=sql_query,
                    columns=[],
                    data_types={}
                )
                
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            error_msg = f"SQL execution failed: {str(e)}"
            
            logger.error(f"[SQL_EXECUTOR] {error_msg} (after {execution_time_ms:.2f}ms)")
            
            return SQLExecutionResult(
                success=False,
                error=error_msg,
                execution_time_ms=execution_time_ms,
                query_executed=sql_query
            )
            
        finally:
            # Clean up resources
            try:
                if cursor:
                    cursor.close()
                if connection:
                    connection.close()
            except Exception as cleanup_error:
                logger.warning(f"[SQL_EXECUTOR] Cleanup error: {cleanup_error}")
    
    def execute_sql_with_context(self, sql_query: str, app_state, context: dict) -> SQLExecutionResult:
        """
        Execute SQL query with additional context information
        
        Args:
            sql_query: Validated SQL query to execute
            app_state: Application state with MySQL connection
            context: Additional context (session_id, user_info, etc.)
            
        Returns:
            SQLExecutionResult with data or error
        """
        try:
            # Log context information
            session_id = context.get('session_id', 'unknown')
            user_query = context.get('user_query', 'unknown')
            
            # Execute the query
            result = self.execute_sql(sql_query, app_state)
            
            return result
            
        except Exception as e:
            logger.error(f"[SQL_EXECUTOR] Context execution error: {e}")
            return SQLExecutionResult(
                success=False,
                error=f"Context execution error: {str(e)}",
                query_executed=sql_query
            )
    
    def _extract_column_types(self, description) -> Dict[str, str]:
        """
        Extract column data types from cursor description
        
        Args:
            description: Cursor description
            
        Returns:
            Dictionary mapping column names to data types
        """
        data_types = {}
        
        try:
            for desc in description:
                column_name = desc[0]
                type_code = desc[1]
                
                # Map MySQL type codes to readable names
                type_name = self._mysql_type_to_string(type_code)
                data_types[column_name] = type_name
                
        except Exception as e:
            logger.warning(f"[SQL_EXECUTOR] Error extracting column types: {e}")
        
        return data_types
    
    def _mysql_type_to_string(self, type_code) -> str:
        """
        Convert MySQL type code to string representation
        
        Args:
            type_code: MySQL type code
            
        Returns:
            String representation of the type
        """
        # Import mysql.connector.FieldType for type mapping
        try:
            import mysql.connector.FieldType as FieldType
            
            type_mapping = {
                FieldType.TINY: 'TINYINT',
                FieldType.SHORT: 'SMALLINT',
                FieldType.LONG: 'INT',
                FieldType.LONGLONG: 'BIGINT',
                FieldType.FLOAT: 'FLOAT',
                FieldType.DOUBLE: 'DOUBLE',
                FieldType.DECIMAL: 'DECIMAL',
                FieldType.DATE: 'DATE',
                FieldType.TIME: 'TIME',
                FieldType.DATETIME: 'DATETIME',
                FieldType.TIMESTAMP: 'TIMESTAMP',
                FieldType.STRING: 'VARCHAR',
                FieldType.VAR_STRING: 'VARCHAR',
                FieldType.BLOB: 'BLOB',
                FieldType.JSON: 'JSON'
            }
            
            return type_mapping.get(type_code, 'UNKNOWN')
            
        except ImportError:
            return 'UNKNOWN'
    
    def _make_serializable(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert data to JSON-serializable format
        
        Args:
            data: Raw data from database
            
        Returns:
            JSON-serializable data
        """
        serializable_data = []
        
        for row in data:
            serializable_row = {}
            for key, value in row.items():
                # Convert non-serializable types
                if value is None:
                    serializable_row[key] = None
                elif isinstance(value, (str, int, float, bool)):
                    serializable_row[key] = value
                elif hasattr(value, 'isoformat'):  # datetime objects
                    serializable_row[key] = value.isoformat()
                elif isinstance(value, bytes):
                    # Convert bytes to string (for BLOB fields)
                    try:
                        serializable_row[key] = value.decode('utf-8')
                    except UnicodeDecodeError:
                        serializable_row[key] = str(value)
                else:
                    # Convert other types to string
                    serializable_row[key] = str(value)
            
            serializable_data.append(serializable_row)
        
        return serializable_data
    
    def test_connection(self, app_state) -> dict:
        """
        Test database connection
        
        Args:
            app_state: Application state with MySQL connection
            
        Returns:
            Connection test result
        """
        try:
            test_query = "SELECT 1 as test_value"
            result = self.execute_sql(test_query, app_state)
            
            if result.success:
                return {
                    "status": "healthy",
                    "execution_time_ms": result.execution_time_ms,
                    "connection_pool": "available"
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": result.error
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def get_execution_stats(self) -> dict:
        """
        Get execution statistics (placeholder for future implementation)
        
        Returns:
            Dictionary with execution statistics
        """
        return {
            "config": {
                "max_rows": self.config.max_rows,
                "timeout_seconds": self.config.timeout_seconds,
                "query_logging": self.config.enable_query_logging
            },
            "status": "active"
        }
    
    def update_config(self, new_config: ExecutionConfig) -> None:
        """
        Update execution configuration
        
        Args:
            new_config: New execution configuration
        """
        self.config = new_config
    
    def health_check(self, app_state) -> dict:
        """
        Perform health check on the SQL executor
        
        Args:
            app_state: Application state with MySQL connection
            
        Returns:
            Health status dictionary
        """
        try:
            # Test database connection
            connection_test = self.test_connection(app_state)
            
            if connection_test["status"] == "healthy":
                return {
                    "status": "healthy",
                    "database_connection": "available",
                    "execution_config": {
                        "max_rows": self.config.max_rows,
                        "timeout_seconds": self.config.timeout_seconds
                    },
                    "test_execution_time_ms": connection_test["execution_time_ms"]
                }
            else:
                return {
                    "status": "unhealthy",
                    "database_connection": "failed",
                    "error": connection_test["error"]
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
