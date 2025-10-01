"""
Chat Handler - Main orchestrator for prompt construction
Integrates system_prompts, tool_prompts, and user_prompts to construct final prompts
Now includes LangChain Sequential Chain integration for analytics queries
"""

import logging
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

# Import prompt modules
from prompts.system_prompts import build_internal_user_context
from prompts.tool_prompts import get_schema
from prompts.user_prompts import (
    build_user_context, 
    is_analytics_related_query,
    handle_non_analytics_query_direct
)

# Import LangChain integration
from langchain_integration.chains.sequential_chain import SequentialChain
from langchain_integration.models.response_models import ChainConfig, LLMConfig

logger = logging.getLogger(__name__)


class ChatHandlerError(Exception):
    """Base exception for chat handler errors"""
    pass


class ValidationError(ChatHandlerError):
    """Input validation errors"""
    pass


class ContextBuildError(ChatHandlerError):
    """Context building errors"""
    pass


class SchemaFetchError(ChatHandlerError):
    """Database schema fetch errors"""
    pass


class ChatHandlerCache:
    """
    Simple in-memory cache for frequently used data
    """
    
    def __init__(self):
        self.schema_cache = {}
        self.system_context_cache = None
        self.cache_timestamps = {}
        self.schema_ttl = 300  # 5 minutes
        self.system_context_ttl = 600  # 10 minutes
    
    def _is_cache_valid(self, cache_key: str, ttl: int) -> bool:
        """Check if cache entry is still valid"""
        if cache_key not in self.cache_timestamps:
            return False
        
        timestamp = self.cache_timestamps[cache_key]
        return datetime.now() - timestamp < timedelta(seconds=ttl)
    
    def get_schema(self, cache_key: str = "default") -> Optional[Dict[str, Any]]:
        """Get cached schema if valid"""
        if cache_key in self.schema_cache and self._is_cache_valid(cache_key, self.schema_ttl):
            logger.debug(f"Schema cache hit for key: {cache_key}")
            return self.schema_cache[cache_key]
        
        logger.debug(f"Schema cache miss for key: {cache_key}")
        return None
    
    def set_schema(self, schema: Dict[str, Any], cache_key: str = "default") -> None:
        """Cache schema with timestamp"""
        self.schema_cache[cache_key] = schema
        self.cache_timestamps[cache_key] = datetime.now()
        logger.debug(f"Schema cached for key: {cache_key}")
    
    def get_system_context(self) -> Optional[str]:
        """Get cached system context if valid"""
        if (self.system_context_cache and 
            self._is_cache_valid("system_context", self.system_context_ttl)):
            logger.debug("System context cache hit")
            return self.system_context_cache
        
        logger.debug("System context cache miss")
        return None
    
    def set_system_context(self, context: str) -> None:
        """Cache system context with timestamp"""
        self.system_context_cache = context
        self.cache_timestamps["system_context"] = datetime.now()
        logger.debug("System context cached")
    
    def clear_cache(self) -> None:
        """Clear all cache entries"""
        self.schema_cache.clear()
        self.system_context_cache = None
        self.cache_timestamps.clear()
        logger.info("Cache cleared")


