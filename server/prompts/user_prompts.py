"""
User Context - User query validation and request context formatting
Handles user query validation and request context formatting
"""

import logging
import time
import re
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def is_analytics_related_query(user_query: str) -> Tuple[bool, str]:
    """
    Determine if user query is related to data/analytics

    Args:
        user_query: Natural language query from user

    Returns:
        Tuple[bool, str]: (is_analytics_related, reason/category)
    """

    if not user_query or not user_query.strip():
        return False, "empty_query"

    query_lower = user_query.lower().strip()

    # Check for negative patterns FIRST (they override analytics keywords)
    non_analytics_pattern = _check_non_analytics_patterns(query_lower)
    if non_analytics_pattern:
        return False, f"non_analytics_pattern: {non_analytics_pattern}"

    # Check for positive analytics indicators
    if _check_analytics_keywords(query_lower):
        return True, "analytics_keywords_detected"

    # For ambiguous cases, use simple heuristics
    # If query contains question words + business terms, likely analytics
    question_words = ["what", "how", "when", "where", "which", "who"]
    business_terms = [
        "payment",
        "transaction",
        "customer",
        "merchant",
        "revenue",
        "business",
    ]

    has_question = any(word in query_lower for word in question_words)
    has_business_term = any(term in query_lower for term in business_terms)

    if has_question and has_business_term:
        return True, "question_with_business_context"

    # Default to non-analytics for safety
    return False, "ambiguous_query_defaulted_to_non_analytics"


def _check_analytics_keywords(query: str) -> bool:
    """
    Check for positive analytics indicators

    Args:
        query: Lowercase query string

    Returns:
        bool: True if analytics keywords found
    """

    analytics_keywords = [
        # Data request terms
        "show",
        "display",
        "list",
        "get",
        "fetch",
        "retrieve",
        # Aggregation terms
        "count",
        "total",
        "sum",
        "average",
        "avg",
        "max",
        "min",
        "calculate",
        # Analytics terms
        "analytics",
        "report",
        "dashboard",
        "metrics",
        "statistics",
        "stats",
        # Rate and percentage terms
        "rate",
        "rates", 
        "ratio",
        "ratios",
        "percentage",
        "percent",
        "%",
        "success_rate",
        "failure_rate",
        "conversion_rate",
        "approval_rate",
        "decline_rate",
        "error_rate",
        # Business data terms
        "payment",
        "payments",
        "transaction",
        "transactions",
        "revenue",
        "sales",
        "customer",
        "customers",
        "merchant",
        "merchants",
        "order",
        "orders",
        # Status terms
        "success",
        "successful",
        "failed",
        "failure",
        "conversion",
        "approval",
        "decline",
        "approved",
        "declined",
        "rejected",
        # Payment payment domain terms
        "connector",
        "connectors",
        "gateway",
        "gateways",
        "processor",
        "processors",
        "payment_method",
        "payment_methods",
        "payment method",
        "payment methods",
        "payment_method_type",
        "payment_method_types",
        "payment method type",
        "payment method types",
        "method",
        "methods",
        "type",
        "types",
        "threeds",
        "3ds",
        "three_ds",
        "three-ds",
        "authentication",
        # Comparison terms
        "compare",
        "comparison",
        "versus",
        "vs",
        "between",
        "trend",
        "trends",
        # Time-based terms
        "daily",
        "weekly",
        "monthly",
        "yearly",
        "today",
        "yesterday",
        "last",
        # Data terms
        "data",
        "information",
        "details",
        "breakdown",
        "analysis",
    ]

    return any(keyword in query for keyword in analytics_keywords)


def _check_non_analytics_patterns(query: str) -> Optional[str]:
    """
    Check for negative patterns that indicate non-analytics queries

    Args:
        query: Lowercase query string

    Returns:
        Optional[str]: Pattern name if found, None otherwise
    """

    non_analytics_patterns = [
        # Greetings (must be at start)
        (r"^(hi|hello|hey|good morning|good afternoon|good evening)", "greeting"),
        (r"^(thanks|thank you|bye|goodbye)", "social"),
        # Contact/support (check before general help to be more specific)
        (r"(contact|phone|support team)", "contact_request"),
        # Help requests
        (r"(help|assistance)", "help_request"),
        (r"(how to|how do i|can you help)", "help_request"),
        # General questions about the system/company
        (
            r"(what is|tell me about) (Payment|this system|this platform)",
            "system_info",
        ),
        (
            r"(who are you|what can you do|what are your capabilities)",
            "capability_inquiry",
        ),
        # Completely unrelated topics (check before analytics keywords)
        (r"(weather|joke|story|news|sports)", "unrelated_topic"),
        (r"(recipe|cooking|food|restaurant)", "unrelated_topic"),
        (r"(movie|music|entertainment)", "unrelated_topic"),
        # Test queries
        (r"^(test|testing|hello world)", "test_query"),
    ]

    for pattern, category in non_analytics_patterns:
        if re.search(pattern, query):
            return category

    return None


