-- =====================================================
-- MySQL Migration Script for Payment System
-- Tables: payment_intent, payment_attempt, customers, address
-- Version: 1.0
-- Date: 2025-09-28
-- =====================================================

-- Set session variables for optimal migration
SET foreign_key_checks = 0;
SET sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO';

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS payment_system 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE payment_system;

-- =====================================================
-- DROP EXISTING TABLES (in reverse dependency order)
-- =====================================================

DROP TABLE IF EXISTS payment_attempt;
DROP TABLE IF EXISTS payment_intent;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS address;

-- =====================================================
-- CREATE TABLES
-- =====================================================

-- Address Table
CREATE TABLE address (
    address_id VARCHAR(255) NOT NULL,
    city VARCHAR(255),
    country VARCHAR(255),
    line1 VARCHAR(255),
    line2 VARCHAR(255),
    line3 VARCHAR(255),
    state VARCHAR(255),
    zip VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    phone_number VARCHAR(255),
    country_code VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (address_id),
    INDEX idx_address_created_at (created_at)
) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Customers Table
CREATE TABLE customers (
    customer_id VARCHAR(255) NOT NULL,
    merchant_id VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(255),
    phone_country_code VARCHAR(255),
    description VARCHAR(255),
    address JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON,
    
    PRIMARY KEY (customer_id, merchant_id),
    INDEX idx_customers_created_at (created_at),
    INDEX idx_customers_merchant_id (merchant_id),
    INDEX idx_customers_email (email)
) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Payment Intent Table
CREATE TABLE payment_intent (
    payment_id VARCHAR(255) NOT NULL,
    merchant_id VARCHAR(255) NOT NULL,
    status ENUM(
        'succeeded',
        'failed', 
        'processing',
        'requires_customer_action',
        'requires_payment_method',
        'requires_confirmation'
    ) NOT NULL,
    amount INT NOT NULL,
    currency ENUM(
        'AED', 'ALL', 'AMD', 'ARS', 'AUD', 'AWG', 'AZN', 'BBD', 'BDT', 'BHD', 
        'BMD', 'BND', 'BOB', 'BRL', 'BSD', 'BWP', 'BZD', 'CAD', 'CHF', 'CNY', 
        'COP', 'CRC', 'CUP', 'CZK', 'DKK', 'DOP', 'DZD', 'EGP', 'ETB', 'EUR', 
        'FJD', 'GBP', 'GHS', 'GIP', 'GMD', 'GTQ', 'GYD', 'HKD', 'HNL', 'HRK', 
        'HTG', 'HUF', 'IDR', 'ILS', 'INR', 'JMD', 'JOD', 'JPY', 'KES', 'KGS', 
        'KHR', 'KRW', 'KWD', 'KYD', 'KZT', 'LAK', 'LBP', 'LKR', 'LRD', 'LSL', 
        'MAD', 'MDL', 'MKD', 'MMK', 'MNT', 'MOP', 'MUR', 'MVR', 'MWK', 'MXN', 
        'MYR', 'NAD', 'NGN', 'NIO', 'NOK', 'NPR', 'NZD', 'OMR', 'PEN', 'PGK', 
        'PHP', 'PKR', 'PLN', 'QAR', 'RUB', 'SAR', 'SCR', 'SEK', 'SGD', 'SLL', 
        'SOS', 'SSP', 'SVC', 'SZL', 'THB', 'TTD', 'TWD', 'TZS', 'USD', 'UYU', 
        'UZS', 'YER', 'ZAR'
    ),
    amount_captured INT DEFAULT NULL,
    customer_id VARCHAR(255) DEFAULT NULL,
    description VARCHAR(255) DEFAULT NULL,
    return_url VARCHAR(255) DEFAULT NULL,
    metadata JSON DEFAULT NULL,
    connector_id VARCHAR(255) DEFAULT NULL,
    shipping_address_id VARCHAR(255) DEFAULT NULL,
    billing_address_id VARCHAR(255) DEFAULT NULL,
    statement_descriptor_name VARCHAR(255) DEFAULT NULL,
    statement_descriptor_suffix VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_synced TIMESTAMP DEFAULT NULL,
    setup_future_usage ENUM('on_session', 'off_session') DEFAULT NULL,
    off_session BOOLEAN DEFAULT NULL,
    client_secret VARCHAR(255) DEFAULT NULL,
    attempt_count INT NOT NULL DEFAULT 0,
    
    PRIMARY KEY (payment_id, merchant_id),
    INDEX idx_payment_intent_merchant_id (merchant_id),
    INDEX idx_payment_intent_customer_id (customer_id),
    INDEX idx_payment_intent_status (status),
    INDEX idx_payment_intent_created_at (created_at),
    INDEX idx_payment_intent_currency (currency),
    INDEX idx_payment_intent_amount (amount),
    INDEX idx_payment_intent_attempt_count (attempt_count)
) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Payment Attempt Table
CREATE TABLE payment_attempt (
    payment_id VARCHAR(255) NOT NULL,
    merchant_id VARCHAR(255) NOT NULL,
    txn_id VARCHAR(255) NOT NULL,
    status ENUM(
        'started',
        'authentication_failed',
        'pending_vbv',
        'vbv_successful',
        'authorized',
        'authorization_failed',
        'charged',
        'authorizing',
        'cod_initiated',
        'voided',
        'void_initiated',
        'capture_initiated',
        'capture_failed',
        'void_failed',
        'auto_refunded',
        'partial_charged',
        'pending',
        'failure',
        'payment_method_awaited',
        'confirmation_awaited'
    ) NOT NULL,
    amount INT NOT NULL,
    currency ENUM(
        'AED', 'ALL', 'AMD', 'ARS', 'AUD', 'AWG', 'AZN', 'BBD', 'BDT', 'BHD', 
        'BMD', 'BND', 'BOB', 'BRL', 'BSD', 'BWP', 'BZD', 'CAD', 'CHF', 'CNY', 
        'COP', 'CRC', 'CUP', 'CZK', 'DKK', 'DOP', 'DZD', 'EGP', 'ETB', 'EUR', 
        'FJD', 'GBP', 'GHS', 'GIP', 'GMD', 'GTQ', 'GYD', 'HKD', 'HNL', 'HRK', 
        'HTG', 'HUF', 'IDR', 'ILS', 'INR', 'JMD', 'JOD', 'JPY', 'KES', 'KGS', 
        'KHR', 'KRW', 'KWD', 'KYD', 'KZT', 'LAK', 'LBP', 'LKR', 'LRD', 'LSL', 
        'MAD', 'MDL', 'MKD', 'MMK', 'MNT', 'MOP', 'MUR', 'MVR', 'MWK', 'MXN', 
        'MYR', 'NAD', 'NGN', 'NIO', 'NOK', 'NPR', 'NZD', 'OMR', 'PEN', 'PGK', 
        'PHP', 'PKR', 'PLN', 'QAR', 'RUB', 'SAR', 'SCR', 'SEK', 'SGD', 'SLL', 
        'SOS', 'SSP', 'SVC', 'SZL', 'THB', 'TTD', 'TWD', 'TZS', 'USD', 'UYU', 
        'UZS', 'YER', 'ZAR'
    ) DEFAULT NULL,
    save_to_locker BOOLEAN DEFAULT NULL,
    connector VARCHAR(255) NOT NULL,
    error_message TEXT DEFAULT NULL,
    offer_amount INT DEFAULT NULL,
    surcharge_amount INT DEFAULT NULL,
    tax_amount INT DEFAULT NULL,
    payment_method_id VARCHAR(255) DEFAULT NULL,
    payment_method ENUM(
        'card',
        'bank_transfer',
        'netbanking',
        'upi',
        'open_banking',
        'consumer_finance',
        'wallet',
        'payment_container',
        'bank_debit',
        'pay_later'
    ) DEFAULT NULL,
    payment_flow ENUM(
        'vsc',
        'emi',
        'otp',
        'upi_intent',
        'upi_collect',
        'upi_scan_and_pay',
        'sdk'
    ) DEFAULT NULL,
    redirect BOOLEAN DEFAULT NULL,
    connector_transaction_id VARCHAR(255) DEFAULT NULL,
    capture_method ENUM('automatic', 'manual', 'scheduled') DEFAULT NULL,
    capture_on TIMESTAMP DEFAULT NULL,
    confirm BOOLEAN NOT NULL,
    authentication_type ENUM('three_ds', 'no_three_ds') DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_synced TIMESTAMP DEFAULT NULL,
    
    PRIMARY KEY (payment_id, merchant_id, txn_id),
    INDEX idx_payment_attempt_merchant_id (merchant_id),
    INDEX idx_payment_attempt_status (status),
    INDEX idx_payment_attempt_connector (connector),
    INDEX idx_payment_attempt_created_at (created_at),
    INDEX idx_payment_attempt_payment_method (payment_method),
    INDEX idx_payment_attempt_amount (amount)
) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- =====================================================
-- ADD FOREIGN KEY CONSTRAINTS
-- =====================================================