class ChatHandler:
    """
    Main chat handler that orchestrates prompt construction
    """
    
    def __init__(self):
        """Initialize chat handler with cache and configuration"""
        self.cache = ChatHandlerCache()
        self.logger = logger
        self.processing_stats = {
            'total_requests': 0,
            'analytics_requests': 0,
            'non_analytics_requests': 0,
            'langchain_requests': 0,
            'errors': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Initialize LangChain Sequential Chain (lazy initialization)
        self.sequential_chain = None
        self._langchain_initialized = False
        self._initialization_lock = False
    
    def _ensure_langchain_initialized(self, app_state, max_retries: int = 3) -> bool:
        """
        Ensure LangChain is initialized with proper configuration (lazy initialization with retry)
        
        Args:
            app_state: Application state with configuration
            max_retries: Maximum number of retry attempts
            
        Returns:
            bool: True if initialization successful, False otherwise
        """
        # Prevent concurrent initialization
        if self._initialization_lock:
            return self.sequential_chain is not None
            
        if self._langchain_initialized and self.sequential_chain is not None:
            return True
            
        try:
            self._initialization_lock = True
            
            # Retry logic with exponential backoff
            for attempt in range(max_retries + 1):
                if attempt > 0:
                    import time
                    wait_time = min(2 ** (attempt - 1), 5)  # Exponential backoff, max 5 seconds
                    time.sleep(wait_time)
                
                try:
                    # Validate app_state and configuration
                    if not self._validate_app_state_for_langchain(app_state):
                        if attempt == max_retries:
                            self.logger.error("[LANGCHAIN_INIT] App state validation failed after all retries")
                            return False
                        continue
                        
                    # Create LLM config from app_state
                    llm_config = LLMConfig.from_app_state(app_state)
                    
                    # Validate LLM configuration before proceeding
                    if not self._validate_llm_config(llm_config):
                        if attempt == max_retries:
                            self.logger.error("[LANGCHAIN_INIT] LLM config validation failed after all retries")
                            return False
                        continue
                        
                    chain_config = ChainConfig(llm_config=llm_config)
                    self.sequential_chain = SequentialChain(chain_config)
                    self._langchain_initialized = True
                    
                    return True
                    
                except Exception as e:
                    if attempt == max_retries:
                        self.logger.error(f"[LANGCHAIN_INIT] ❌ Failed to initialize LangChain after {max_retries} retries: {e}")
                        self.sequential_chain = None
                        self._langchain_initialized = False
                        return False
                    else:
                        self.logger.warning(f"[LANGCHAIN_INIT] Attempt {attempt + 1} failed: {e}")
                        
        except Exception as e:
            self.logger.error(f"[LANGCHAIN_INIT] ❌ Critical error during initialization: {e}")
            self.sequential_chain = None
            self._langchain_initialized = False
            return False
        finally:
            self._initialization_lock = False
            
        return False
    
    def _validate_app_state_for_langchain(self, app_state) -> bool:
        """
        Validate app_state has required configuration for LangChain
        
        Args:
            app_state: Application state to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if app_state is None:
            self.logger.error("[LANGCHAIN_INIT] app_state is None")
            return False
            
        if not hasattr(app_state, 'config'):
            self.logger.error("[LANGCHAIN_INIT] app_state missing config attribute")
            return False
            
        ai_config = app_state.config.get('ai', {})
        if not ai_config:
            self.logger.error("[LANGCHAIN_INIT] AI configuration not found in app_state")
            return False
            
        return True
    
    def _validate_llm_config(self, llm_config: LLMConfig) -> bool:
        """
        Validate LLM configuration has required fields
        
        Args:
            llm_config: LLM configuration to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not llm_config.api_key:
            self.logger.error("[LANGCHAIN_INIT] API key not configured in LLM config")
            return False
            
        if not llm_config.model_name:
            self.logger.error("[LANGCHAIN_INIT] Model name not configured in LLM config")
            return False
            
        return True
    
    def _initialize_langchain(self, app_state=None) -> None:
        """
        Legacy initialization method (kept for backward compatibility)
        Use _ensure_langchain_initialized for new code
        """
        if app_state:
            self._ensure_langchain_initialized(app_state)
        else:
            self.logger.warning("[LANGCHAIN_INIT] Legacy initialization called without app_state")
    
    def process_chat_request(self, app_state, user_query: str) -> str:
        """
        Process chat request and return constructed prompt or direct response
        
        Args:
            app_state: Application state with database connections
            user_query: Natural language query from user
            
        Returns:
            str: Either constructed prompt in [system][Tool][User] format or direct response
            
        Raises:
            ChatHandlerError: For critical processing errors
        """
        start_time = time.time()
        self.processing_stats['total_requests'] += 1
        
        try:
            # Step 1: Validate inputs
            self._validate_inputs(app_state, user_query)
            
            # Step 2: Build user context and check if analytics query
            user_context_result = self._build_user_context(user_query)
            
            # Step 3: Handle non-analytics queries directly
            if not user_context_result['is_analytics']:
                self.processing_stats['non_analytics_requests'] += 1
                response = self._handle_non_analytics_query(
                    user_query, 
                    user_context_result['reason']
                )
                
                processing_time = time.time() - start_time
                return response
            
            # Step 4: Process analytics query - build all contexts
            self.processing_stats['analytics_requests'] += 1
            
            # Build system context
            system_context = self._build_system_context()
            
            # Build tool context
            tool_context = self._build_tool_context(app_state)
            
            # Step 5: Construct final prompt
            final_prompt = self._construct_final_prompt(
                system_context, 
                tool_context, 
                user_context_result
            )
            
            processing_time = time.time() - start_time
            return final_prompt
            
        except Exception as e:
            self.processing_stats['errors'] += 1
            processing_time = time.time() - start_time
            self.logger.error(f"[CHAT_HANDLER_ERROR] Failed after {processing_time:.3f}s: {e}")
            
            # Return fallback response for critical errors
            return self._get_fallback_response(str(e))
    
    def _validate_inputs(self, app_state, user_query: str) -> None:
        """
        Validate inputs before processing
        
        Args:
            app_state: Application state object
            user_query: User query string
            
        Raises:
            ValidationError: If validation fails
        """
        if app_state is None:
            raise ValidationError("app_state cannot be None")
        
        if not user_query or not user_query.strip():
            raise ValidationError("user_query cannot be empty")
        
        # Check if app_state has required methods
        if not hasattr(app_state, 'get_mysql_connection'):
            raise ValidationError("app_state missing get_mysql_connection method")
        
        # Validate query length (reasonable limits)
        if len(user_query.strip()) < 2:
            raise ValidationError("user_query too short")
        
        if len(user_query) > 10000:
            raise ValidationError("user_query too long (max 10000 characters)")
        
        self.logger.debug("[VALIDATION_SUCCESS] Input validation passed")
    
    def _build_user_context(self, user_query: str) -> Dict[str, Any]:
        """
        Build user context using user_prompts module
        
        Args:
            user_query: Natural language query from user
            
        Returns:
            Dict containing user context information
            
        Raises:
            ContextBuildError: If user context building fails
        """
        try:
            self.logger.debug("[USER_CONTEXT_START] Building user context")
            
            # Check if query is analytics-related
            is_analytics, reason = is_analytics_related_query(user_query)
            
            result = {
                'is_analytics': is_analytics,
                'reason': reason,
                'query': user_query,
                'context': None
            }
            
            # If analytics query, build full context
            if is_analytics:
                context = build_user_context(user_query)
                result['context'] = context
                self.logger.debug("[USER_CONTEXT_SUCCESS] Analytics context built")
            else:
                self.logger.debug(f"[USER_CONTEXT_SUCCESS] Non-analytics query detected: {reason}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"[USER_CONTEXT_ERROR] Failed to build user context: {e}")
            raise ContextBuildError(f"User context building failed: {e}")
    
    def _build_system_context(self) -> str:
        """
        Build system context using system_prompts module
        
        Returns:
            str: Complete system context string
            
        Raises:
            ContextBuildError: If system context building fails
        """
        try:
            self.logger.debug("[SYSTEM_CONTEXT_START] Building system context")
            
            # Check cache first
            cached_context = self.cache.get_system_context()
            if cached_context:
                self.processing_stats['cache_hits'] += 1
                self.logger.debug("[SYSTEM_CONTEXT_CACHE_HIT] Using cached system context")
                return cached_context
            
            self.processing_stats['cache_misses'] += 1
            
            # Build fresh system context
            system_context = build_internal_user_context()
            
            # Cache the result
            self.cache.set_system_context(system_context)
            
            self.logger.debug("[SYSTEM_CONTEXT_SUCCESS] System context built and cached")
            return system_context
            
        except Exception as e:
            self.logger.error(f"[SYSTEM_CONTEXT_ERROR] Failed to build system context: {e}")
            raise ContextBuildError(f"System context building failed: {e}")
    
    def _build_tool_context(self, app_state) -> str:
        """
        Build tool context using tool_prompts module
        
        Args:
            app_state: Application state with database connections
            
        Returns:
            str: Formatted tool context with schema information
            
        Raises:
            SchemaFetchError: If schema cannot be fetched from database or cache
        """
        try:
            self.logger.debug("[TOOL_CONTEXT_START] Building tool context")
            
            # Check cache first
            cached_schema = self.cache.get_schema()
            if cached_schema:
                self.processing_stats['cache_hits'] += 1
                self.logger.debug("[TOOL_CONTEXT_CACHE_HIT] Using cached schema")
                schema_info = cached_schema
            else:
                self.processing_stats['cache_misses'] += 1
                
                # Fetch fresh schema
                schema_info = get_schema(app_state)
                
                # Check if schema fetch was successful
                if not schema_info:
                    raise SchemaFetchError("Failed to fetch schema from database: get_schema returned None")
                
                # Check if schema has errors - look for explicit error keys only
                if any(isinstance(v, dict) and 'error' in v for v in schema_info.values()):
                    error_details = [f"{k}: {v['error']}" for k, v in schema_info.items() if isinstance(v, dict) and 'error' in v]
                    raise SchemaFetchError(f"Schema fetch failed with errors: {'; '.join(error_details)}")
                
                # Cache the successful result
                self.cache.set_schema(schema_info)
                self.logger.debug("[TOOL_CONTEXT_SUCCESS] Schema fetched and cached")
            
            # Format schema information for prompt
            tool_context = self._format_schema_for_prompt(schema_info)
            
            return tool_context
            
        except SchemaFetchError:
            # Re-raise SchemaFetchError as-is
            raise
        except Exception as e:
            self.logger.error(f"[TOOL_CONTEXT_ERROR] Failed to build tool context: {e}")
            
            # Try to use cached schema as fallback
            cached_schema = self.cache.get_schema()
            if cached_schema:
                self.logger.warning("[TOOL_CONTEXT_FALLBACK] Using cached schema as fallback")
                return self._format_schema_for_prompt(cached_schema)
            
            # If no cache available, raise SchemaFetchError
            raise SchemaFetchError(f"Failed to build tool context and no cached schema available: {e}")
    
    def _format_schema_for_prompt(self, schema_info: Dict[str, Any]) -> str:
        """
        Format schema information for inclusion in prompt
        
        Args:
            schema_info: Schema information from tool_prompts
            
        Returns:
            str: Formatted schema context
            
        Raises:
            SchemaFetchError: If schema_info is empty or invalid
        """
        if not schema_info:
            raise SchemaFetchError("Cannot format schema for prompt: schema_info is empty")
        
        context_parts = [
            "## DATABASE SCHEMA INFORMATION",
            ""
        ]
        
        # Process each table
        for table_name, table_info in schema_info.items():
            if isinstance(table_info, dict) and 'columns' in table_info:
                context_parts.append(f"### {table_name.upper()} TABLE:")
                context_parts.append("")
                
                # Add columns
                if table_info['columns']:
                    context_parts.append("**Columns:**")
                    for col in table_info['columns']:
                        nullable = "NULL" if col.get('nullable') == 'YES' else "NOT NULL"
                        key_info = f" ({col.get('key')})" if col.get('key') else ""
                        context_parts.append(f"- {col['name']}: {col['data_type']} {nullable}{key_info}")
                    context_parts.append("")
                
                # Add indexes
                if table_info.get('indexes'):
                    context_parts.append("**Indexes:**")
                    for idx in table_info['indexes']:
                        unique = "UNIQUE " if idx.get('unique') else ""
                        columns = ", ".join(idx.get('columns', []))
                        context_parts.append(f"- {unique}INDEX {idx['name']} ({columns})")
                    context_parts.append("")
                
                # Add foreign keys
                if table_info.get('foreign_keys'):
                    context_parts.append("**Foreign Keys:**")
                    for fk in table_info['foreign_keys']:
                        context_parts.append(
                            f"- {fk['column']} → {fk['referenced_table']}.{fk['referenced_column']}"
                        )
                    context_parts.append("")
            
            elif isinstance(table_info, dict) and 'error' in table_info:
                context_parts.append(f"### {table_name.upper()} TABLE: Error - {table_info['error']}")
                context_parts.append("")
        
        return "\n".join(context_parts)
    
    
    def _construct_final_prompt(self, system_ctx: str, tool_ctx: str, user_ctx: Dict[str, Any]) -> str:
        """
        Construct final prompt in required [system][Tool][User] format
        
        Args:
            system_ctx: System context string
            tool_ctx: Tool context string
            user_ctx: User context dictionary
            
        Returns:
            str: Complete formatted prompt string
        """
        try:
            self.logger.debug("[PROMPT_CONSTRUCTION_START] Assembling final prompt")
            
            prompt_parts = [
                "[SYSTEM CONTEXT]",
                system_ctx,
                "",
                "[TOOL CONTEXT]",
                tool_ctx,
                "",
                "[USER CONTEXT]",
                user_ctx['context'] if user_ctx['context'] else f"User Query: {user_ctx['query']}",
                ""
            ]
            
            final_prompt = "\n".join(prompt_parts)
            
            self.logger.debug(f"[PROMPT_CONSTRUCTION_SUCCESS] Final prompt constructed ({len(final_prompt)} chars)")
            return final_prompt
            
        except Exception as e:
            self.logger.error(f"[PROMPT_CONSTRUCTION_ERROR] Failed to construct prompt: {e}")
            raise ContextBuildError(f"Prompt construction failed: {e}")
    
    def _handle_non_analytics_query(self, user_query: str, reason: str) -> str:
        """
        Handle non-analytics queries directly
        
        Args:
            user_query: Original user query
            reason: Classification reason
            
        Returns:
            str: Direct response for non-analytics query
        """
        try:
            self.logger.debug(f"[NON_ANALYTICS_HANDLER] Processing query with reason: {reason}")
            
            # Use the existing direct handler from user_prompts
            result = handle_non_analytics_query_direct(user_query, reason, self.logger)
            
            return result.get('response', 'I can help you with payment analytics. Please ask a question about your payment data.')
            
        except Exception as e:
            self.logger.error(f"[NON_ANALYTICS_HANDLER_ERROR] Failed to handle non-analytics query: {e}")
            return "I'm here to help with payment analytics. Please ask a question about your payment data."
    
    def process_with_langchain(self, app_state, user_query: str, session_id: str = "") -> 'DataSummaryResult':
        """
        Process analytics query using LangChain Sequential Chain
        
        Args:
            app_state: Application state with database connections
            user_query: Natural language query from user
            session_id: Session ID for tracking
            
        Returns:
            DataSummaryResult: Final response object with html_summary, markdown_data, etc.
        """
        start_time = time.time()
        self.processing_stats['langchain_requests'] += 1
        
        try:
            # Ensure LangChain is initialized with proper configuration
            if not self._ensure_langchain_initialized(app_state):
                self.logger.error("[LANGCHAIN_HANDLER] Failed to initialize LangChain Sequential Chain")
                return self._get_fallback_response("LangChain integration not available - configuration error")
            
            # Step 1: Validate inputs
            self._validate_inputs(app_state, user_query)
            
            # Step 2: Build user context and check if analytics query
            user_context_result = self._build_user_context(user_query)
            
            # Step 3: Handle non-analytics queries directly
            if not user_context_result['is_analytics']:
                self.processing_stats['non_analytics_requests'] += 1
                response_text = self._handle_non_analytics_query(
                    user_query, 
                    user_context_result['reason']
                )
                
                # Create DataSummaryResult for non-analytics response
                from langchain_integration.models.response_models import DataSummaryResult
                non_analytics_result = DataSummaryResult(
                    success=True,
                    summary=response_text,
                    html_summary=f"<p>{response_text}</p>",
                    markdown_data="No data table available for non-analytics queries",
                    key_insights=["Non-analytics query handled directly"],
                    data_points_analyzed=0,
                    summary_time_ms=(time.time() - start_time) * 1000,
                    prompt_tokens=0,
                    completion_tokens=0
                )
                
                processing_time = time.time() - start_time
                return non_analytics_result
            
            # Step 4: Build contexts for LangChain processing
            system_context = self._build_system_context()
            tool_context = self._build_tool_context(app_state)
            
            # Step 5: Construct final prompt
            final_prompt = self._construct_final_prompt(
                system_context, 
                tool_context, 
                user_context_result
            )
            
            # Step 6: Process through LangChain Sequential Chain
            chain_result = self.sequential_chain.process(
                final_prompt=final_prompt,
                app_state=app_state,
                user_query=user_query,
                session_id=session_id
            )
            
            processing_time = time.time() - start_time
            
            if chain_result.success:
                return chain_result.final_response
            else:
                self.logger.error(
                    f"[LANGCHAIN_HANDLER] Sequential chain failed in {processing_time:.3f}s - "
                    f"Type: {chain_result.response_type}, Error: {chain_result.final_response}"
                )
                return chain_result.final_response
                
        except Exception as e:
            self.processing_stats['errors'] += 1
            processing_time = time.time() - start_time
            self.logger.error(f"[LANGCHAIN_HANDLER] Failed after {processing_time:.3f}s: {e}")
            
            # Return fallback response for critical errors
            return self._get_fallback_response(str(e))
    
    def _get_fallback_response(self, error_msg: str) -> 'DataSummaryResult':
        """
        Get fallback response for critical errors
        
        Args:
            error_msg: Error message
            
        Returns:
            DataSummaryResult: Fallback response object
        """
        from langchain_integration.models.response_models import DataSummaryResult
        
        fallback_text = f"""I apologize, but I encountered an error while processing your request. 

Error: {error_msg}

Please try rephrasing your question or contact support if the issue persists.

I can help you with:
• Payment analytics and reporting
• Transaction summaries and trends
• Revenue analysis
• Success/failure rate analysis

What payment data would you like to explore?"""

        return DataSummaryResult(
            success=False,
            error=error_msg,
            summary=fallback_text,
            html_summary=f"<p><strong>Error:</strong> {error_msg}</p><p>Please try rephrasing your question or contact support if the issue persists.</p>",
            markdown_data="No data available due to error",
            key_insights=[f"Error occurred: {error_msg}"],
            data_points_analyzed=0,
            summary_time_ms=0.0,
            prompt_tokens=0,
            completion_tokens=0
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get processing statistics
        
        Returns:
            Dict containing processing statistics
        """
        return {
            'processing_stats': self.processing_stats.copy(),
            'cache_stats': {
                'schema_cache_size': len(self.cache.schema_cache),
                'system_context_cached': self.cache.system_context_cache is not None,
                'cache_timestamps': len(self.cache.cache_timestamps)
            }
        }
    
    def clear_cache(self) -> None:
        """Clear all caches"""
        self.cache.clear_cache()


# Convenience functions for easy integration
def process_chat_request(app_state, user_query: str) -> str:
    """
    Convenience function to process chat request (original method)
    
    Args:
        app_state: Application state with database connections
        user_query: Natural language query from user
        
    Returns:
        str: Constructed prompt or direct response
    """
    handler = ChatHandler()
    return handler.process_chat_request(app_state, user_query)


def process_chat_request_with_langchain(app_state, user_query: str, session_id: str = "") -> 'DataSummaryResult':
    """
    Convenience function to process chat request with LangChain Sequential Chain
    
    Args:
        app_state: Application state with database connections
        user_query: Natural language query from user
        session_id: Session ID for tracking
        
    Returns:
        DataSummaryResult: Final response object with html_summary, markdown_data, etc.
    """
    handler = ChatHandler()
    # Re-initialize LangChain with app_state configuration
    handler._initialize_langchain(app_state)
    return handler.process_with_langchain(app_state, user_query, session_id)
