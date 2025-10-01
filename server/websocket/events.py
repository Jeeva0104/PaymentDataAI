from flask_socketio import emit, disconnect
from flask import request
from utils.app_state import get_app_state
from chat_handler import process_chat_request, process_chat_request_with_langchain, ChatHandler
from langchain_integration.models.response_models import DataSummaryResult
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

def register_websocket_events(socketio):
    """
    Register all WebSocket event handlers.
    
    Args:
        socketio: SocketIO instance
    """
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        try:
            session_id = request.sid
            client_ip = request.environ.get('REMOTE_ADDR', 'unknown')
            
            logger.info(f"Client connected: {session_id} from {client_ip}")
            
            # Get app state
            app_state = get_app_state()
            
            # Add connection to WebSocket manager
            websocket_manager = app_state.get_websocket_manager()
            websocket_manager.add_connection(session_id, {
                'ip': client_ip,
                'user_agent': request.headers.get('User-Agent', 'unknown')
            })
            
            # Send welcome message
            emit('connection_established', {
                'status': 'connected',
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'message': 'WebSocket connection established successfully'
            })
            
            # Store session info in Redis for tracking
            try:
                redis_client = app_state.get_redis_client()
                session_data = {
                    'connected_at': datetime.now().isoformat(),
                    'ip': client_ip,
                    'user_agent': request.headers.get('User-Agent', 'unknown')
                }
                redis_client.set(f"session:{session_id}", json.dumps(session_data), ex=3600)  # 1 hour expiry
            except Exception as e:
                logger.error(f"Error storing session in Redis: {e}")
            
        except Exception as e:
            logger.error(f"Error handling connection: {e}")
            emit('error', {'message': 'Connection error occurred'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        try:
            session_id = request.sid
            logger.info(f"Client disconnected: {session_id}")
            
            # Get app state
            app_state = get_app_state()
            
            # Remove connection from WebSocket manager
            websocket_manager = app_state.get_websocket_manager()
            websocket_manager.remove_connection(session_id)
            
            # Clean up session data from Redis
            try:
                redis_client = app_state.get_redis_client()
                redis_client.delete(f"session:{session_id}")
            except Exception as e:
                logger.error(f"Error cleaning up session from Redis: {e}")
            
        except Exception as e:
            logger.error(f"Error handling disconnection: {e}")
    
    @socketio.on('user-query')
    def handle_user_query(data):
        """
        Handle user query events.
        
        Args:
            data: Query data from client
        """
        try:
            session_id = request.sid
            logger.info(f"Received user-query from {session_id}: {data}")
            
            # Validate input data
            if not isinstance(data, dict):
                emit('query_error', {
                    'error': 'Invalid data format. Expected JSON object.',
                    'timestamp': datetime.now().isoformat()
                })
                return
            
            query = data.get('query', '').strip()
            if not query:
                emit('query_error', {
                    'error': 'Query cannot be empty.',
                    'timestamp': datetime.now().isoformat()
                })
                return
            
            # Get app state
            app_state = get_app_state()
            
            # Increment message count
            websocket_manager = app_state.get_websocket_manager()
            websocket_manager.increment_message_count(session_id)
            
            # Process the query
            response = process_user_query(query, session_id, app_state)
            
            # Send response back to client
            emit('query_response', response)
            
        except Exception as e:
            logger.error(f"Error handling user query: {e}")
            emit('query_error', {
                'error': 'An error occurred while processing your query.',
                'timestamp': datetime.now().isoformat()
            })
    
    @socketio.on('ping')
    def handle_ping():
        """Handle ping requests for connection health check"""
        try:
            session_id = request.sid
            emit('pong', {
                'timestamp': datetime.now().isoformat(),
                'session_id': session_id
            })
        except Exception as e:
            logger.error(f"Error handling ping: {e}")
    
    @socketio.on('get_session_info')
    def handle_get_session_info():
        """Get session information"""
        try:
            session_id = request.sid
            app_state = get_app_state()
            
            # Get connection info from WebSocket manager
            websocket_manager = app_state.get_websocket_manager()
            connection_info = websocket_manager.get_connection_info(session_id)
            
            # Get session data from Redis
            session_data = {}
            try:
                redis_client = app_state.get_redis_client()
                redis_session = redis_client.get(f"session:{session_id}")
                if redis_session:
                    session_data = json.loads(redis_session)
            except Exception as e:
                logger.error(f"Error retrieving session from Redis: {e}")
            
            emit('session_info', {
                'session_id': session_id,
                'connection_info': connection_info,
                'session_data': session_data,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error getting session info: {e}")
            emit('error', {'message': 'Error retrieving session information'})
    
    @socketio.on('get_chat_stats')
    def handle_get_chat_stats():
        """Get ChatHandler processing statistics"""
        try:
            session_id = request.sid
            logger.info(f"Chat stats requested by session: {session_id}")
            
            # Create ChatHandler instance to get stats
            handler = ChatHandler()
            stats = handler.get_stats()
            
            emit('chat_stats', {
                'stats': stats,
                'session_id': session_id,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error getting chat stats: {e}")
            emit('error', {'message': 'Error retrieving chat statistics'})
    
    @socketio.on('clear_chat_cache')
    def handle_clear_chat_cache():
        """Clear ChatHandler cache"""
        try:
            session_id = request.sid
            logger.info(f"Cache clear requested by session: {session_id}")
            
            handler = ChatHandler()
            handler.clear_cache()
            
            emit('cache_cleared', {
                'message': 'Chat handler cache cleared successfully',
                'session_id': session_id,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error clearing chat cache: {e}")
            emit('error', {'message': 'Error clearing chat cache'})
    
    @socketio.on('get_query_history')
    def handle_get_query_history(data):
        """Get query history for the session"""
        try:
            session_id = request.sid
            app_state = get_app_state()
            redis_client = app_state.get_redis_client()
            
            # Get limit from request data (default 10)
            limit = data.get('limit', 10) if isinstance(data, dict) else 10
            limit = min(max(1, limit), 50)  # Clamp between 1 and 50
            
            # Get all query keys for this session
            pattern = f"query:{session_id}:*"
            query_keys = redis_client.keys(pattern)
            
            # Sort by timestamp (newest first) and limit
            query_keys.sort(reverse=True)
            query_keys = query_keys[:limit]
            
            # Fetch query data
            history = []
            for key in query_keys:
                try:
                    query_data = redis_client.get(key)
                    if query_data:
                        history.append(json.loads(query_data))
                except Exception as e:
                    logger.error(f"Error parsing query history entry: {e}")
            
            emit('query_history', {
                'history': history,
                'total_queries': len(query_keys),
                'session_id': session_id,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error getting query history: {e}")
            emit('error', {'message': 'Error retrieving query history'})

def classify_and_format_response(query: str, chat_response: str) -> tuple:
    """
    Classify response type and format appropriately
    
    Args:
        query: Original user query
        chat_response: Response from ChatHandler
        
    Returns:
        tuple: (response_type, formatted_response)
    """
    
    # Check if response is a constructed prompt
    if chat_response.startswith('[SYSTEM CONTEXT]'):
        return 'analytics_prompt', chat_response
    
    # Check for specific response patterns
    if 'I\'m your analytics assistant' in chat_response:
        return 'help', chat_response
    elif 'Hello!' in chat_response and 'analytics' in chat_response:
        return 'greeting', chat_response
    elif 'I\'m specialized in payment analytics' in chat_response:
        return 'non_analytics', chat_response
    elif 'error' in chat_response.lower() or 'Error:' in chat_response:
        return 'error', chat_response
    elif any(keyword in chat_response.lower() for keyword in ['payment', 'transaction', 'analytics', 'revenue']):
        return 'analytics_direct', chat_response
    else:
        return 'general', chat_response


def handle_chat_error(base_response: dict, error: Exception) -> dict:
    """
    Handle ChatHandler errors and return appropriate WebSocket response
    
    Args:
        base_response: Base response dictionary
        error: Exception that occurred
        
    Returns:
        dict: Error response for WebSocket
    """
    
    error_type = type(error).__name__
    logger.error(f"[WEBSOCKET_CHAT_ERROR] {error_type}: {str(error)}")
    
    if 'ValidationError' in error_type:
        base_response.update({
            'status': 'validation_error',
            'response': f'Invalid query: {str(error)}',
            'type': 'validation_error'
        })
    elif 'ContextBuildError' in error_type:
        base_response.update({
            'status': 'error',
            'response': 'Unable to process query due to system error. Please try again.',
            'type': 'error'
        })
    else:
        base_response.update({
            'status': 'error',
            'response': 'An unexpected error occurred. Please try again.',
            'type': 'error'
        })
    
    return base_response


def store_query_history(session_id: str, query: str, response: str, app_state) -> None:
    """
    Store query and response in Redis for session history
    
    Args:
        session_id: WebSocket session ID
        query: Original user query
        response: ChatHandler response
        app_state: Application state instance
    """
    try:
        redis_client = app_state.get_redis_client()
        
        history_entry = {
            'query': query,
            'response': response[:500],  # Truncate long responses
            'timestamp': datetime.now().isoformat(),
            'response_length': len(response)
        }
        
        # Store individual query
        query_key = f"query:{session_id}:{datetime.now().timestamp()}"
        redis_client.set(query_key, json.dumps(history_entry), ex=86400)
        
        # Update session query count
        session_queries_key = f"session_queries:{session_id}"
        redis_client.incr(session_queries_key)
        redis_client.expire(session_queries_key, 86400)
        
    except Exception as e:
        logger.error(f"Error storing query history: {e}")


def process_user_query(query: str, session_id: str, app_state) -> dict:
    """
    Process user query and return serialized DataSummaryResult (no storage)
    
    Args:
        query: User query string
        session_id: WebSocket session ID
        app_state: Application state instance
        
    Returns:
        Dictionary with complete DataSummaryResult data
    """
    
    try:
        logger.info(f"[WEBSOCKET_CHAT] Session {session_id}: {query[:50]}...")
        
        # Get DataSummaryResult object from LangChain
        data_summary_result = process_chat_request_with_langchain(app_state, query, session_id)
        
        # Return serialized DataSummaryResult directly
        return {
            'query': query,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat(),
            'success': data_summary_result.success,
            'summary': data_summary_result.summary,
            'html_summary': data_summary_result.html_summary,
            'markdown_data': data_summary_result.markdown_data,
            'key_insights': data_summary_result.key_insights or [],
            'data_points_analyzed': data_summary_result.data_points_analyzed,
            'summary_time_ms': data_summary_result.summary_time_ms,
            'error': data_summary_result.error,
            'prompt_tokens': data_summary_result.prompt_tokens or 0,
            'completion_tokens': data_summary_result.completion_tokens or 0
        }
        
    except Exception as e:
        logger.error(f"[WEBSOCKET_CHAT_ERROR] {str(e)}")
        
        # Return error in same format
        return {
            'query': query,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'summary': f"Error: {str(e)}",
            'html_summary': f"<p><strong>Error:</strong> {str(e)}</p>",
            'markdown_data': None,
            'key_insights': [],
            'error': str(e),
            'data_points_analyzed': 0,
            'summary_time_ms': 0.0,
            'prompt_tokens': 0,
            'completion_tokens': 0
        }
