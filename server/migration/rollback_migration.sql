-- =====================================================
-- MySQL Rollback Script for Payment System
-- Purpose: Safely remove payment system tables
-- Version: 1.0
-- Date: 2025-09-28
-- =====================================================

-- WARNING: This script will permanently delete all data in the payment system tables
-- Make sure you have a backup before running this script

-- Set session variables
SET foreign_key_checks = 0;

-- Use the payment_system database
USE payment_system;

-- =====================================================
-- BACKUP VERIFICATION (Optional - uncomment to check data before deletion)
-- =====================================================

-- Check if tables exist and have data
-- SELECT 'payment_attempt' as table_name, COUNT(*) as record_count FROM payment_attempt
-- UNION ALL
-- SELECT 'payment_intent' as table_name, COUNT(*) as record_count FROM payment_intent  
-- UNION ALL
-- SELECT 'customers' as table_name, COUNT(*) as record_count FROM customers
-- UNION ALL
-- SELECT 'address' as table_name, COUNT(*) as record_count FROM address;

-- =====================================================
-- DROP FOREIGN KEY CONSTRAINTS FIRST
-- =====================================================

-- Drop foreign key constraints to avoid dependency issues
ALTER TABLE payment_attempt DROP FOREIGN KEY IF EXISTS fk_payment_attempt_intent;
ALTER TABLE payment_intent DROP FOREIGN KEY IF EXISTS fk_payment_intent_customer;
ALTER TABLE payment_intent DROP FOREIGN KEY IF EXISTS fk_payment_intent_shipping;
ALTER TABLE payment_intent DROP FOREIGN KEY IF EXISTS fk_payment_intent_billing;

-- =====================================================
-- DROP TABLES (in reverse dependency order)
-- =====================================================

-- Drop payment_attempt table (depends on payment_intent)
DROP TABLE IF EXISTS payment_attempt;
SELECT 'Dropped payment_attempt table' as status;

-- Drop payment_intent table (depends on customers and address)
DROP TABLE IF EXISTS payment_intent;
SELECT 'Dropped payment_intent table' as status;

-- Drop customers table (independent)
DROP TABLE IF EXISTS customers;
SELECT 'Dropped customers table' as status;

-- Drop address table (independent)
DROP TABLE IF EXISTS address;
SELECT 'Dropped address table' as status;

-- =====================================================
-- VERIFY CLEANUP
-- =====================================================

-- Check that tables are removed
SELECT 
    TABLE_NAME,
    TABLE_TYPE
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'payment_system'
AND TABLE_NAME IN ('address', 'customers', 'payment_intent', 'payment_attempt');

-- If the above query returns no rows, the rollback was successful

-- =====================================================
-- OPTIONAL: DROP DATABASE (uncomment if you want to remove the entire database)
-- =====================================================

-- WARNING: This will remove the entire payment_system database
-- Only uncomment if you want to completely remove everything

-- DROP DATABASE IF EXISTS payment_system;
-- SELECT 'Dropped payment_system database' as status;

-- =====================================================
-- RE-ENABLE FOREIGN KEY CHECKS
-- =====================================================

SET foreign_key_checks = 1;

-- =====================================================
-- ROLLBACK COMPLETE
-- =====================================================

SELECT 'Rollback completed successfully!' as status;
SELECT 'All payment system tables have been removed.' as message;
