# Payment Data AI 

## Architecture

### App State Structure
```python
app_state = {
    'config': {},           # Environment configuration
    'mysql_connection': {}, # MySQL connection pool
    'redis_connection': {}, # Redis connection manager
    'websocket_config': {}  # WebSocket manager
}
```

### Project Structure
```
server/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── config/
│   ├── __init__.py
│   ├── app_config.py      # Environment configuration loader
│   ├── database.py        # MySQL connection pool
│   ├── redis_config.py    # Redis connection manager
│   └── websocket_config.py # WebSocket configuration
├── utils/
│   ├── __init__.py
│   └── app_state.py       # Centralized app state management
├── websocket/
│   ├── __init__.py
│   └── events.py          # WebSocket event handlers
└── prompts/               # Existing prompt files
```

## Prerequisites

- Python 3.8+
- Docker and Docker Compose
- Git

## Configuration

### Environment Variables (.env)
```bash
# MySQL Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=payment_user
MYSQL_PASSWORD=payment_secure_2024!
MYSQL_DATABASE=payment_system

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# WebSocket Configuration
WEBSOCKET_CORS_ORIGINS=*
WEBSOCKET_ASYNC_MODE=eventlet
```

## Installation & Setup

### Option 1: Full Docker Development (Recommended)

#### Quick Start
```bash
# Make the development script executable
chmod +x docker-dev.sh

# Start the complete development environment
./docker-dev.sh start
```

This will:
- Build and start Flask app, MySQL, and Redis containers
- Enable hot-reload for immediate code changes
- Set up proper networking between services
- Provide health checks and monitoring

#### Development Commands
```bash
# Start development environment
./docker-dev.sh start

# View logs (all services or specific)
./docker-dev.sh logs
./docker-dev.sh logs app

# Check service status and health
./docker-dev.sh status

# Restart services
./docker-dev.sh restart

# Rebuild Flask app after dependency changes
./docker-dev.sh rebuild

# Enter Flask app container for debugging
./docker-dev.sh shell

# Stop development environment
./docker-dev.sh stop

# Clean up (removes volumes and containers)
./docker-dev.sh cleanup
```

### Option 2: Local Development with Docker Services

#### 1. Start Database Services Only
```bash
# Start only MySQL and Redis
docker-compose up mysql redis -d
```

#### 2. Install Python Dependencies Locally
```bash
cd server
pip install -r requirements.txt
```

#### 3. Run Flask Application Locally
```bash
cd server
python app.py
```

### Environment Configuration
The `.env` file is configured with:
- MySQL database settings
- Redis configuration  
- WebSocket settings
- Flask development settings

**Note:** When using full Docker development, the app automatically connects to containerized MySQL and Redis services.

## API Endpoints

### Health Check Endpoints
- `GET /` - Root endpoint with basic info
- `GET /health` - Basic health check for all components
- `GET /health/detailed` - Detailed health check with statistics
- `GET /health/mysql` - MySQL-specific health check
- `GET /health/redis` - Redis-specific health check
- `GET /health/websocket` - WebSocket-specific health check

### Information Endpoints
- `GET /stats` - Comprehensive application statistics
- `GET /config` - Non-sensitive configuration information

## WebSocket Events

### Client → Server Events
- `connect` - Establish WebSocket connection
- `disconnect` - Close WebSocket connection
- `user-query` - Send user query for processing
- `ping` - Health check ping
- `get_session_info` - Request session information

### Server → Client Events
- `connection_established` - Connection confirmation
- `query_response` - Response to user query
- `query_error` - Error in query processing
- `pong` - Response to ping
- `session_info` - Session information
- `error` - General error messages

## Testing the Application

### 1. Test HTTP Endpoints
```bash
# Basic health check
curl http://localhost:5000/health

# Detailed health check
curl http://localhost:5000/health/detailed

# Application statistics
curl http://localhost:5000/stats
```

### 2. Test WebSocket Functionality
Open `test_client.html` in your browser:
```bash
# Open the test client
open test_client.html
# or
python -m http.server 8000
# Then navigate to http://localhost:8000/test_client.html
```





