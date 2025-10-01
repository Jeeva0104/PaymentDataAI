import logging
from typing import Tuple, List, Optional

from ..models.response_models import SQLValidationResult
from .common_validator import (
    extract_tables_from_query,
    validate_security_patterns,
    parse_cte_query,
    extract_subqueries,
)

logger = logging.getLogger(__name__)


def validate_table_authorization(tables: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate that all tables are in the allowed list for internal queries
    Returns: (is_valid, error_message)

    TODO: Implement internal-specific table authorization
    Internal queries may have broader table access than merchant queries
    """
    # Placeholder - to be implemented based on internal requirements
    # Internal queries might have access to more tables
    allowed_tables = [
        "payment_intent",
        "payment_attempt",
        "customers",
        "address",
        # TODO: Add additional internal tables as needed
        # "internal_metrics", "system_logs", "audit_trail", etc.
    ]

    for table in tables:
        if table.lower() not in allowed_tables:
            return False, f"Unauthorized table access: {table}"

    return True, None


def is_valid_sql(query: str, req_body_internal_id: str) -> SQLValidationResult:
    """
    Internal-specific SQL validator

    TODO: Implement internal-specific validation logic
    - Less restrictive validation for internal system queries
    - Broader table access patterns
    - Different security requirements for internal use
    - May not require merchant_id filtering for some queries

    Args:
        query: SQL query string to validate
        req_body_internal_id: Internal system ID from request body

    Returns:
        SQLValidationResult with validation status and error message
    """
    # Placeholder implementation
    logger.warning("Internal validator not yet implemented - using basic validation")

    try:
        # Basic input validation
        if not isinstance(query, str) or not isinstance(req_body_internal_id, str):
            return SQLValidationResult(isValid=False, error="Invalid input types")

        if not query.strip():
            return SQLValidationResult(isValid=False, error="Empty query")

        if not req_body_internal_id.strip():
            return SQLValidationResult(isValid=False, error="Empty internal_id value")

        # TODO: Implement full internal validation logic
        # Internal queries might have different validation rules:
        # - May allow queries without WHERE clauses for system monitoring
        # - May allow broader table access
        # - May have different security patterns

        return SQLValidationResult(
            isValid=False, error="Internal validator not implemented"
        )

    except Exception as e:
        logger.error(f"Error in internal validator: {str(e)}")
        return SQLValidationResult(
            isValid=False, error=f"Internal validation error: {str(e)}"
        )


def validate_internal_sql_comprehensive(
    query: str, internal_id: str
) -> SQLValidationResult:
    """
    Comprehensive internal SQL validation using common validator functions

    This is a more complete implementation that uses the common validation
    functions while we work on the full internal validator.

    Args:
        query: SQL query string to validate
        internal_id: Internal system ID from request body

    Returns:
        SQLValidationResult with validation status and error message
    """
    try:
        # Basic input validation
        if not isinstance(query, str) or not isinstance(internal_id, str):
            return SQLValidationResult(isValid=False, error="Invalid input types")

        if not query.strip():
            return SQLValidationResult(isValid=False, error="Empty query")

        if not internal_id.strip():
            return SQLValidationResult(isValid=False, error="Empty internal_id value")

        # Check query length
        if len(query) > 10000:
            return SQLValidationResult(
                isValid=False, error="Query too long (max 10000 characters)"
            )

        # Parse CTE if present
        is_cte, ctes, main_query = parse_cte_query(query)

        if is_cte:
            # Validate each CTE
            cte_names = [cte_name for cte_name, _ in ctes]

            for cte_name, cte_query in ctes:
                # Validate security patterns for each CTE
                is_secure, security_error = validate_security_patterns(
                    cte_query, f"CTE {cte_name}"
                )
                if not is_secure:
                    return SQLValidationResult(isValid=False, error=security_error)

                # Extract and validate tables in CTE
                cte_tables = extract_tables_from_query(cte_query, cte_names)
                table_valid, table_error = validate_table_authorization(cte_tables)
                if not table_valid:
                    return SQLValidationResult(
                        isValid=False, error=f"CTE {cte_name}: {table_error}"
                    )

            # Validate main query
            query_to_validate = main_query
            context = "Main query"
        else:
            # No CTE, validate entire query
            query_to_validate = query
            context = "Query"
            cte_names = []

        # Validate security patterns
        is_secure, security_error = validate_security_patterns(
            query_to_validate, context
        )
        if not is_secure:
            return SQLValidationResult(isValid=False, error=security_error)

        # Extract and validate tables
        tables = extract_tables_from_query(query_to_validate, cte_names)
        table_valid, table_error = validate_table_authorization(tables)
        if not table_valid:
            return SQLValidationResult(isValid=False, error=table_error)

        # Extract and validate subqueries
        subqueries = extract_subqueries(query_to_validate)
        for context, subquery in subqueries:
            # Validate security patterns for each subquery
            is_secure, security_error = validate_security_patterns(subquery, context)
            if not is_secure:
                return SQLValidationResult(isValid=False, error=security_error)

            # Extract and validate tables in subquery
            subquery_tables = extract_tables_from_query(subquery, cte_names)
            table_valid, table_error = validate_table_authorization(subquery_tables)
            if not table_valid:
                return SQLValidationResult(
                    isValid=False, error=f"{context}: {table_error}"
                )

        # If we get here, validation passed
        all_tables = tables.copy()
        if is_cte:
            for _, cte_query in ctes:
                all_tables.extend(extract_tables_from_query(cte_query, cte_names))

        return SQLValidationResult(
            isValid=True,
            validated_tables=list(set(all_tables)),
            warnings=[
                "Using comprehensive validation - full internal validator pending implementation"
            ],
        )

    except Exception as e:
        logger.error(f"Error in comprehensive internal validator: {str(e)}")
        return SQLValidationResult(isValid=False, error=f"Validation error: {str(e)}")
