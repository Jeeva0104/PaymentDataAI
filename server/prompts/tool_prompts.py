"""
Tool prompts for database schema operations
Contains methods to fetch MySQL table schema information
"""

import logging
from typing import Dict, Any, List, Optional
from mysql.connector import Error

logger = logging.getLogger(__name__)


def _fetch_table_schema(connection, table_name: str) -> Dict[str, Any]:
    """
    Internal helper to fetch complete schema for a single table
    
    Args:
        connection: MySQL connection object
        table_name: Name of the table to fetch schema for
        
    Returns:
        Dict containing complete table schema information
    """
    cursor = None
    try:
        cursor = connection.cursor()
        
        # Query for column information
        column_query = """
        SELECT 
            COLUMN_NAME,
            DATA_TYPE,
            IS_NULLABLE,
            COLUMN_KEY
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = 'payment_system' 
        AND TABLE_NAME = %s
        ORDER BY ORDINAL_POSITION
        """
        
        cursor.execute(column_query, (table_name,))
        column_results = cursor.fetchall()
        
        # Format column information
        columns = []
        for row in column_results:
            columns.append({
                'name': row[0],
                'data_type': row[1],
                'nullable': row[2],
                'key': row[3] if row[3] else ''
            })
        
        # Query for index information
        index_query = """
        SELECT 
            INDEX_NAME,
            COLUMN_NAME,
            NON_UNIQUE
        FROM INFORMATION_SCHEMA.STATISTICS 
        WHERE TABLE_SCHEMA = 'payment_system' 
        AND TABLE_NAME = %s
        AND INDEX_NAME != 'PRIMARY'
        ORDER BY INDEX_NAME, SEQ_IN_INDEX
        """
        
        cursor.execute(index_query, (table_name,))
        index_results = cursor.fetchall()
        
        # Format index information
        indexes_dict = {}
        for row in index_results:
            index_name = row[0]
            column_name = row[1]
            non_unique = row[2]
            
            if index_name not in indexes_dict:
                indexes_dict[index_name] = {
                    'name': index_name,
                    'columns': [],
                    'unique': not bool(non_unique)
                }
            
            indexes_dict[index_name]['columns'].append(column_name)
        
        indexes = list(indexes_dict.values())
        
        # Query for foreign key information
        fk_query = """
        SELECT 
            CONSTRAINT_NAME,
            COLUMN_NAME,
            REFERENCED_TABLE_NAME,
            REFERENCED_COLUMN_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
        WHERE TABLE_SCHEMA = 'payment_system'
        AND TABLE_NAME = %s
        AND REFERENCED_TABLE_NAME IS NOT NULL
        """
        
        cursor.execute(fk_query, (table_name,))
        fk_results = cursor.fetchall()
        
        # Format foreign key information
        foreign_keys = []
        for row in fk_results:
            foreign_keys.append({
                'constraint_name': row[0],
                'column': row[1],
                'referenced_table': row[2],
                'referenced_column': row[3]
            })
        
        return {
            'table_name': table_name,
            'columns': columns,
            'indexes': indexes,
            'foreign_keys': foreign_keys
        }
        
    except Error as e:
        logger.error(f"Error fetching schema for table {table_name}: {e}")
        return {
            'table_name': table_name,
            'columns': [],
            'indexes': [],
            'foreign_keys': [],
            'error': str(e)
        }
    finally:
        if cursor:
            cursor.close()


def get_payment_intent_schema(app_state) -> Dict[str, Any]:
    """
    Fetch schema structure for payment_intent table
    
    Args:
        app_state: Application state containing MySQL connection
        
    Returns:
        Dict containing payment_intent table schema information
    """
    connection = None
    try:
        connection = app_state.get_mysql_connection()
        schema_info = _fetch_table_schema(connection, 'payment_intent')
        logger.info("Successfully fetched payment_intent schema")
        return schema_info
        
    except Exception as e:
        logger.error(f"Error getting payment_intent schema: {e}")
        return {
            'table_name': 'payment_intent',
            'columns': [],
            'indexes': [],
            'foreign_keys': [],
            'error': str(e)
        }
    finally:
        if connection:
            connection.close()


def get_payment_attempt_schema(app_state) -> Dict[str, Any]:
    """
    Fetch schema structure for payment_attempt table
    
    Args:
        app_state: Application state containing MySQL connection
        
    Returns:
        Dict containing payment_attempt table schema information
    """
    connection = None
    try:
        connection = app_state.get_mysql_connection()
        schema_info = _fetch_table_schema(connection, 'payment_attempt')
        logger.info("Successfully fetched payment_attempt schema")
        return schema_info
        
    except Exception as e:
        logger.error(f"Error getting payment_attempt schema: {e}")
        return {
            'table_name': 'payment_attempt',
            'columns': [],
            'indexes': [],
            'foreign_keys': [],
            'error': str(e)
        }
    finally:
        if connection:
            connection.close()


def get_address_schema(app_state) -> Dict[str, Any]:
    """
    Fetch schema structure for address table
    
    Args:
        app_state: Application state containing MySQL connection
        
    Returns:
        Dict containing address table schema information
    """
    connection = None
    try:
        connection = app_state.get_mysql_connection()
        schema_info = _fetch_table_schema(connection, 'address')
        logger.info("Successfully fetched address schema")
        return schema_info
        
    except Exception as e:
        logger.error(f"Error getting address schema: {e}")
        return {
            'table_name': 'address',
            'columns': [],
            'indexes': [],
            'foreign_keys': [],
            'error': str(e)
        }
    finally:
        if connection:
            connection.close()


def get_customer_schema(app_state) -> Dict[str, Any]:
    """
    Fetch schema structure for customers table
    
    Args:
        app_state: Application state containing MySQL connection
        
    Returns:
        Dict containing customers table schema information
    """
    connection = None
    try:
        connection = app_state.get_mysql_connection()
        schema_info = _fetch_table_schema(connection, 'customers')
        logger.info("Successfully fetched customers schema")
        return schema_info
        
    except Exception as e:
        logger.error(f"Error getting customers schema: {e}")
        return {
            'table_name': 'customers',
            'columns': [],
            'indexes': [],
            'foreign_keys': [],
            'error': str(e)
        }
    finally:
        if connection:
            connection.close()


def get_schema(app_state) -> Dict[str, Any]:
    """
    Fetch schema structures for all payment-related tables
    
    Args:
        app_state: Application state containing MySQL connection
        
    Returns:
        Dict containing schema information for all tables:
        {
            'payment_intent': {...},
            'payment_attempt': {...},
            'address': {...},
            'customers': {...}
        }
    """
    try:
        logger.info("Starting to fetch all table schemas")
        
        # Fetch schema for all tables
        schemas = {
            'payment_intent': get_payment_intent_schema(app_state),
            'payment_attempt': get_payment_attempt_schema(app_state),
            'address': get_address_schema(app_state),
            'customers': get_customer_schema(app_state)
        }
        
        logger.info("Successfully fetched all table schemas")
        return schemas
        
    except Exception as e:
        logger.error(f"Error fetching all schemas: {e}")
        return {
            'payment_intent': {'error': str(e)},
            'payment_attempt': {'error': str(e)},
            'address': {'error': str(e)},
            'customers': {'error': str(e)},
            'global_error': str(e)
        }
