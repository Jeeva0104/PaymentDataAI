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

# Function to build and start services
start_dev() {
    print_status "Starting development environment..."
    check_docker
    
    # Build and start services
    docker-compose up --build -d
    
    print_success "Development environment started!"
    print_status "Services available at:"
    echo "  - Flask App: http://localhost:5000"
    echo "  - MySQL: localhost:3306"
    echo "  - Redis: localhost:6379"
    echo ""
    print_status "To view logs: ./docker-dev.sh logs"
    print_status "To stop: ./docker-dev.sh stop"
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
    print_status "Service status:"
    docker-compose ps
    echo ""
    print_status "Health checks:"
    echo "  Flask App: $(curl -s http://localhost:5000/health | jq -r '.status' 2>/dev/null || echo 'Not responding')"
    echo "  MySQL: $(docker-compose exec mysql mysqladmin ping -h localhost -u root -p${MYSQL_ROOT_PASSWORD} 2>/dev/null | grep -q 'alive' && echo 'alive' || echo 'not responding')"
    echo "  Redis: $(docker-compose exec redis redis-cli ping 2>/dev/null || echo 'not responding')"
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
