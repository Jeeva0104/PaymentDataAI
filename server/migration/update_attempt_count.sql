-- =====================================================
-- Update Script to Add Missing attempt_count Values
-- This script adds attempt_count values to all payment_intent records
-- that are missing this field in the test data
-- =====================================================

USE payment_system;

-- Update all payment intent records with realistic attempt_count values based on status
UPDATE payment_intent SET attempt_count = CASE
    -- Succeeded payments typically have 1-2 attempts
    WHEN status = 'succeeded' THEN 1
    -- Failed payments typically have 3-5 attempts (multiple retries)
    WHEN status = 'failed' THEN FLOOR(3 + RAND() * 3)
    -- Processing payments typically have 1-3 attempts
    WHEN status = 'processing' THEN FLOOR(1 + RAND() * 3)
    -- Requires customer action typically have 2-4 attempts
    WHEN status = 'requires_customer_action' THEN FLOOR(2 + RAND() * 3)
    -- Requires payment method typically have 1-2 attempts
    WHEN status = 'requires_payment_method' THEN FLOOR(1 + RAND() * 2)
    -- Requires confirmation typically have 1-3 attempts
    WHEN status = 'requires_confirmation' THEN FLOOR(1 + RAND() * 3)
    -- Default to 1 for any other status
    ELSE 1
END
WHERE attempt_count = 0 OR attempt_count IS NULL;

-- Verify the update
SELECT 
    status,
    MIN(attempt_count) as min_attempts,
    MAX(attempt_count) as max_attempts,
    AVG(attempt_count) as avg_attempts,
    COUNT(*) as count
FROM payment_intent 
GROUP BY status 
ORDER BY status;

-- Show attempt count distribution
SELECT 
    attempt_count,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM payment_intent), 2) as percentage
FROM payment_intent 
GROUP BY attempt_count 
ORDER BY attempt_count;

SELECT 'attempt_count values updated successfully for all payment_intent records!' as status;