-- Add foreign key constraints after all tables are created
ALTER TABLE payment_intent 
ADD CONSTRAINT fk_payment_intent_customer 
FOREIGN KEY (customer_id, merchant_id) 
REFERENCES customers(customer_id, merchant_id) 
ON DELETE CASCADE;

ALTER TABLE payment_intent 
ADD CONSTRAINT fk_payment_intent_shipping 
FOREIGN KEY (shipping_address_id) 
REFERENCES address(address_id) 
ON DELETE SET NULL;

ALTER TABLE payment_intent 
ADD CONSTRAINT fk_payment_intent_billing 
FOREIGN KEY (billing_address_id) 
REFERENCES address(address_id) 
ON DELETE SET NULL;

ALTER TABLE payment_attempt 
ADD CONSTRAINT fk_payment_attempt_intent 
FOREIGN KEY (payment_id, merchant_id) 
REFERENCES payment_intent(payment_id, merchant_id) 
ON DELETE CASCADE;

-- =====================================================
-- ENABLE FOREIGN KEY CHECKS
-- =====================================================

SET foreign_key_checks = 1;

-- =====================================================
-- VERIFICATION QUERIES
-- =====================================================

-- Verify table creation
SELECT 
    TABLE_NAME,
    ENGINE,
    TABLE_COLLATION,
    TABLE_ROWS
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'payment_system'
AND TABLE_NAME IN ('address', 'customers', 'payment_intent', 'payment_attempt');

