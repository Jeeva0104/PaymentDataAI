#!/bin/bash

# MySQL connection configuration
MYSQL_HOST=${MYSQL_HOST:-mysql}
MYSQL_USER=${MYSQL_USER:-root}
MYSQL_PASSWORD=${MYSQL_PASSWORD}
MYSQL_DATABASE=${MYSQL_DATABASE}

# Connection retry configuration
MAX_RETRIES=${MYSQL_MAX_RETRIES:-30}
RETRY_INTERVAL=${MYSQL_RETRY_INTERVAL:-2}

# Function to check MySQL connectivity
check_mysql_connection() {
    mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1;" > /dev/null 2>&1
    return $?
}

# Function to check if database exists
check_database_exists() {
    mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "USE $MYSQL_DATABASE;" > /dev/null 2>&1
    return $?
}

# Main wait function
wait_for_mysql() {
    local retries=0
    
    echo "Waiting for MySQL server to be ready..."
    echo "Host: $MYSQL_HOST"
    echo "User: $MYSQL_USER"
    echo "Database: $MYSQL_DATABASE"
    echo "Max retries: $MAX_RETRIES"
    echo "Retry interval: ${RETRY_INTERVAL}s"
    echo ""
    
    # Wait for MySQL server to be responsive
    while [ $retries -lt $MAX_RETRIES ]; do
        if check_mysql_connection; then
            echo "✓ MySQL server is responsive"
            break
        else
            retries=$((retries + 1))
            echo "⏳ Attempt $retries/$MAX_RETRIES: MySQL not ready, waiting ${RETRY_INTERVAL}s..."
            sleep $RETRY_INTERVAL
        fi
    done
    
    if [ $retries -eq $MAX_RETRIES ]; then
        echo "❌ Failed to connect to MySQL after $MAX_RETRIES attempts"
        echo "Connection details:"
        echo "  Host: $MYSQL_HOST"
        echo "  User: $MYSQL_USER"
        echo "  Database: $MYSQL_DATABASE"
        exit 1
    fi
    
    # Wait for database to be available
    retries=0
    echo "Waiting for database '$MYSQL_DATABASE' to be available..."
    
    while [ $retries -lt $MAX_RETRIES ]; do
        if check_database_exists; then
            echo "✓ Database '$MYSQL_DATABASE' is available"
            break
        else
            retries=$((retries + 1))
            echo "⏳ Attempt $retries/$MAX_RETRIES: Database not ready, waiting ${RETRY_INTERVAL}s..."
            sleep $RETRY_INTERVAL
        fi
    done
    
    if [ $retries -eq $MAX_RETRIES ]; then
        echo "❌ Database '$MYSQL_DATABASE' not available after $MAX_RETRIES attempts"
        echo "Creating database if it doesn't exist..."
        
        # Try to create database
        if mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS $MYSQL_DATABASE;"; then
            echo "✓ Database '$MYSQL_DATABASE' created successfully"
        else
            echo "❌ Failed to create database '$MYSQL_DATABASE'"
            exit 1
        fi
    fi
    
    echo "✅ MySQL is ready for migrations!"
    echo ""
    
    # Show MySQL version and status
    echo "MySQL Server Information:"
    mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "
        SELECT 
            VERSION() as 'MySQL Version',
            NOW() as 'Current Time',
            DATABASE() as 'Current Database';
    "
    echo ""
}

# Function to test connection (can be called independently)
test_mysql_connection() {
    echo "Testing MySQL connection..."
    if check_mysql_connection; then
        echo "✓ Connection successful"
        if check_database_exists; then
            echo "✓ Database '$MYSQL_DATABASE' exists"
        else
            echo "⚠ Database '$MYSQL_DATABASE' does not exist"
        fi
    else
        echo "❌ Connection failed"
        return 1
    fi
}
