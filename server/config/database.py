import mysql.connector.pooling
from mysql.connector import Error
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class MySQLConnectionPool:
    """MySQL connection pool manager"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize MySQL connection pool.
        
        Args:
            config: MySQL configuration dictionary
        """
        self.config = config
        self.pool = None
        self._create_pool()
    
    def _create_pool(self) -> None:
        """Create MySQL connection pool"""
        try:
            pool_config = {
                'pool_name': 'payment_pool',
                'pool_size': min(self.config.get('max_connections', 10), 32),  # MySQL Connector limit
                'pool_reset_session': True,
                'host': self.config['host'],
                'port': self.config['port'],
                'user': self.config['user'],
                'password': self.config['password'],
                'database': self.config['database'],
                'charset': self.config.get('charset', 'utf8mb4'),
                'autocommit': True,
                'raise_on_warnings': True,
            }
            
            self.pool = mysql.connector.pooling.MySQLConnectionPool(**pool_config)
            
        except Error as e:
            logger.error(f"Error creating MySQL connection pool: {e}")
            raise
    
    def get_connection(self):
        """
        Get a connection from the pool.
        
        Returns:
            MySQL connection object
        """
        try:
            if self.pool is None:
                raise Exception("Connection pool not initialized")
            
            connection = self.pool.get_connection()
            if connection.is_connected():
                return connection
            else:
                raise Exception("Failed to get active connection from pool")
                
        except Error as e:
            logger.error(f"Error getting connection from pool: {e}")
            raise
    
    def return_connection(self, connection) -> None:
        """
        Return connection to pool (handled automatically by context manager).
        
        Args:
            connection: MySQL connection object
        """
        if connection and connection.is_connected():
            connection.close()
    
    def close_pool(self) -> None:
        """Close all connections in the pool"""
        try:
            if self.pool:
                # Close all connections in pool
                # Note: mysql-connector-python doesn't have a direct close_all method
                # Connections will be closed when the pool object is destroyed
                self.pool = None
                
        except Exception as e:
            logger.error(f"Error closing MySQL connection pool: {e}")
    
    def get_pool_status(self) -> Dict[str, Any]:
        """
        Get connection pool status.
        
        Returns:
            Dictionary with pool status information
        """
        if not self.pool:
            return {'status': 'not_initialized'}
        
        try:
            # Get a test connection to verify pool health
            test_conn = self.pool.get_connection()
            test_conn.close()
            
            return {
                'status': 'healthy',
                'pool_name': self.pool.pool_name,
                'pool_size': self.pool.pool_size,
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

def create_mysql_pool(config: Dict[str, Any]) -> MySQLConnectionPool:
    """
    Create and return MySQL connection pool.
    
    Args:
        config: MySQL configuration dictionary
        
    Returns:
        MySQLConnectionPool instance
    """
    return MySQLConnectionPool(config)

def test_mysql_connection(config: Dict[str, Any]) -> bool:
    """
    Test MySQL connection with given configuration.
    
    Args:
        config: MySQL configuration dictionary
        
    Returns:
        True if connection successful, False otherwise
    """
    try:
        connection = mysql.connector.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset=config.get('charset', 'utf8mb4')
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            connection.close()
            return result[0] == 1
            
    except Error as e:
        logger.error(f"MySQL connection test failed: {e}")
        return False
    
    return False
