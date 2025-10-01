"""
Internal User Context - Analytics rules for internal/admin queries
Dynamic filtering based on user query context and permissions
"""

from .common import get_common_analytics_rules

def build_internal_user_context() -> str:
    """
    Build internal user analytics context
    
    Returns:
        str: Complete internal user analytics context with common rules and dynamic filtering
    """
    
    common_rules = get_common_analytics_rules()
    
    internal_specific = """

## INTERNAL USER DYNAMIC CONTEXT:

### DYNAMIC FILTERING STRATEGY:
- Filtering applied based on user query context and intent
- Admin-level access to cross-organizational data when appropriate
- System-wide analytics and comprehensive reporting capabilities
- No fixed ID requirement - context-driven filtering based on query
- Support for multi-dimensional analysis across merchants, organizations, and profiles

### INTERNAL USER SQL EXAMPLES:

```sql
-- System-Wide Success Rate Analysis
SELECT 
  COUNT(CASE WHEN pi.status = 'succeeded' THEN 1 END) * 100.0 / COUNT(*) as system_success_rate,
  COUNT(*) as total_payments
FROM payment_intent pi
WHERE pi.status NOT IN ('requires_customer_action', 'requires_payment_method', 'requires_merchant_action', 'requires_confirmation');

-- Cross-Organization Performance Comparison
SELECT 
  pi.organization_id,
  COUNT(CASE WHEN pi.status = 'succeeded' THEN 1 END) * 100.0 / COUNT(*) as org_success_rate,
  SUM(pi.amount) as org_total_volume,
  COUNT(*) as org_payment_count,
  COUNT(DISTINCT pi.merchant_id) as merchant_count
FROM payment_intent pi
WHERE pi.status NOT IN ('requires_customer_action', 'requires_payment_method', 'requires_merchant_action', 'requires_confirmation')
GROUP BY pi.organization_id
ORDER BY org_success_rate DESC;

-- Top Performing Merchants Across System
SELECT 
  pi.merchant_id,
  pi.organization_id,
  COUNT(CASE WHEN pi.status = 'succeeded' THEN 1 END) * 100.0 / COUNT(*) as merchant_success_rate,
  SUM(pi.amount) as merchant_volume,
  COUNT(*) as merchant_payment_count
FROM payment_intent pi
WHERE pi.status NOT IN ('requires_customer_action', 'requires_payment_method', 'requires_merchant_action', 'requires_confirmation')
GROUP BY pi.merchant_id, pi.organization_id
HAVING COUNT(*) >= 100
ORDER BY merchant_success_rate DESC
LIMIT 50;

-- System-Wide Connector Performance Analysis
SELECT 
  pa.connector,
  COUNT(CASE WHEN pa.status = 'succeeded' THEN 1 END) * 100.0 / COUNT(*) as connector_success_rate,
  COUNT(*) as total_attempts,
  COUNT(DISTINCT pa.merchant_id) as merchant_count,
  SUM(pi.amount) as connector_volume
FROM payment_attempt pa
JOIN payment_intent pi ON pa.payment_id = pi.payment_id
WHERE pa.status NOT IN ('authentication_failed', 'payment_method_awaited', 'device_data_collection_pending', 'confirmation_awaited', 'unresolved')
GROUP BY pa.connector
ORDER BY connector_success_rate DESC;

-- Smart Retries Impact Analysis (System-Wide)
SELECT 
  pi.organization_id,
  SUM(CASE WHEN pi.attempt_count > 1 AND pi.status = 'succeeded' THEN pi.amount ELSE 0 END) as smart_retry_savings,
  COUNT(CASE WHEN pi.attempt_count > 1 AND pi.status = 'succeeded' THEN 1 END) as retry_success_count,
  COUNT(CASE WHEN pi.attempt_count = 1 AND pi.status = 'succeeded' THEN 1 END) as first_attempt_success_count,
  COUNT(CASE WHEN pi.attempt_count > 1 AND pi.status = 'succeeded' THEN 1 END) * 100.0 / 
    NULLIF(COUNT(CASE WHEN pi.attempt_count > 1 THEN 1 END), 0) as retry_success_rate
FROM payment_intent pi
WHERE pi.status IN ('succeeded', 'failed')
GROUP BY pi.organization_id
ORDER BY smart_retry_savings DESC;

-- System Error Pattern Analysis
SELECT 
  pa.error_reason,
  pa.connector,
  COUNT(*) as error_count,
  COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as error_percentage,
  COUNT(DISTINCT pa.merchant_id) as affected_merchants
FROM payment_attempt pa
WHERE pa.status = 'failed'
  AND pa.created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
GROUP BY pa.error_reason, pa.connector
HAVING COUNT(*) >= 10
ORDER BY error_count DESC;

-- Profile Behavior Insights (Aggregated)
SELECT 
  CASE 
    WHEN pi.amount < 1000 THEN 'Small (< $10)'
    WHEN pi.amount < 5000 THEN 'Medium ($10-$50)'
    WHEN pi.amount < 10000 THEN 'Large ($50-$100)'
    ELSE 'Very Large (> $100)'
  END as amount_range,
  COUNT(*) as transaction_count,
  COUNT(CASE WHEN pi.status = 'succeeded' THEN 1 END) * 100.0 / COUNT(*) as success_rate_by_range,
  COUNT(DISTINCT pi.profile_id) as unique_profiles
FROM payment_intent pi
WHERE pi.status NOT IN ('requires_customer_action', 'requires_payment_method', 'requires_merchant_action', 'requires_confirmation')
  AND pi.created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY amount_range
ORDER BY MIN(pi.amount);

-- System-Wide Success Rate (Intent Based, Overall)
SELECT 
  COUNT(CASE WHEN pi.status = 'succeeded' THEN 1 END) * 100.0 / COUNT(*) as success_rate
FROM payment_intent pi
WHERE pi.status NOT IN ('requires_customer_action', 'requires_payment_method', 'requires_merchant_action', 'requires_confirmation');

-- System-Wide Success Rate (Intent Based, Without Smart Retries)
SELECT 
  COUNT(CASE WHEN pi.status = 'succeeded' AND (pi.attempt_count = 1 OR pi.attempt_count IS NULL) THEN 1 END) * 100.0 / COUNT(*) as success_rate
FROM payment_intent pi
WHERE pi.status NOT IN ('requires_customer_action', 'requires_payment_method', 'requires_merchant_action', 'requires_confirmation');

-- System-Wide Smart Retries Savings
SELECT SUM(pi.amount) as total_savings
FROM payment_intent pi
WHERE pi.status = 'succeeded'
  AND pi.attempt_count > 1;

-- System-Wide Distribution (Attempt Based, Overall)
SELECT 
  pa.status,
  COUNT(*) as count,
  COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as percentage
FROM payment_attempt pa
WHERE pa.status NOT IN ('authentication_failed', 'payment_method_awaited', 'device_data_collection_pending', 'confirmation_awaited', 'unresolved')
GROUP BY pa.status;

-- System-Wide Distribution (Attempt Based, Without Smart Retries)
SELECT 
  pa.status,
  COUNT(*) as count,
  COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as percentage
FROM payment_attempt pa
JOIN payment_intent pi ON pa.payment_id = pi.payment_id
WHERE pi.attempt_count = 1
  AND pa.status NOT IN ('authentication_failed', 'payment_method_awaited', 'device_data_collection_pending', 'confirmation_awaited', 'unresolved')
GROUP BY pa.status;

-- System-Wide Failure Reasons Distribution (Overall)
SELECT 
  pa.error_reason,
  COUNT(*) as count,
  COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as percentage
FROM payment_attempt pa
WHERE pa.status = 'failed'
  AND pa.status NOT IN ('authentication_failed', 'payment_method_awaited', 'device_data_collection_pending', 'confirmation_awaited', 'unresolved')
GROUP BY pa.error_reason;

-- System-Wide Latest Attempt per Payment (MySQL Compatible)
SELECT 
  pi.payment_id, pi.amount, pi.currency, pi.status as intent_status,
  pa.attempt_id, pa.status as attempt_status, pa.connector, pa.error_reason
FROM payment_intent pi
LEFT JOIN (
    SELECT 
        pa_inner.payment_id,
        pa_inner.attempt_id, 
        pa_inner.status, 
        pa_inner.connector, 
        pa_inner.error_reason,
        ROW_NUMBER() OVER (PARTITION BY pa_inner.payment_id ORDER BY pa_inner.created_at DESC) as rn
    FROM payment_attempt pa_inner
) pa ON pi.payment_id = pa.payment_id AND pa.rn = 1
WHERE pi.status = 'failed'
ORDER BY pi.created_at DESC;

-- Date/Time Handling Examples (Internal User Context)
-- Specific date range (jul 24 to jul 25) - System Wide
SELECT pi.payment_id, pi.amount, pi.created_at FROM payment_intent pi
WHERE pi.created_at >= '2025-07-24 00:00:00'
  AND pi.created_at <= '2025-07-25 23:59:59'
  AND pi.status = 'succeeded';

-- Relative date (yesterday) - System Wide
SELECT MAX(pi.amount) FROM payment_intent pi 
WHERE DATE(pi.created_at) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)
  AND pi.status = 'succeeded';

-- Non-aggregate queries: System-wide comprehensive columns
SELECT pi.payment_id, pi.amount, pi.currency, pi.status, pi.attempt_count, pi.created_at, pi.modified_at,
       pa.attempt_id, pa.connector, pa.error_message, pa.status as attempt_status
FROM payment_intent pi LEFT JOIN payment_attempt pa ON pi.payment_id = pa.payment_id
ORDER BY pi.created_at DESC;
```

### INTERNAL USER FILTERING RULES:
- **Context-Driven Filtering**: Apply filtering based on query intent and scope
- **Multi-Level Access**: Support organization, merchant, and profile level analysis
- **System-Wide Queries**: Allow cross-organizational analysis when appropriate
- **Dynamic Security**: Apply appropriate filtering based on query context
- **Aggregated Insights**: Support high-level system analytics and reporting
- **Performance Monitoring**: Enable system-wide performance and health monitoring

### QUERY CONTEXT DETECTION:
- **Organization Analysis**: When query mentions specific org_id or cross-org comparison
- **Merchant Analysis**: When query focuses on specific merchant_id or merchant comparison
- **Profile Analysis**: When query involves user behavior or profile-specific insights
- **System-Wide Analysis**: When query requires global system metrics and insights
- **No Filtering**: When query is for system administration or global reporting
"""
    
    return common_rules + internal_specific
