from flask_socketio import SocketIO
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class WebSocketManager:
    """WebSocket manager for Flask-SocketIO"""
    
    def __init__(self, app, config: Dict[str, Any]):
        """
        Initialize WebSocket manager.
        
        Args:
            app: Flask application instance
            config: WebSocket configuration dictionary
        """
        self.config = config
        self.socketio = None
        self.active_connections = {}
        self._initialize_socketio(app)
    
    def _initialize_socketio(self, app) -> None:
        """Initialize Flask-SocketIO"""
        try:
            socketio_config = {
                'cors_allowed_origins': self.config.get('cors_origins', '*'),
                'async_mode': self.config.get('async_mode', 'eventlet'),
                'ping_timeout': self.config.get('ping_timeout', 60),
                'ping_interval': self.config.get('ping_interval', 25),
                'logger': True,
                'engineio_logger': False,
            }
            
            self.socketio = SocketIO(app, **socketio_config)
            
        except Exception as e:
            logger.error(f"Error initializing WebSocket: {e}")
            raise
    
    def get_socketio(self) -> SocketIO:
        """
        Get SocketIO instance.
        
        Returns:
            SocketIO instance
        """
        if self.socketio is None:
            raise Exception("SocketIO not initialized")
        
        return self.socketio
    
    def add_connection(self, session_id: str, user_data: Dict[str, Any] = None) -> None:
        """
        Add a new connection to tracking.
        
        Args:
            session_id: Socket session ID
            user_data: Optional user data to store
        """
        self.active_connections[session_id] = {
            'connected_at': self._get_current_timestamp(),
            'user_data': user_data or {},
            'message_count': 0
        }
    
    def remove_connection(self, session_id: str) -> None:
        """
        Remove connection from tracking.
        
        Args:
            session_id: Socket session ID
        """
        if session_id in self.active_connections:
            del self.active_connections[session_id]
    
    def increment_message_count(self, session_id: str) -> None:
        """
        Increment message count for a connection.
        
        Args:
            session_id: Socket session ID
        """
        if session_id in self.active_connections:
            self.active_connections[session_id]['message_count'] += 1
    
    def get_connection_count(self) -> int:
        """
        Get total number of active connections.
        
        Returns:
            Number of active connections
        """
        return len(self.active_connections)
    
    def get_connection_info(self, session_id: str) -> Dict[str, Any]:
        """
        Get information about a specific connection.
        
        Args:
            session_id: Socket session ID
            
        Returns:
            Connection information dictionary
        """
        return self.active_connections.get(session_id, {})
    
    def get_all_connections(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all active connections.
        
        Returns:
            Dictionary of all active connections
        """
        return self.active_connections.copy()
    
    def broadcast_message(self, event: str, data: Dict[str, Any], room: str = None) -> None:
        """
        Broadcast message to all or specific room.
        
        Args:
            event: Event name
            data: Data to send
            room: Optional room to broadcast to
        """
        try:
            if room:
                self.socketio.emit(event, data, room=room)
            else:
                self.socketio.emit(event, data, broadcast=True)
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")
    
    def send_to_client(self, session_id: str, event: str, data: Dict[str, Any]) -> None:
        """
        Send message to specific client.
        
        Args:
            session_id: Target session ID
            event: Event name
            data: Data to send
        """
        try:
            self.socketio.emit(event, data, room=session_id)
        except Exception as e:
            logger.error(f"Error sending message to client {session_id}: {e}")
    
    def get_websocket_stats(self) -> Dict[str, Any]:
        """
        Get WebSocket statistics.
        
        Returns:
            Dictionary with WebSocket statistics
        """
        total_messages = sum(
            conn.get('message_count', 0) 
            for conn in self.active_connections.values()
        )
        
        return {
            'active_connections': self.get_connection_count(),
            'total_messages_processed': total_messages,
            'async_mode': self.config.get('async_mode'),
            'cors_origins': self.config.get('cors_origins'),
        }
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp as string"""
        from datetime import datetime
        return datetime.now().isoformat()

def create_websocket_manager(app, config: Dict[str, Any]) -> WebSocketManager:
    """
    Create and return WebSocket manager.
    
    Args:
        app: Flask application instance
        config: WebSocket configuration dictionary
        
    Returns:
        WebSocketManager instance
    """
    return WebSocketManager(app, config)
