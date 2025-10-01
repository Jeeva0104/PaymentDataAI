from flask import Flask, jsonify, request
from flask_socketio import SocketIO
import logging
import sys
import os

# Add the server directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.app_state import initialize_app_state, get_app_state
from websocket.events import register_websocket_events

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

logger = logging.getLogger(__name__)

def create_app():
    """
    Create and configure Flask application.
    
    Returns:
        Flask application instance with SocketIO attached
    """
    app = Flask(__name__)
    
    # Configure Flask app
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info("Starting Flask application initialization...")
    
    # Initialize app state
    if not initialize_app_state(app):
        logger.error("Failed to initialize app state")
        sys.exit(1)
    
    # Get app state instance
    app_state = get_app_state()
    
    # Get SocketIO instance from app state
    socketio = app_state.get_socketio()
    
    # Attach SocketIO to app for production access
    app.socketio = socketio
    
    # Register WebSocket events
    register_websocket_events(socketio)
    
    # Register HTTP routes
    register_routes(app)
    
    logger.info("Flask application created and configured successfully")
    logger.info(f"Available routes: {[rule.rule for rule in app.url_map.iter_rules()]}")
    
    return app

def register_routes(app):
    """
    Register HTTP routes.
    
    Args:
        app: Flask application instance
    """
    
    @app.route('/')
    def index():
        """Root endpoint"""
        return jsonify({
            'message': 'Flask app with WebSocket, MySQL, and Redis is running!',
            'status': 'healthy',
            'endpoints': {
                'health': '/health',
                'health_detailed': '/health/detailed',
                'stats': '/stats',
                'websocket': '/socket.io/'
            }
        })
    
    @app.route('/health')
    def health_check():
        """Basic health check endpoint"""
        try:
            app_state = get_app_state()
            health_status = app_state.health_check()
            
            # Determine overall health
            overall_health = 'healthy'
            for component, status in health_status.items():
                if isinstance(status, str) and ('error' in status.lower() or 'unhealthy' in status.lower()):
                    overall_health = 'unhealthy'
                    break
            
            return jsonify({
                'status': overall_health,
                'timestamp': app_state.config.get('timezone', 'UTC'),
                'components': health_status
            }), 200 if overall_health == 'healthy' else 503
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500
    
    @app.route('/health/detailed')
    def detailed_health_check():
        """Detailed health check with component information"""
        try:
            app_state = get_app_state()
            health_status = app_state.health_check()
            stats = app_state.get_stats()
            
            return jsonify({
                'health': health_status,
                'stats': stats,
                'app_initialized': app_state.is_initialized()
            })
            
        except Exception as e:
            logger.error(f"Detailed health check failed: {e}")
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500
    
    @app.route('/health/mysql')
    def mysql_health():
        """MySQL-specific health check"""
        try:
            app_state = get_app_state()
            mysql_pool = app_state.mysql_connection
            
            if not mysql_pool:
                return jsonify({'status': 'not_initialized'}), 503
            
            status = mysql_pool.get_pool_status()
            return jsonify(status)
            
        except Exception as e:
            logger.error(f"MySQL health check failed: {e}")
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500
    
    @app.route('/health/redis')
    def redis_health():
        """Redis-specific health check"""
        try:
            app_state = get_app_state()
            redis_manager = app_state.redis_connection
            
            if not redis_manager:
                return jsonify({'status': 'not_initialized'}), 503
            
            info = redis_manager.get_connection_info()
            return jsonify(info)
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500
    
    @app.route('/health/websocket')
    def websocket_health():
        """WebSocket-specific health check"""
        try:
            app_state = get_app_state()
            websocket_manager = app_state.get_websocket_manager()
            
            if not websocket_manager:
                return jsonify({'status': 'not_initialized'}), 503
            
            stats = websocket_manager.get_websocket_stats()
            return jsonify(stats)
            
        except Exception as e:
            logger.error(f"WebSocket health check failed: {e}")
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500
    
    @app.route('/stats')
    def get_stats():
        """Get comprehensive application statistics"""
        try:
            app_state = get_app_state()
            stats = app_state.get_stats()
            
            return jsonify({
                'stats': stats,
                'timestamp': app_state.config.get('timezone', 'UTC')
            })
            
        except Exception as e:
            logger.error(f"Stats endpoint failed: {e}")
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500
    
    @app.route('/config')
    def get_config():
        """Get non-sensitive configuration information"""
        try:
            app_state = get_app_state()
            
            # Return only non-sensitive config
            safe_config = {
                'mysql': {
                    'host': app_state.config['mysql']['host'],
                    'port': app_state.config['mysql']['port'],
                    'database': app_state.config['mysql']['database'],
                    'charset': app_state.config['mysql']['charset']
                },
                'redis': {
                    'host': app_state.config['redis']['host'],
                    'port': app_state.config['redis']['port'],
                    'db': app_state.config['redis']['db']
                },
                'websocket': app_state.config['websocket'],
                'timezone': app_state.config['timezone'],
                'environment': app_state.config['environment']
            }
            
            return jsonify(safe_config)
            
        except Exception as e:
            logger.error(f"Config endpoint failed: {e}")
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        return jsonify({
            'error': 'Endpoint not found',
            'available_endpoints': [
                '/',
                '/health',
                '/health/detailed',
                '/health/mysql',
                '/health/redis',
                '/health/websocket',
                '/stats',
                '/config'
            ]
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        logger.error(f"Internal server error: {error}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500

# Create application instance for production (Gunicorn)
app = create_app()

if __name__ == '__main__':
    """Run the application in development mode"""
    try:
        # Get SocketIO instance for development
        socketio = app.socketio
        
        # Get configuration
        app_state = get_app_state()
        config = app_state.config
        
        # Run the application with SocketIO for development
        logger.info("Starting Flask application with SocketIO in development mode...")
        socketio.run(
            app,
            host='0.0.0.0',
            port=5000,
            debug=config.get('debug', False),
            allow_unsafe_werkzeug=True  # For development only
        )
        
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        try:
            app_state = get_app_state()
            app_state.cleanup()
        except:
            pass
