import redis
from redis.connection import ConnectionPool
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class RedisConnectionManager:
    """Redis connection manager with connection pooling"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Redis connection manager.
        
        Args:
            config: Redis configuration dictionary
        """
        self.config = config
        self.pool = None
        self.client = None
        self._create_connection()
    
    def _create_connection(self) -> None:
        """Create Redis connection pool and client"""
        try:
            # Create connection pool
            pool_config = {
                'host': self.config['host'],
                'port': self.config['port'],
                'db': self.config['db'],
                'max_connections': self.config.get('max_connections', 10),
                'decode_responses': True,
                'socket_connect_timeout': 5,
                'socket_timeout': 5,
                'retry_on_timeout': True,
                'health_check_interval': 30,
            }
            
            # Add password if provided
            if self.config.get('password'):
                pool_config['password'] = self.config['password']
            
            self.pool = ConnectionPool(**pool_config)
            self.client = redis.Redis(connection_pool=self.pool)
            
            # Test connection
            self.client.ping()
            logger.info(f"Redis connection established successfully to {self.config['host']}:{self.config['port']}")
            
        except redis.RedisError as e:
            logger.error(f"Error creating Redis connection: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating Redis connection: {e}")
            raise
    
    def get_client(self) -> redis.Redis:
        """
        Get Redis client.
        
        Returns:
            Redis client instance
        """
        if self.client is None:
            raise Exception("Redis client not initialized")
        
        return self.client
    
    def ping(self) -> bool:
        """
        Test Redis connection.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            if self.client:
                return self.client.ping()
            return False
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
    
    def close_connection(self) -> None:
        """Close Redis connection pool"""
        try:
            if self.client:
                self.client.close()
                logger.info("Redis connection closed")
            
            if self.pool:
                self.pool.disconnect()
                logger.info("Redis connection pool closed")
                
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get Redis connection information.
        
        Returns:
            Dictionary with connection information
        """
        try:
            if not self.client:
                return {'status': 'not_connected'}
            
            info = self.client.info()
            return {
                'status': 'connected',
                'redis_version': info.get('redis_version'),
                'connected_clients': info.get('connected_clients'),
                'used_memory_human': info.get('used_memory_human'),
                'total_commands_processed': info.get('total_commands_processed'),
                'keyspace_hits': info.get('keyspace_hits'),
                'keyspace_misses': info.get('keyspace_misses'),
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def set_key(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """
        Set a key-value pair in Redis.
        
        Args:
            key: Redis key
            value: Value to store
            ex: Expiration time in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return self.client.set(key, value, ex=ex)
        except Exception as e:
            logger.error(f"Error setting Redis key {key}: {e}")
            return False
    
    def get_key(self, key: str) -> Optional[str]:
        """
        Get value for a key from Redis.
        
        Args:
            key: Redis key
            
        Returns:
            Value if key exists, None otherwise
        """
        try:
            return self.client.get(key)
        except Exception as e:
            logger.error(f"Error getting Redis key {key}: {e}")
            return None
    
    def delete_key(self, key: str) -> bool:
        """
        Delete a key from Redis.
        
        Args:
            key: Redis key to delete
            
        Returns:
            True if key was deleted, False otherwise
        """
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Error deleting Redis key {key}: {e}")
            return False

def create_redis_connection(config: Dict[str, Any]) -> RedisConnectionManager:
    """
    Create and return Redis connection manager.
    
    Args:
        config: Redis configuration dictionary
        
    Returns:
        RedisConnectionManager instance
    """
    return RedisConnectionManager(config)

def test_redis_connection(config: Dict[str, Any]) -> bool:
    """
    Test Redis connection with given configuration.
    
    Args:
        config: Redis configuration dictionary
        
    Returns:
        True if connection successful, False otherwise
    """
    try:
        client_config = {
            'host': config['host'],
            'port': config['port'],
            'db': config['db'],
            'socket_connect_timeout': 5,
            'socket_timeout': 5,
        }
        
        if config.get('password'):
            client_config['password'] = config['password']
        
        client = redis.Redis(**client_config)
        result = client.ping()
        client.close()
        return result
        
    except Exception as e:
        logger.error(f"Redis connection test failed: {e}")
        return False
