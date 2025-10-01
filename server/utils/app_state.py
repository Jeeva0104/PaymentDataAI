from typing import Dict, Any, Optional
import logging
import atexit
from config.app_config import load_config, validate_config
from config.database import create_mysql_pool, MySQLConnectionPool
from config.redis_config import create_redis_connection, RedisConnectionManager
from config.websocket_config import create_websocket_manager, WebSocketManager

logger = logging.getLogger(__name__)

class AppState:
    """Global application state manager"""
    
    def __init__(self):
        """Initialize app state"""
        self.config: Dict[str, Any] = {}
        self.mysql_connection: Optional[MySQLConnectionPool] = None
        self.redis_connection: Optional[RedisConnectionManager] = None
        self.websocket_config: Optional[WebSocketManager] = None
        self._initialized = False
    
    def initialize(self, app) -> bool:
        """
        Initialize all app state components.
        
        Args:
            app: Flask application instance
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing app state...")
            
            # Load configuration
            self.config = load_config()
            if not validate_config(self.config):
                logger.error("Configuration validation failed")
                return False
            
            logger.info("Configuration loaded and validated successfully")
            
            # Initialize MySQL connection pool
            self.mysql_connection = create_mysql_pool(self.config['mysql'])
            logger.info("MySQL connection pool initialized")
            
            # Initialize Redis connection
            self.redis_connection = create_redis_connection(self.config['redis'])
            logger.info("Redis connection initialized")
            
            # Initialize WebSocket manager
            self.websocket_config = create_websocket_manager(app, self.config['websocket'])
            logger.info("WebSocket manager initialized")
            
            # Register cleanup handlers
            atexit.register(self.cleanup)
            
            self._initialized = True
            logger.info("App state initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing app state: {e}")
            self.cleanup()
            return False
    
    def is_initialized(self) -> bool:
        """
        Check if app state is initialized.
        
        Returns:
            True if initialized, False otherwise
        """
        return self._initialized
    
    def get_mysql_connection(self):
        """
        Get MySQL connection from pool.
        
        Returns:
            MySQL connection object
        """
        if not self.mysql_connection:
            raise Exception("MySQL connection pool not initialized")
        
        return self.mysql_connection.get_connection()
    
    def get_redis_client(self):
        """
        Get Redis client.
        
        Returns:
            Redis client object
        """
        if not self.redis_connection:
            raise Exception("Redis connection not initialized")
        
        return self.redis_connection.get_client()
    
    def get_socketio(self):
        """
        Get SocketIO instance.
        
        Returns:
            SocketIO instance
        """
        if not self.websocket_config:
            raise Exception("WebSocket manager not initialized")
        
        return self.websocket_config.get_socketio()
    
    def get_websocket_manager(self) -> WebSocketManager:
        """
        Get WebSocket manager.
        
        Returns:
            WebSocketManager instance
        """
        if not self.websocket_config:
            raise Exception("WebSocket manager not initialized")
        
        return self.websocket_config
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all components.
        
        Returns:
            Dictionary with health status of all components
        """
        health_status = {
            'app_state': 'healthy' if self._initialized else 'not_initialized',
            'mysql': 'unknown',
            'redis': 'unknown',
            'websocket': 'unknown'
        }
        
        # Check MySQL
        try:
            if self.mysql_connection:
                mysql_status = self.mysql_connection.get_pool_status()
                health_status['mysql'] = mysql_status.get('status', 'unknown')
            else:
                health_status['mysql'] = 'not_initialized'
        except Exception as e:
            health_status['mysql'] = f'error: {str(e)}'
        
        # Check Redis
        try:
            if self.redis_connection:
                health_status['redis'] = 'healthy' if self.redis_connection.ping() else 'unhealthy'
            else:
                health_status['redis'] = 'not_initialized'
        except Exception as e:
            health_status['redis'] = f'error: {str(e)}'
        
        # Check WebSocket
        try:
            if self.websocket_config:
                health_status['websocket'] = 'healthy'
                health_status['websocket_connections'] = self.websocket_config.get_connection_count()
            else:
                health_status['websocket'] = 'not_initialized'
        except Exception as e:
            health_status['websocket'] = f'error: {str(e)}'
        
        return health_status
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics.
        
        Returns:
            Dictionary with statistics from all components
        """
        stats = {
            'app_state': {
                'initialized': self._initialized,
                'config_loaded': bool(self.config)
            }
        }
        
        # MySQL stats
        try:
            if self.mysql_connection:
                stats['mysql'] = self.mysql_connection.get_pool_status()
            else:
                stats['mysql'] = {'status': 'not_initialized'}
        except Exception as e:
            stats['mysql'] = {'status': 'error', 'error': str(e)}
        
        # Redis stats
        try:
            if self.redis_connection:
                stats['redis'] = self.redis_connection.get_connection_info()
            else:
                stats['redis'] = {'status': 'not_initialized'}
        except Exception as e:
            stats['redis'] = {'status': 'error', 'error': str(e)}
        
        # WebSocket stats
        try:
            if self.websocket_config:
                stats['websocket'] = self.websocket_config.get_websocket_stats()
            else:
                stats['websocket'] = {'status': 'not_initialized'}
        except Exception as e:
            stats['websocket'] = {'status': 'error', 'error': str(e)}
        
        return stats
    
    def cleanup(self) -> None:
        """Clean up all connections and resources"""
        logger.info("Cleaning up app state...")
        
        try:
            if self.mysql_connection:
                self.mysql_connection.close_pool()
                logger.info("MySQL connection pool closed")
        except Exception as e:
            logger.error(f"Error closing MySQL connection pool: {e}")
        
        try:
            if self.redis_connection:
                self.redis_connection.close_connection()
                logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
        
        self._initialized = False
        logger.info("App state cleanup completed")

# Global app state instance
app_state = AppState()

def get_app_state() -> AppState:
    """
    Get the global app state instance.
    
    Returns:
        AppState instance
    """
    return app_state

def initialize_app_state(app) -> bool:
    """
    Initialize the global app state.
    
    Args:
        app: Flask application instance
        
    Returns:
        True if initialization successful, False otherwise
    """
    return app_state.initialize(app)
