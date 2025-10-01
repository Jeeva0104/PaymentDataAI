"""
Common Analytics Context - Shared rules across all context types
Contains SQL generation patterns, table relationships, and universal analytics rules
"""

def get_common_analytics_rules() -> str:
    """
    Returns common analytics rules used across all context types
    
    Returns:
        str: Common analytics context with metrics rules and SQL patterns
    """
    
    return """
## ANALYTICS METRICS CALCULATION GUIDE

### Payment Intent Based Metrics:

**Total Payments Savings:**
- Overall: SUM(amount) WHERE attempt_count > 1 AND status = 'succeeded'
  - Amount saved via Smart Retries (payments that succeeded after retry)
- Without Smart Retries: Always 0 (no smart retries used)
  - Value is 0 when Smart Retries are disabled

**Payments Success Rate:**
- Overall: COUNT(successful intents) / COUNT(total intents excluding dropoffs)
  - successful_intents / total_intents (all intents included & excluding dropoffs)
- Without Smart Retries: COUNT(first attempt success) / COUNT(total intents excluding dropoffs)
  - successful_intents (succeeded on first attempt) / total_intents (all intents included & excluding dropoffs)
- Dropoffs excluded (both categories):
  - RequiresCustomerAction
  - RequiresPaymentMethod
  - RequiresMerchantAction
  - RequiresConfirmation

**Total Payments Processed:**
- Overall: SUM(amount) + COUNT(*) WHERE status = 'succeeded'
  - Total payments processed amount and count based on all successful intents
- Without Smart Retries: SUM(amount) + COUNT(*) WHERE status = 'succeeded' AND attempt_count = 1
  - Payments processed amount and count based on intents which succeeded in first attempt

**Successful Payments Distribution:**
- Without Smart Retries: successful_first_attempts / total_intents
  - Intents succeeded on first attempt divided by total intents (equivalent to all first attempts)
  - Intents succeeded on first attempt / Total Intents
- Dropoffs excluded:
  - RequiresCustomerAction
  - RequiresPaymentMethod
  - RequiresMerchantAction
  - RequiresConfirmation

**Failed Payments Distribution:**
- Without Smart Retries: failed_first_attempts / total_intents
  - Intents which failed on first attempt divided by total Intents
  - Intents with (attempt-count > 1 or attempt-count == 0 and status = failed) / Total Intents
- Dropoffs excluded:
  - RequiresCustomerAction
  - RequiresPaymentMethod
  - RequiresMerchantAction
  - RequiresConfirmation

### Payment Attempt Based Metrics:

**Total Payments Processed:**
- Overall: SUM(amount) + COUNT(*) WHERE status = 'succeeded'
  - Total payments processed amount and count based on all successful attempts
- Without Smart Retries: SUM(amount) + COUNT(*) WHERE status = 'succeeded' AND attempt_count = 1
  - Payments processed amount and count based on successful first attempts

**Successful Payments Distribution:**
- Overall: successful_attempts / total_attempts
  - Overall successful attempts divided by total number of attempts
  - Overall Successful Attempts / Total Attempts
- Without Smart Retries: successful_first_attempts / total_first_attempts
  - Successful First Attempts divided by total first attempts
  - Successful First Attempts / Total First Attempts
- Dropoffs:
  - AuthenticationFailed
  - PaymentMethodAwaited
  - DeviceDataCollectionPending
  - ConfirmationAwaited
  - Unresolved

**Failed Payments Distribution:**
- Overall: failed_attempts / total_attempts
  - Overall failed attempts divided by total number of attempts
  - Overall Failed Attempts / Total Attempts
- Without Smart Retries: failed_first_attempts / total_first_attempts
  - Failed First Attempts divided by total first attempts
  - Failed First Attempts / Total First Attempts
- Dropoffs:
  - AuthenticationFailed
  - PaymentMethodAwaited
  - DeviceDataCollectionPending
  - ConfirmationAwaited
  - Unresolved

**Failure Reasons Distribution:**
- Overall: COUNT(failure_reason) / COUNT(total_failed_attempts) GROUP BY failure_reason
  - Failure Reason count along with ratio of count / total failed attempts based on group by
  - Count of Failure Reason per dimension / Total Failed Attempts
- Without Smart Retries: COUNT(failure_reason) / COUNT(total_failed_first_attempts) GROUP BY failure_reason
  - Failure Reason count based on first attempt along with ratio of count / total failed first attempts
  - Count of Failure Reason (first attempt) per dimension / Total Failed First Attempts

### SQL GENERATION RULES:

1. **ID Column Exclusion:**
   - NEVER include filtering ID columns in SELECT clauses or result sets
   - These IDs are ONLY used for WHERE filtering for security isolation
   - When selecting specific columns: Exclude filtering IDs from the column list
   - When using SELECT *: Replace with explicit column lists excluding filtering IDs

2. **Smart Retries Detection:**
   - "Overall" or no specification: Include all attempts
   - "Without Smart Retries": Add WHERE pi.attempt_count = 1 OR pi.attempt_count IS NULL
   - "Smart Retries savings": Focus on pi.attempt_count > 1

3. **Table Relationships:**
   - Payment Intent Based: Start with payment_intent, LEFT JOIN payment_attempt
   - Payment Attempt Based: Start with payment_attempt, JOIN payment_intent for additional data

4. **Status Exclusions:**
   - Payment Intent dropoffs: NOT IN ('requires_customer_action', 'requires_payment_method', 'requires_merchant_action', 'requires_confirmation')
   - Payment Attempt dropoffs: NOT IN ('authentication_failed', 'payment_method_awaited', 'device_data_collection_pending', 'confirmation_awaited', 'unresolved')

5. **TABLE COLUMN DISAMBIGUATION - CRITICAL:**
   - NEVER confuse columns between payment_intent and payment_attempt tables
   - Always use proper table aliases (pi for payment_intent, pa for payment_attempt)
   - Specify table prefixes for ALL columns when joining tables

   **payment_intent Table Columns:**
   - payment_id (PRIMARY KEY)
   - amount (ONLY in payment_intent, NOT in payment_attempt)
   - currency (ONLY in payment_intent)
   - status (payment_intent status: succeeded, failed, requires_customer_action, etc.)
   - attempt_count (ONLY in payment_intent, retry attempt number)
   - created_at, modified_at (payment_intent timestamps)
   - description, metadata (payment_intent specific fields)

   **payment_attempt Table Columns:**
   - attempt_id (PRIMARY KEY)
   - payment_id (FOREIGN KEY to payment_intent)
   - status (payment_attempt status: succeeded, failed, authentication_failed, etc.)
   - connector (payment processor: stripe, adyen, etc.)
   - error_reason, error_message (attempt-specific error details)
   - created_at, modified_at (attempt timestamps)

   **COMMON COLUMN CONFUSION TO AVOID:**
   - ❌ WRONG: SELECT pa.amount (amount is NOT in payment_attempt)
   - ✅ CORRECT: SELECT pi.amount (amount is in payment_intent)
   
   - ❌ WRONG: SELECT pi.connector (connector is NOT in payment_intent)
   - ✅ CORRECT: SELECT pa.connector (connector is in payment_attempt)
   
   - ❌ WRONG: SELECT pi.error_reason (error_reason is NOT in payment_intent)
   - ✅ CORRECT: SELECT pa.error_reason (error_reason is in payment_attempt)
   
   - ❌ WRONG: SELECT pa.currency (currency is NOT in payment_attempt)
   - ✅ CORRECT: SELECT pi.currency (currency is in payment_intent)
   
   - ❌ WRONG: SELECT pa.attempt_count (attempt_count is NOT in payment_attempt)
   - ✅ CORRECT: SELECT pi.attempt_count (attempt_count is in payment_intent)

   **MANDATORY TABLE ALIASING RULES:**
   - ALWAYS use 'pi' alias for payment_intent
   - ALWAYS use 'pa' alias for payment_attempt
   - ALWAYS prefix columns with table alias when joining: pi.status, pa.status
   - NEVER use ambiguous column references like just 'status' in JOINs

6. **SUBQUERY AND LATERAL JOIN SECURITY RULES - CRITICAL:**
   - EVERY subquery that accesses payment tables MUST include appropriate filtering IDs
   - This applies to: WHERE subqueries, LATERAL joins, CTEs, EXISTS clauses, IN clauses
   - No exceptions - even correlated subqueries need explicit filtering ID filters
   - The SQL validator enforces these rules strictly and will reject queries without proper filtering
   - Every subquery accessing payment_intent, payment_attempt, refund, or dispute tables MUST filter by appropriate ID
   - This prevents data leakage between different security contexts
   - Queries will be rejected if ANY subquery lacks proper ID filtering
   - Always use the same filtering ID value throughout the entire query

7. **QUERY FORMATTING RULES - CRITICAL:**
   - Generate clean SQL queries WITHOUT any comments
   - Do NOT include explanatory comments (-- comments) in the SQL output
   - Do NOT include inline documentation or descriptions
   - Focus on clear, readable SQL structure without commentary
   - Return ONLY executable SQL code
   - Use proper indentation for readability
   - Use meaningful column aliases
   - Structure complex queries with clear line breaks
   - Keep the SQL clean and production-ready

### QUERY INTERPRETATION GUIDELINES:

- **"success rate"** → Payment Intent Based Success Rate
- **"savings"** or **"smart retries"** → Total Payments Savings
- **"distribution"** → Appropriate distribution based on context
- **"without smart retries"** → Filter to attempt_count = 1 only
- **"overall"** or no specification → Include all attempts
- **"failure reasons"** → Failure Reasons Distribution
- **"processed"** → Total Payments Processed

### NON-AGGREGATE QUERY HANDLING:

**Detection Logic:**
- Aggregate keywords: "rate", "total", "count", "sum", "average", "percentage", "distribution" → Use analytics patterns
- Non-aggregate keywords: "show", "list", "get", "find", "view", "display" → Use comprehensive columns
- Default: When unclear, prefer full column selection

**Column Strategy:**
- For non-aggregate queries: SELECT comprehensive columns but EXCLUDE filtering IDs
- Replace SELECT * with explicit column lists excluding filtering IDs
- Always maintain filtering ID security filtering in WHERE clause

### DATE AND TIME HANDLING - ENHANCED RULES:

**Database Format**: All timestamps are in YYYY-MM-DD HH:MM:SS format (e.g., '2024-07-31 12:45:24')

**Date Query Classification - CRITICAL:**

1. **Relative Dates** (Use MySQL date functions):
   - **"yesterday"**: DATE(created_at) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)
   - **"today"**: DATE(created_at) = CURDATE()  
   - **"last 7 days"**: created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
   - **"last week"**: created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
   - **"last month"**: created_at >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)
   - **"this week"**: created_at >= DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY)
   - **"this month"**: created_at >= DATE_FORMAT(CURDATE(), '%Y-%m-01')

2. **Specific Dates** (Parse to absolute timestamps):
   - **Month + Day**: "jul 24", "july 24", "24 jul", "24 july"
   - **Date Ranges**: "jul 24 to jul 25", "between jul 24 and jul 25", "from jul 24 to jul 25"
   - **ISO Format**: "2024-07-24", "2024-07-24 to 2024-07-25"
   - **With Year**: "jul 24 2024", "july 24, 2024"

**Detection Logic:**
- If query contains **month names/abbreviations + day numbers** → Use specific date parsing
- If query contains **relative terms** (yesterday, last, ago, this) → Use MySQL functions
- If query contains **range indicators** (between, to, from) with specific dates → Parse date range
- If ambiguous → Default to relative date handling

**Specific Date Parsing Rules:**
- **Current year assumption**: If no year specified, assume current year (2025)
- **Day boundaries**: Single dates span full day (00:00:00 to 23:59:59)
- **Range boundaries**: Start date at 00:00:00, end date at 23:59:59
- **Month parsing**: Support both abbreviations (jan, feb, jul) and full names (january, february, july)

**Month Name Mappings:**
- **Abbreviations**: jan=1, feb=2, mar=3, apr=4, may=5, jun=6, jul=7, aug=8, sep=9, oct=10, nov=11, dec=12
- **Full Names**: january=1, february=2, march=3, april=4, may=5, june=6, july=7, august=8, september=9, october=10, november=11, december=12

**Date Column References**: created_at, modified_at (in payment_intent, payment_attempt, refund tables)
"""
