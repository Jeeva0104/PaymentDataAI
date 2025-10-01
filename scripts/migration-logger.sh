#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Log levels
LOG_LEVEL=${LOG_LEVEL:-INFO}

# Timestamp function
get_timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

# Generic log function
log_message() {
    local level=$1
    local message=$2
    local color=$3
    local timestamp=$(get_timestamp)
    
    echo -e "${color}[${timestamp}] [${level}] ${message}${NC}"
}

# Info level logging (default)
log_info() {
    log_message "INFO" "$1" "${GREEN}"
}

# Warning level logging
log_warn() {
    log_message "WARN" "$1" "${YELLOW}"
}

# Error level logging
log_error() {
    log_message "ERROR" "$1" "${RED}"
}

# Debug level logging
log_debug() {
    if [ "$LOG_LEVEL" = "DEBUG" ]; then
        log_message "DEBUG" "$1" "${BLUE}"
    fi
}

# Success level logging
log_success() {
    log_message "SUCCESS" "$1" "${GREEN}"
}

# Migration-specific logging functions
log_migration_start() {
    local migration_type=$1
    echo ""
    echo -e "${PURPLE}========================================${NC}"
    echo -e "${PURPLE}  PAYMENT SYSTEM MIGRATION STARTED${NC}"
    echo -e "${PURPLE}========================================${NC}"
    log_info "Migration Type: $migration_type"
    log_info "Started at: $(get_timestamp)"
    echo ""
}

log_migration_end() {
    local migration_type=$1
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  MIGRATION COMPLETED SUCCESSFULLY${NC}"
    echo -e "${GREEN}========================================${NC}"
    log_success "Migration Type: $migration_type"
    log_success "Completed at: $(get_timestamp)"
    echo ""
}

log_migration_error() {
    local migration_type=$1
    local error_message=$2
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}  MIGRATION FAILED${NC}"
    echo -e "${RED}========================================${NC}"
    log_error "Migration Type: $migration_type"
    log_error "Error: $error_message"
    log_error "Failed at: $(get_timestamp)"
    echo ""
}

# Progress indicator
log_progress() {
    local current=$1
    local total=$2
    local description=$3
    local percentage=$((current * 100 / total))
    
    echo -ne "\r${CYAN}Progress: [$current/$total] ($percentage%) - $description${NC}"
    if [ $current -eq $total ]; then
        echo ""
    fi
}

# SQL execution logging
log_sql_start() {
    local sql_file=$1
    log_info "🔄 Executing SQL: $(basename "$sql_file")"
}

log_sql_success() {
    local sql_file=$1
    local duration=$2
    log_success "✅ Completed: $(basename "$sql_file") ${duration:+(${duration}s)}"
}

log_sql_error() {
    local sql_file=$1
    local error_message=$2
    log_error "❌ Failed: $(basename "$sql_file") - $error_message"
}

# Environment info logging
log_environment() {
    log_info "Environment Information:"
    log_info "  MySQL Host: ${MYSQL_HOST:-'not set'}"
    log_info "  MySQL Database: ${MYSQL_DATABASE:-'not set'}"
    log_info "  MySQL User: ${MYSQL_USER:-'not set'}"
    log_info "  Migration Type: ${MIGRATION_TYPE:-'not set'}"
    log_info "  Log Level: ${LOG_LEVEL:-'INFO'}"
}

# Database status logging
log_database_status() {
    log_info "Database Status Check:"
    
    # Check if we can connect and show basic info
    if mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "SELECT 'Connected' as Status;" > /dev/null 2>&1; then
        log_success "✅ Database connection: OK"
        
        # Show table count
        local table_count=$(mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = '$MYSQL_DATABASE';" -N 2>/dev/null || echo "0")
        log_info "📊 Tables in database: $table_count"
        
    else
        log_error "❌ Database connection: FAILED"
    fi
}

# Cleanup function for emergency stops
cleanup_migration() {
    echo ""
    log_warn "🛑 Migration interrupted or stopped"
    log_info "Cleaning up..."
    # Add any cleanup logic here if needed
    exit 1
}

# Trap signals for graceful shutdown
trap cleanup_migration SIGINT SIGTERM

# Banner function
print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    PAYMENT SYSTEM MIGRATION                 ║"
    echo "║                      Database Migration Tool                ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}
