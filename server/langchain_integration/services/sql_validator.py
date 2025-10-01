"""
SQL Validator Service

Validates generated SQL queries using the internal validation methods.
Integrates with the existing validation logic for security and authorization checks.
"""

import logging
import time
from typing import Optional

from ..models.response_models import (
    SQLValidationResult,
    SQLValidationError,
    ValidationConfig
)
from ..validators.internal_validator import (
    is_valid_sql,
    validate_internal_sql_comprehensive
)

logger = logging.getLogger(__name__)


class SQLValidatorService:
    """Service for validating SQL queries using internal validation logic"""
    
    def __init__(self, config: Optional[ValidationConfig] = None):
        """
        Initialize SQL Validator Service
        
        Args:
            config: Validation configuration, uses defaults if None
        """
        self.config = config or ValidationConfig()
        logger.info("SQL Validator Service initialized")
    
    def validate_sql(self, sql_query: str, internal_id: str = "system") -> SQLValidationResult:
        """
        Validate SQL query using internal validation methods
        
        Args:
            sql_query: SQL query string to validate
            internal_id: Internal system ID for validation context
            
        Returns:
            SQLValidationResult with validation status and details
        """
        start_time = time.time()
        
        try:
            logger.info("[SQL_VALIDATOR] Starting SQL validation")
            
            # Basic input validation
            if not sql_query or not sql_query.strip():
                return SQLValidationResult(
                    isValid=False,
                    error="Empty SQL query provided"
                )
            
            if not internal_id or not internal_id.strip():
                internal_id = "system"  # Default fallback
            
            # Check query length
            if len(sql_query) > self.config.max_query_length:
                return SQLValidationResult(
                    isValid=False,
                    error=f"Query too long (max {self.config.max_query_length} characters)"
                )
            
            logger.debug(f"[SQL_VALIDATOR] Validating query: {sql_query[:100]}...")
            
            # Use comprehensive validation as primary method
            # This provides better validation coverage while the full internal validator is pending
            validation_result = validate_internal_sql_comprehensive(sql_query, internal_id)
            
            # If comprehensive validation fails, try the basic internal validator as fallback
            if not validation_result.isValid and self.config.enable_security_checks:
                logger.debug("[SQL_VALIDATOR] Comprehensive validation failed, trying basic validator")
                basic_result = is_valid_sql(sql_query, internal_id)
                
                # If basic validator gives a different result, log it but use comprehensive result
                if basic_result.isValid != validation_result.isValid:
                    logger.warning(
                        f"[SQL_VALIDATOR] Validation mismatch - "
                        f"Comprehensive: {validation_result.isValid}, Basic: {basic_result.isValid}"
                    )
            
            # Calculate validation time
            validation_time_ms = (time.time() - start_time) * 1000
            
            if validation_result.isValid:
                logger.info(f"[SQL_VALIDATOR] SQL validation passed in {validation_time_ms:.2f}ms")
                if validation_result.validated_tables:
                    logger.debug(f"[SQL_VALIDATOR] Validated tables: {validation_result.validated_tables}")
            else:
                logger.warning(f"[SQL_VALIDATOR] SQL validation failed in {validation_time_ms:.2f}ms: {validation_result.error}")
            
            return validation_result
            
        except Exception as e:
            validation_time_ms = (time.time() - start_time) * 1000
            error_msg = f"SQL validation error: {str(e)}"
            
            logger.error(f"[SQL_VALIDATOR] {error_msg} (after {validation_time_ms:.2f}ms)")
            
            return SQLValidationResult(
                isValid=False,
                error=error_msg
            )
    
    def validate_sql_with_context(self, sql_query: str, context: dict) -> SQLValidationResult:
        """
        Validate SQL query with additional context information
        
        Args:
            sql_query: SQL query string to validate
            context: Additional context (session_id, user_info, etc.)
            
        Returns:
            SQLValidationResult with validation status and details
        """
        try:
            # Extract internal_id from context or use default
            internal_id = context.get('internal_id', context.get('session_id', 'system'))
            
            # Add context-specific validation logic here if needed
            # For now, use the standard validation
            result = self.validate_sql(sql_query, internal_id)
            
            # Add context information to warnings if available
            if result.isValid and context:
                context_info = []
                if 'session_id' in context:
                    context_info.append(f"Session: {context['session_id']}")
                if 'user_query' in context:
                    context_info.append(f"Query type: {self._classify_user_query(context['user_query'])}")
                
                if context_info:
                    if not result.warnings:
                        result.warnings = []
                    result.warnings.extend(context_info)
            
            return result
            
        except Exception as e:
            logger.error(f"[SQL_VALIDATOR] Context validation error: {e}")
            return SQLValidationResult(
                isValid=False,
                error=f"Context validation error: {str(e)}"
            )
    
    def _classify_user_query(self, user_query: str) -> str:
        """
        Classify the type of user query for context
        
        Args:
            user_query: Original user query
            
        Returns:
            Query classification string
        """
        if not user_query:
            return "unknown"
        
        query_lower = user_query.lower()
        
        if any(word in query_lower for word in ['count', 'total', 'sum', 'average']):
            return "aggregation"
        elif any(word in query_lower for word in ['trend', 'over time', 'daily', 'monthly']):
            return "trend_analysis"
        elif any(word in query_lower for word in ['top', 'best', 'worst', 'highest', 'lowest']):
            return "ranking"
        elif any(word in query_lower for word in ['compare', 'vs', 'versus', 'difference']):
            return "comparison"
        else:
            return "general"
    
    def batch_validate(self, sql_queries: list, internal_id: str = "system") -> list:
        """
        Validate multiple SQL queries in batch
        
        Args:
            sql_queries: List of SQL query strings
            internal_id: Internal system ID for validation context
            
        Returns:
            List of SQLValidationResult objects
        """
        results = []
        
        logger.info(f"[SQL_VALIDATOR] Starting batch validation of {len(sql_queries)} queries")
        
        for i, sql_query in enumerate(sql_queries):
            try:
                result = self.validate_sql(sql_query, f"{internal_id}_batch_{i}")
                results.append(result)
            except Exception as e:
                logger.error(f"[SQL_VALIDATOR] Batch validation error for query {i}: {e}")
                results.append(SQLValidationResult(
                    isValid=False,
                    error=f"Batch validation error: {str(e)}"
                ))
        
        # Summary logging
        valid_count = sum(1 for r in results if r.isValid)
        logger.info(f"[SQL_VALIDATOR] Batch validation complete: {valid_count}/{len(sql_queries)} valid")
        
        return results
    
    def update_config(self, new_config: ValidationConfig) -> None:
        """
        Update validation configuration
        
        Args:
            new_config: New validation configuration
        """
        self.config = new_config
        logger.info("SQL Validator configuration updated")
    
    def get_validation_stats(self) -> dict:
        """
        Get validation statistics (placeholder for future implementation)
        
        Returns:
            Dictionary with validation statistics
        """
        return {
            "config": {
                "enable_security_checks": self.config.enable_security_checks,
                "max_query_length": self.config.max_query_length,
                "enable_table_authorization": self.config.enable_table_authorization
            },
            "status": "active"
        }
    
    def health_check(self) -> dict:
        """
        Perform health check on the SQL validator
        
        Returns:
            Health status dictionary
        """
        try:
            # Test with a simple valid query
            test_query = "SELECT id, amount FROM payment_intent WHERE status = 'succeeded' LIMIT 10"
            test_result = self.validate_sql(test_query, "health_check")
            
            if test_result.isValid:
                return {
                    "status": "healthy",
                    "validation_config": {
                        "security_checks": self.config.enable_security_checks,
                        "table_authorization": self.config.enable_table_authorization
                    }
                }
            else:
                return {
                    "status": "degraded",
                    "warning": f"Test validation failed: {test_result.error}"
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