def _build_non_analytics_context(user_query: str, reason: str) -> str:
    """
    Build context for non-analytics queries

    Args:
        user_query: Original user query
        reason: Classification reason

    Returns:
        str: Non-analytics context with appropriate response
    """

    response_template = get_response_template(reason)

    context_parts = [
        "## Non-Analytics Query Context",
        "",
        f"**Query Type:** NON_ANALYTICS_QUERY",
        f"**Classification Reason:** {reason}",
        f"**User Query:** {user_query}",
        "",
        "## Response:",
        response_template,
        "",
        "## Instructions:",
        "- Do NOT generate SQL queries for this request",
        "- Return the response template above as the final answer",
        "- Do NOT attempt to interpret this as a data request",
    ]

    return "\n".join(context_parts)


def build_user_context(user_query: str) -> str:
    """
    Build user context with query information - fail extensively

    Args:
        user_query: Natural language query from user

    Returns:
        str: User context string

    Raises:
        Exception: If user context validation fails
    """

    start_time = time.time()
    logger.debug(
        f"[USER_FLOW_START] query_length={len(user_query) if user_query else 0}"
    )

    try:
        # Validate inputs
        if not user_query or not user_query.strip():
            raise Exception("User query is empty or invalid")

        # Check if query is analytics-related
        classification_start = time.time()
        is_analytics, reason = is_analytics_related_query(user_query)
        classification_duration = time.time() - classification_start
        logger.debug(
            f"[QUERY_CLASSIFICATION] completed in {classification_duration:.3f}s, result: {is_analytics}, reason: {reason}"
        )

        # Build appropriate context based on classification
        context_start = time.time()
        if not is_analytics:
            logger.info(f"[NON_ANALYTICS_QUERY] {reason}: {user_query}")
            user_context = _build_non_analytics_context(user_query, reason)
        else:
            logger.info(f"[ANALYTICS_QUERY] {reason}: {user_query}")
            user_context = _build_user_request_context(user_query)

        context_duration = time.time() - context_start
        logger.debug(f"[USER_CONTEXT_BUILD] completed in {context_duration:.3f}s")

        total_duration = time.time() - start_time
        logger.info(f"[USER_FLOW_SUCCESS] completed in {total_duration:.3f}s")
        return user_context

    except Exception as e:
        total_duration = time.time() - start_time
        logger.error(f"[USER_FLOW_FAILED] after {total_duration:.3f}s: {e}")
        raise  # Fail extensively


def _build_user_request_context(user_query: str) -> str:
    """
    Build user request context with query information

    Args:
        user_query: Natural language query from user

    Returns:
        str: Formatted user context
    """

    context_parts = [
        "## User Request Context",
        "",
        f"**User Query:** {user_query}",
        "",
        "## Critical Requirements:",
        "- ALWAYS apply appropriate data filtering for security",
        "- NEVER include filtering IDs in SELECT clauses or result sets",
        "- NEVER confuse columns between payment_intent and payment_attempt tables",
        "- ALWAYS use table aliases (pi for payment_intent, pa for payment_attempt) when joining",
        "- ALWAYS prefix columns with table alias when joining tables (pi.status, pa.status)",
        "- For NON-AGGREGATE queries: SELECT comprehensive column sets but EXCLUDE filtering IDs",
        "- For AGGREGATE queries: Apply appropriate analytics calculation based on query intent",
        "- Replace SELECT * with explicit column lists that exclude filtering IDs",
        "- Use exact enum values and exclude specified dropoff statuses",
        "- Use proper JOIN syntax when combining tables",
        "- Include appropriate column aliases for clarity (intent_status, attempt_status)",
        "- Return ONLY the SQL query with no additional text or formatting",
        "- Ensure proper spacing around SQL keywords (especially WHERE, JOIN, ON, AND, OR)",
        "- When in doubt between aggregate vs non-aggregate, prefer explicit column selection without filtering IDs",
    ]

    return "\n".join(context_parts)


