"""
Sequential Chain Orchestrator

Coordinates the execution of all services in the proper sequence:
1. SQL Generation (LLM)
2. SQL Validation (Security checks)
3. SQL Execution (MySQL)
4. Data Summarization (LLM)

Implements the error handling strategy specified by the user.
"""

import logging
import time
from typing import Optional

from ..models.response_models import (
    SequentialChainResult,
    ChainConfig,
    create_error_result,
    create_success_result,
)
from ..services.sql_generator import SQLGeneratorService
from ..services.sql_validator import SQLValidatorService
from ..services.sql_executor import SQLExecutorService
from ..services.data_summarizer import DataSummarizerService

logger = logging.getLogger(__name__)


class SequentialChain:
    """
    Sequential Chain Orchestrator

    Coordinates all services in the proper sequence with comprehensive
    error handling and fallback mechanisms.
    """

    def __init__(self, config: Optional[ChainConfig] = None):
        """
        Initialize Sequential Chain

        Args:
            config: Chain configuration, uses defaults if None
        """
        self.config = config or ChainConfig()

        # Initialize all services
        self.sql_generator = SQLGeneratorService(self.config.llm_config)
        self.sql_validator = SQLValidatorService(self.config.validation_config)
        self.sql_executor = SQLExecutorService(self.config.execution_config)
        self.data_summarizer = DataSummarizerService(self.config.llm_config)

        logger.info("Sequential Chain initialized with all services")

    def process(
        self, final_prompt: str, app_state, user_query: str = "", session_id: str = ""
    ) -> SequentialChainResult:
        """
        Process the complete sequential chain

        Args:
            final_prompt: Complete prompt from chat_handler
            app_state: Application state with database connections
            user_query: Original user query for context
            session_id: Session ID for tracking

        Returns:
            SequentialChainResult with final response or error
        """
        start_time = time.time()

        try:
            logger.info(
                f"[CHAIN_DEBUG] 🚀 Starting processing for session: {session_id}"
            )
            logger.info(f"[CHAIN_DEBUG] 📝 Input Analysis:")
            logger.info(
                f"[CHAIN_DEBUG]   - Final prompt length: {len(final_prompt)} chars"
            )
            logger.info(f"[CHAIN_DEBUG]   - User query: {user_query[:100]}...")
            logger.debug(
                f"[CHAIN_DEBUG]   - Full prompt preview: {final_prompt[:500]}..."
            )

            # Step 1: SQL Generation
            logger.info("[CHAIN_DEBUG] 🔄 Step 1: SQL Generation")
            logger.info(final_prompt)
            sql_result = self.sql_generator.generate_sql(final_prompt)

            if not sql_result.success:
                # SQL generation failed - return error
                error_msg = f"SQL generation failed: {sql_result.error}"
                logger.error(f"[SEQUENTIAL_CHAIN] {error_msg}")

                result = create_error_result(
                    error_msg, "sql_generation_error", user_query, session_id
                )
                result.sql_generation = sql_result
                result.total_processing_time_ms = (time.time() - start_time) * 1000
                return result

            logger.info(
                f"[SEQUENTIAL_CHAIN] SQL generated successfully: {sql_result.sql_query}"
            )

            # Step 2: SQL Validation
            logger.info("[SEQUENTIAL_CHAIN] Step 2: SQL Validation")
            validation_context = {"session_id": session_id, "user_query": user_query}
            validation_result = self.sql_validator.validate_sql_with_context(
                sql_result.sql_query, validation_context
            )

            if not validation_result.isValid:
                # SQL validation failed - return error
                error_msg = f"SQL validation failed: {validation_result.error}"
                logger.error(f"[SEQUENTIAL_CHAIN] {error_msg}")

                result = create_error_result(
                    error_msg, "sql_validation_error", user_query, session_id
                )
                result.sql_generation = sql_result
                result.sql_validation = validation_result
                result.total_processing_time_ms = (time.time() - start_time) * 1000
                return result

            logger.info("[SEQUENTIAL_CHAIN] SQL validation passed")

            # Step 3: SQL Execution
            logger.info("[SEQUENTIAL_CHAIN] Step 3: SQL Execution")
            execution_context = {"session_id": session_id, "user_query": user_query}
            execution_result = self.sql_executor.execute_sql_with_context(
                sql_result.sql_query, app_state, execution_context
            )

            if not execution_result.success:
                # SQL execution failed - return error
                error_msg = f"SQL execution failed: {execution_result.error}"
                logger.error(f"[SEQUENTIAL_CHAIN] {error_msg}")

                result = create_error_result(
                    error_msg, "sql_execution_error", user_query, session_id
                )
                result.sql_generation = sql_result
                result.sql_validation = validation_result
                result.sql_execution = execution_result
                result.total_processing_time_ms = (time.time() - start_time) * 1000
                return result

            logger.info(
                f"[SEQUENTIAL_CHAIN] SQL executed successfully, returned {execution_result.row_count} rows"
            )

            # Step 4: Data Summarization
            logger.info("[SEQUENTIAL_CHAIN] Step 4: Data Summarization")
            summary_result = self.data_summarizer.summarize_data(
                execution_result, user_query, sql_result.sql_query
            )

            if not summary_result.success:
                # Data summarization failed - return raw data as fallback
                logger.warning(
                    f"[SEQUENTIAL_CHAIN] Data summarization failed: {summary_result.error}"
                )

                if self.config.enable_fallback_to_data:
                    # Create complete DataSummaryResult for fallback
                    from ..models.response_models import DataSummaryResult
                    
                    fallback_text = self.data_summarizer.create_fallback_summary(
                        execution_result, user_query
                    )
                    
                    fallback_result = DataSummaryResult(
                        success=True,
                        summary=fallback_text,
                        html_summary=f"<p><strong>Fallback Summary:</strong> {fallback_text.replace('•', '<strong>•</strong>')}</p>",
                        markdown_data=self.data_summarizer.convert_data_to_markdown_table(execution_result.data),
                        key_insights=["LLM summarization failed", f"Retrieved {execution_result.row_count} records"],
                        data_points_analyzed=execution_result.row_count,
                        summary_time_ms=0.0,
                        prompt_tokens=0,
                        completion_tokens=0
                    )

                    logger.info(
                        "[SEQUENTIAL_CHAIN] Using fallback DataSummaryResult due to LLM failure"
                    )

                    result = create_success_result(
                        fallback_result, "data", user_query, session_id
                    )
                    result.sql_generation = sql_result
                    result.sql_validation = validation_result
                    result.sql_execution = execution_result
                    result.data_summary = fallback_result
                    result.total_processing_time_ms = (time.time() - start_time) * 1000
                    return result
                else:
                    # Return error if fallback is disabled
                    error_msg = f"Data summarization failed: {summary_result.error}"
                    result = create_error_result(
                        error_msg, "data_summarization_error", user_query, session_id
                    )
                    result.sql_generation = sql_result
                    result.sql_validation = validation_result
                    result.sql_execution = execution_result
                    result.data_summary = summary_result
                    result.total_processing_time_ms = (time.time() - start_time) * 1000
                    return result

            # All steps successful - return DataSummaryResult object
            logger.info("[SEQUENTIAL_CHAIN] All steps completed successfully")

            result = create_success_result(
                summary_result, "summary", user_query, session_id
            )
            result.sql_generation = sql_result
            result.sql_validation = validation_result
            result.sql_execution = execution_result
            result.data_summary = summary_result
            result.total_processing_time_ms = (time.time() - start_time) * 1000

            # Log final statistics
            logger.info(
                f"[SEQUENTIAL_CHAIN] Processing complete - "
                f"Total time: {result.total_processing_time_ms:.2f}ms, "
                f"Rows: {execution_result.row_count}, "
                f"Tokens: {result.total_prompt_tokens + result.total_completion_tokens}"
            )

            return result

        except Exception as e:
            # Unexpected error in chain processing
            total_time_ms = (time.time() - start_time) * 1000
            error_msg = f"Sequential chain processing failed: {str(e)}"

            logger.error(
                f"[SEQUENTIAL_CHAIN] {error_msg} (after {total_time_ms:.2f}ms)"
            )

            result = create_error_result(
                error_msg, "chain_error", user_query, session_id
            )
            result.total_processing_time_ms = total_time_ms
            return result

    def process_with_retry(
        self, final_prompt: str, app_state, user_query: str = "", session_id: str = ""
    ) -> SequentialChainResult:
        """
        Process with retry logic (if enabled in config)

        Args:
            final_prompt: Complete prompt from chat_handler
            app_state: Application state with database connections
            user_query: Original user query for context
            session_id: Session ID for tracking

        Returns:
            SequentialChainResult with final response or error
        """
        if not self.config.enable_retry_on_failure:
            return self.process(final_prompt, app_state, user_query, session_id)

        last_result = None

        for attempt in range(self.config.max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(
                        f"[SEQUENTIAL_CHAIN] Retry attempt {attempt}/{self.config.max_retries}"
                    )

                result = self.process(final_prompt, app_state, user_query, session_id)

                if result.success:
                    if attempt > 0:
                        logger.info(
                            f"[SEQUENTIAL_CHAIN] Retry successful on attempt {attempt}"
                        )
                    return result

                last_result = result

                # Don't retry certain types of errors
                if result.response_type in [
                    "sql_validation_error",
                    "sql_execution_error",
                ]:
                    logger.info(
                        f"[SEQUENTIAL_CHAIN] Not retrying {result.response_type}"
                    )
                    break

            except Exception as e:
                logger.error(f"[SEQUENTIAL_CHAIN] Retry attempt {attempt} failed: {e}")
                if attempt == self.config.max_retries:
                    return create_error_result(
                        f"All retry attempts failed: {str(e)}",
                        "retry_exhausted",
                        user_query,
                        session_id,
                    )

        return last_result or create_error_result(
            "Processing failed with no result", "unknown_error", user_query, session_id
        )

    def health_check(self, app_state) -> dict:
        """
        Perform comprehensive health check on all services

        Args:
            app_state: Application state for database testing

        Returns:
            Health status dictionary
        """
        try:
            health_status = {
                "status": "healthy",
                "services": {},
                "overall_status": "healthy",
            }

            # Check SQL Generator
            generator_health = self.sql_generator.health_check()
            health_status["services"]["sql_generator"] = generator_health

            # Check SQL Validator
            validator_health = self.sql_validator.health_check()
            health_status["services"]["sql_validator"] = validator_health

            # Check SQL Executor
            executor_health = self.sql_executor.health_check(app_state)
            health_status["services"]["sql_executor"] = executor_health

            # Check Data Summarizer
            summarizer_health = self.data_summarizer.health_check()
            health_status["services"]["data_summarizer"] = summarizer_health

            # Determine overall health
            unhealthy_services = [
                name
                for name, status in health_status["services"].items()
                if status.get("status") != "healthy"
            ]

            if unhealthy_services:
                health_status["overall_status"] = "degraded"
                health_status["unhealthy_services"] = unhealthy_services

            return health_status

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "overall_status": "unhealthy",
            }

    def get_stats(self) -> dict:
        """
        Get comprehensive statistics from all services

        Returns:
            Statistics dictionary
        """
        try:
            return {
                "config": {
                    "enable_fallback_to_data": self.config.enable_fallback_to_data,
                    "enable_retry_on_failure": self.config.enable_retry_on_failure,
                    "max_retries": self.config.max_retries,
                },
                "services": {
                    "sql_validator": self.sql_validator.get_validation_stats(),
                    "sql_executor": self.sql_executor.get_execution_stats(),
                },
            }
        except Exception as e:
            return {"error": str(e), "status": "error"}

    def update_config(self, new_config: ChainConfig) -> None:
        """
        Update chain configuration and propagate to services

        Args:
            new_config: New chain configuration
        """
        self.config = new_config

        # Update service configurations
        self.sql_generator.update_config(new_config.llm_config)
        self.sql_validator.update_config(new_config.validation_config)
        self.sql_executor.update_config(new_config.execution_config)
        self.data_summarizer.update_config(new_config.llm_config)

        logger.info("Sequential Chain configuration updated")

    def test_end_to_end(self, app_state) -> dict:
        """
        Perform end-to-end test of the sequential chain

        Args:
            app_state: Application state for testing

        Returns:
            Test result dictionary
        """
        try:
            test_prompt = """
[SYSTEM CONTEXT]
You are a payment analytics assistant.

[TOOL CONTEXT]
Available tables: payment_intent (id, amount, status, created_at)

[USER CONTEXT]
User Query: Show me the total number of successful payments
"""

            result = self.process(
                final_prompt=test_prompt,
                app_state=app_state,
                user_query="Show me the total number of successful payments",
                session_id="test_session",
            )

            return {
                "test_status": "passed" if result.success else "failed",
                "result": {
                    "success": result.success,
                    "response_type": result.response_type,
                    "processing_time_ms": result.total_processing_time_ms,
                    "error": result.final_response if not result.success else None,
                },
            }

        except Exception as e:
            return {"test_status": "failed", "error": str(e)}
