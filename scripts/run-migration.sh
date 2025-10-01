#!/bin/bash
set -e

# Source environment and logging utilities
source /scripts/wait-for-mysql.sh
source /scripts/migration-logger.sh

# Migration type from environment variable (default: full)
MIGRATION_TYPE=${MIGRATION_TYPE:-full}

log_info "Starting migration type: $MIGRATION_TYPE"
log_info "Target database: $MYSQL_DATABASE"

# Wait for MySQL to be ready
log_info "Waiting for MySQL to be ready..."
wait_for_mysql

# Function to run SQL file
run_sql_file() {
    local sql_file=$1
    local file_name=$(basename "$sql_file")
    
    log_info "Executing SQL file: $file_name"
    
    if [ ! -f "$sql_file" ]; then
        log_error "SQL file not found: $sql_file"
        exit 1
    fi
    
    # Execute the SQL file
    mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" < "$sql_file"
    
    if [ $? -eq 0 ]; then
        log_info "Successfully executed: $file_name"
    else
        log_error "Failed to execute: $file_name"
        exit 1
    fi
}

# Execute migrations based on type
case $MIGRATION_TYPE in
    "tables")
        log_info "Running tables-only migration"
        run_sql_file "/migrations/payment_tables_migration.sql"
        ;;
    "data")
        log_info "Running test data generation"
        run_sql_file "/migrations/generate_test_data.sql"
        ;;
    "full")
        log_info "Running full migration (tables + test data)"
        run_sql_file "/migrations/payment_tables_migration.sql"
        log_info "Tables created successfully, now generating test data..."
        run_sql_file "/migrations/generate_test_data.sql"
        ;;
    "rollback")
        log_info "Running rollback migration"
        run_sql_file "/migrations/rollback_migration.sql"
        ;;
    "update-attempt-count")
        log_info "Running attempt count update"
        run_sql_file "/migrations/update_attempt_count.sql"
        ;;
    *)
        log_error "Unknown migration type: $MIGRATION_TYPE"
        log_error "Available types: tables, data, full, rollback, update-attempt-count"
        exit 1
        ;;
esac

log_info "Migration completed successfully!"
log_info "Migration type '$MIGRATION_TYPE' finished at $(date)"

# Optional: Show table status
log_info "Showing final database status:"
mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "
    SELECT 
        TABLE_NAME as 'Table',
        TABLE_ROWS as 'Rows',
        ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) as 'Size (MB)'
    FROM information_schema.TABLES 
    WHERE TABLE_SCHEMA = '$MYSQL_DATABASE' 
    ORDER BY TABLE_NAME;
"