def get_response_template(reason: str) -> str:
    """
    Get appropriate response template based on classification reason

    Args:
        reason: Classification reason from query classification

    Returns:
        str: Response template
    """

    if "greeting" in reason or "social" in reason:
        return """Hello! I'm your analytics assistant for Payment. I can help you analyze your payment data and generate insights.

Here are some examples of what you can ask me:
• "Show me total payments for this month"
• "Count successful transactions today"
• "What's my average transaction amount?"
• "Compare this week's revenue to last week"

How can I help you with your payment analytics today?"""

    elif "help_request" in reason or "capability_inquiry" in reason:
        return """I'm here to help you analyze your Payment payment data! I can generate insights and answer questions about your transactions, payments, and revenue.

**What I can help with:**
• Payment analytics and reporting
• Transaction summaries and counts
• Revenue analysis and trends
• Customer and merchant insights
• Time-based comparisons

**Example queries:**
• "Show me payments from last week"
• "Count failed transactions today"
• "What's my total revenue this month?"
• "Compare successful vs failed payments"

**What would you like to analyze?**"""

    elif "system_info" in reason:
        return """I'm your dedicated analytics assistant for the Payment platform. I specialize in helping you understand and analyze your payment data.

**My capabilities:**
• Generate SQL queries for your payment data
• Provide transaction analytics and insights
• Create reports on payment trends and patterns
• Answer questions about your business metrics

**To get started, try asking:**
• "Show me today's payment summary"
• "How many transactions were processed this week?"
• "What's my success rate for payments?"

What payment data would you like to explore?"""

    elif "unrelated_topic" in reason:
        return """I'm specialized in payment analytics for Payment. I can't help with general topics, but I'm great at analyzing your payment data!

**I can help you with:**
• Payment transaction analysis
• Revenue and business metrics
• Success rates and failure analysis
• Customer payment patterns

**Try asking something like:**
• "Show me payment trends"
• "Count transactions by status"
• "What's my revenue breakdown?"

What payment analytics can I help you with?"""

    elif "contact_request" in reason:
        return """For support and contact information, please refer to your Payment dashboard or documentation.

I'm here to help with **payment data analytics**. I can analyze your transactions, generate reports, and provide insights about your payment data.

**I can help you with:**
• Transaction analysis and reporting
• Payment success/failure metrics
• Revenue trends and summaries
• Customer payment insights

**What payment data would you like to analyze?**"""

    elif "query_too_short" in reason:
        return """Your query seems too short. Please provide a more detailed question about your payment data.

**Examples of good queries:**
• "Show me payments from last week"
• "Count successful transactions today"
• "What's my total revenue this month?"
• "Compare failed vs successful payments"

**What payment data would you like to analyze?**"""

    elif "query_too_long" in reason:
        return """Your query is too long. Please shorten it to focus on a specific aspect of your payment data.

**Examples of concise queries:**
• "Show me today's payments"
• "Count failed transactions"
• "Total revenue this week"
• "Payment success rate"

**What payment data would you like to analyze?**"""

    elif "invalid_query_format" in reason:
        return """I detected an invalid query format. Please rephrase your question using natural language.

**Examples of valid queries:**
• "Show me payment transactions"
• "Count successful payments today"
• "What's my revenue breakdown?"
• "Analyze payment trends"

**What payment data would you like to explore?**"""

    elif "missing_query" in reason or "malformed_query" in reason:
        return """Please provide a valid query about your payment data.

**I can help you analyze:**
• Payment transactions and trends
• Revenue and business metrics
• Success rates and failure analysis
• Customer payment patterns

**Example queries:**
• "Show me payments from yesterday"
• "Count transactions by status"
• "What's my average transaction amount?"

**What would you like to analyze?**"""

    elif "query_validation" in reason:
        return """There was an issue with your query. Please try rephrasing it using simple, natural language.

**I can help you with:**
• Payment analytics and reporting
• Transaction summaries and trends
• Revenue analysis
• Success/failure rate analysis

**Example queries:**
• "Show me recent payments"
• "Count today's transactions"
• "What's my total revenue?"

**What payment data would you like to explore?**"""

    else:  # Default for ambiguous or other cases
        return """I'm your Payment  assistant. I help analyze payment data and generate insights about your transactions.

**I can help you with:**
• Payment analytics and reporting
• Transaction summaries and trends
• Revenue analysis
• Success/failure rate analysis

**Example questions:**
• "Show me payments for today"
• "Count successful transactions"
• "What's my total revenue?"
• "Analyze payment trends"

**What payment data would you like to explore?**"""


def handle_non_analytics_query_direct(
    user_query: str,
    reason: str,
    logger_instance: Optional[logging.Logger] = None,
) -> dict:
    """
    Handle non-analytics queries directly without generating full context (OPTIMIZED)

    Args:
        user_query: Original user query
        reason: Classification reason from is_analytics_related_query
        logger_instance: Optional logger instance, uses module logger if None

    Returns:
        dict: Response with guidance message
    """
    # Use provided logger or fall back to module logger
    log = logger_instance if logger_instance else logger

    # Get response template directly based on reason
    try:
        response_template = get_response_template(reason)
    except Exception as e:
        log.warning(f"Failed to get response template for reason '{reason}': {e}")
        # Fallback response
        response_template = """I'm your Payment analytics assistant. I help analyze payment data and generate insights about your transactions.

**I can help you with:**
• Payment analytics and reporting
• Transaction summaries and trends
• Revenue analysis
• Success/failure rate analysis

**What payment data would you like to explore?**"""

    return {
        "response": response_template,
        "status": "success",
        "query_executed": "",  # No SQL executed for non-analytics queries
        "row_count": 0,
    }
