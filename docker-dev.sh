#!/bin/bash

# Development Docker Compose Script
# This script provides easy commands for development workflow

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Function to check if a service is ready
check_service_health() {
    local service_name="$1"
    local url="$2"
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            return 0
        fi
        sleep 2
        attempt=$((attempt + 1))
    done
    return 1
}

# Function to check if frontend is ready
check_frontend_health() {
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "http://localhost:3000" > /dev/null 2>&1; then
            return 0
        fi
        sleep 2
        attempt=$((attempt + 1))
    done
    return 1
}

# Function to wait for services and display endpoints
wait_for_services() {
    print_status "Waiting for services to be ready..."
    echo ""
    
    # Wait for backend health check
    print_status "Checking backend service..."
    if check_service_health "Flask App" "http://localhost:5000/health"; then
        print_success "✓ Backend endpoint ready: http://localhost:5000"
    else
        print_warning "⚠ Backend endpoint may not be ready: http://localhost:5000"
    fi
    
    # Wait for frontend
    print_status "Checking frontend service..."
    if check_frontend_health; then
        print_success "✓ Frontend endpoint ready: http://localhost:3000"
    else
        print_warning "⚠ Frontend endpoint may not be ready: http://localhost:3000"
    fi
    
    echo ""
    print_success "🚀 Payment Data AI Application Ready!"
    echo ""
    echo -e "${GREEN}📱 Application Endpoints:${NC}"
    echo -e "  ${BLUE}Frontend:${NC} http://localhost:3000"
    echo -e "  ${BLUE}Backend:${NC}  http://localhost:5000"
    echo ""
    echo -e "${YELLOW}🔧 Development Services:${NC}"
    echo -e "  ${BLUE}MySQL:${NC}   localhost:3306"
    echo -e "  ${BLUE}Redis:${NC}    localhost:6379"
    echo ""
    echo -e "${BLUE}💡 Quick Commands:${NC}"
    echo "  View logs:    ./docker-dev.sh logs"
    echo "  Check status: ./docker-dev.sh status"
    echo "  Stop:         ./docker-dev.sh stop"
    echo ""
}

# Function to build and start services
start_dev() {
    print_status "Starting Payment Data AI development environment..."
    check_docker
    
    # Build and start services
    print_status "Building and starting containers..."
    docker-compose up --build -d
    
    if [ $? -eq 0 ]; then
        print_success "Containers started successfully!"
        wait_for_services
    else
        print_error "Failed to start containers"
        exit 1
    fi
}

# Function to stop services
stop_dev() {
    print_status "Stopping development environment..."
    docker-compose down
    print_success "Development environment stopped!"
}

# Function to restart services
restart_dev() {
    print_status "Restarting development environment..."
    docker-compose restart
    print_success "Development environment restarted!"
}

# Function to view logs
show_logs() {
    if [ -z "$2" ]; then
        print_status "Showing logs for all services..."
        docker-compose logs -f
    else
        print_status "Showing logs for service: $2"
        docker-compose logs -f "$2"
    fi
}

# Function to rebuild app
rebuild_app() {
    print_status "Rebuilding Flask application..."
    docker-compose build app
    docker-compose up -d app
    print_success "Flask application rebuilt and restarted!"
}

# Function to show status
show_status() {
    print_status "Payment Data AI Application Status"
    echo ""
    
    print_status "Container Status:"
    docker-compose ps
    echo ""
    
    # Check endpoint availability
    print_status "Endpoint Availability:"
    
    # Check backend
    if curl -s -f "http://localhost:5000/health" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ Backend:${NC}  http://localhost:5000 (Ready)"
    else
        echo -e "  ${RED}✗ Backend:${NC}  http://localhost:5000 (Not responding)"
    fi
    
    # Check frontend
    if curl -s -f "http://localhost:3000" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ Frontend:${NC} http://localhost:3000 (Ready)"
    else
        echo -e "  ${RED}✗ Frontend:${NC} http://localhost:3000 (Not responding)"
    fi
    
    echo ""
    print_status "Service Health Checks:"
    echo "  Flask App: $(curl -s http://localhost:5000/health | jq -r '.status' 2>/dev/null || echo 'Not responding')"
    echo "  MySQL: $(docker-compose exec mysql mysqladmin ping -h localhost -u root -p${MYSQL_ROOT_PASSWORD} 2>/dev/null | grep -q 'alive' && echo 'alive' || echo 'not responding')"
    echo "  Redis: $(docker-compose exec redis redis-cli ping 2>/dev/null || echo 'not responding')"
    
    echo ""
    echo -e "${YELLOW}🔧 Development Services:${NC}"
    echo -e "  ${BLUE}MySQL:${NC}   localhost:3306"
    echo -e "  ${BLUE}Redis:${NC}    localhost:6379"
}

# Function to enter app container
shell_app() {
    print_status "Entering Flask app container..."
    docker-compose exec app bash
}

# Function to clean up
cleanup() {
    print_status "Cleaning up Docker resources..."
    docker-compose down -v
    docker system prune -f
    print_success "Cleanup completed!"
}

# Main script logic
case "$1" in
    "start")
        start_dev
        ;;
    "stop")
        stop_dev
        ;;
    "restart")
        restart_dev
        ;;
    "logs")
        show_logs "$@"
        ;;
    "rebuild")
        rebuild_app
        ;;
    "status")
        show_status
        ;;
    "shell")
        shell_app
        ;;
    "cleanup")
        cleanup
        ;;
    *)
        echo "Flask Development Docker Script"
        echo ""
        echo "Usage: $0 {start|stop|restart|logs|rebuild|status|shell|cleanup}"
        echo ""
        echo "Commands:"
        echo "  start    - Build and start all services"
        echo "  stop     - Stop all services"
        echo "  restart  - Restart all services"
        echo "  logs     - Show logs (optionally specify service: logs app)"
        echo "  rebuild  - Rebuild and restart Flask app"
        echo "  status   - Show service status and health"
        echo "  shell    - Enter Flask app container"
        echo "  cleanup  - Stop services and clean up volumes"
        echo ""
        echo "Examples:"
        echo "  $0 start"
        echo "  $0 logs app"
        echo "  $0 status"
        exit 1
        ;;
esac