-- Verify indexes
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    COLUMN_NAME,
    NON_UNIQUE
FROM information_schema.STATISTICS 
WHERE TABLE_SCHEMA = 'payment_system'
AND TABLE_NAME IN ('payment_intent', 'payment_attempt')
ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;

-- Verify foreign key constraints
SELECT 
    CONSTRAINT_NAME,
    TABLE_NAME,
    COLUMN_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE 
WHERE TABLE_SCHEMA = 'payment_system'
AND REFERENCED_TABLE_NAME IS NOT NULL;

-- =====================================================
-- SAMPLE INSERT STATEMENTS (for testing)
-- =====================================================

-- Sample address
INSERT INTO address (address_id, city, country, line1, first_name, last_name) 
VALUES ('addr_001', 'Mumbai', 'India', '123 Main Street', 'John', 'Doe');

-- Sample customer
INSERT INTO customers (customer_id, merchant_id, name, email) 
VALUES ('cust_001', 'merch_001', 'John Doe', 'john.doe@example.com');

-- Sample payment intent
INSERT INTO payment_intent (payment_id, merchant_id, status, amount, currency, customer_id, description, attempt_count) 
VALUES ('pay_001', 'merch_001', 'processing', 10000, 'INR', 'cust_001', 'Test payment', 1);

-- Sample payment attempt
INSERT INTO payment_attempt (payment_id, merchant_id, txn_id, status, amount, currency, connector, confirm) 
VALUES ('pay_001', 'merch_001', 'txn_001', 'started', 10000, 'INR', 'stripe', true);

-- =====================================================
-- CLEANUP TEST DATA (uncomment to remove test data)
-- =====================================================

-- DELETE FROM payment_attempt WHERE payment_id = 'pay_001';
-- DELETE FROM payment_intent WHERE payment_id = 'pay_001';
-- DELETE FROM customers WHERE customer_id = 'cust_001';
-- DELETE FROM address WHERE address_id = 'addr_001';

-- =====================================================
-- MIGRATION COMPLETE
-- =====================================================

SELECT 'Migration completed successfully!' as status;
