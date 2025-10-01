"""
SQL Generator Service

Uses LangChain with LLM to convert natural language queries to SQL.
Processes the final_prompt from chat_handler and generates SQL queries.
"""

import logging
import time
import os
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from ..models.response_models import (
    SQLGenerationResult, 
    SQLGenerationError,
    LLMConfig,
    QueryType
)

logger = logging.getLogger(__name__)


class SQLGeneratorService:
    """Service for generating SQL from natural language using LLM"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """
        Initialize SQL Generator Service
        
        Args:
            config: LLM configuration, uses defaults if None
        """
        self.config = config or LLMConfig()
        self.llm = None
        self.chain = None
        self._initialize_llm()
        self._initialize_chain()
    
    def _initialize_llm(self) -> None:
        """Initialize the LLM with configuration"""
        try:
            # Get configuration values
            api_key = self.config.api_key
            api_base = self.config.api_base
            model_name = self.config.model_name
            
            # Enhanced configuration logging
            logger.info(f"[SQL_GEN_CONFIG] Initializing LLM with configuration:")
            logger.info(f"[SQL_GEN_CONFIG] Model: {model_name}")
            logger.info(f"[SQL_GEN_CONFIG] API Base: {api_base[:50] + '...' if api_base and len(api_base) > 50 else api_base}")
            logger.info(f"[SQL_GEN_CONFIG] API Key: {'SET (' + str(len(api_key)) + ' chars)' if api_key else 'MISSING'}")
            logger.info(f"[SQL_GEN_CONFIG] Temperature: {self.config.sql_generation_temperature}")
            logger.info(f"[SQL_GEN_CONFIG] Timeout: {self.config.timeout_seconds}s")
            
            if not api_key:
                raise SQLGenerationError("AI API key not configured in app_state")
            
            if not api_base:
                raise SQLGenerationError("AI API base URL not configured in app_state")
            
            if not model_name:
                raise SQLGenerationError("AI model name not configured in app_state")
            
            # Initialize ChatOpenAI with Google AI endpoint
            logger.info(f"[SQL_GEN_CONFIG] Creating ChatOpenAI instance...")
            self.llm = ChatOpenAI(
                model=model_name,
                openai_api_base=api_base,
                openai_api_key=api_key,
                temperature=self.config.sql_generation_temperature,
                timeout=self.config.timeout_seconds
            )
            
            logger.info(f"[SQL_GEN_CONFIG] ✅ SQL Generator LLM initialized successfully with model: {model_name}")
            
        except Exception as e:
            logger.error(f"[SQL_GEN_CONFIG] ❌ Failed to initialize LLM: {type(e).__name__}: {e}")
            raise SQLGenerationError(f"LLM initialization failed: {e}", e)
    
    def _initialize_chain(self) -> None:
        """Initialize the LangChain chain for SQL generation"""
        try:
            # Create prompt template for SQL generation
            sql_prompt_template = """
You are an expert SQL query generator for payment analytics. Your task is to convert natural language queries into valid MySQL SQL queries.

{final_prompt}

IMPORTANT INSTRUCTIONS:
1. Generate ONLY the SQL query, no explanations or markdown formatting
2. Use proper MySQL syntax
3. Include appropriate WHERE clauses for data filtering
4. Use table aliases for better readability
5. Ensure the query is safe and follows best practices
6. Do not include semicolons at the end
7. Return only the raw SQL query

SQL Query:"""

            # Create prompt template
            prompt = PromptTemplate(
                input_variables=["final_prompt"],
                template=sql_prompt_template
            )
            
            # Create chain with output parser
            output_parser = StrOutputParser()
            self.chain = prompt | self.llm | output_parser
            
            logger.info("SQL generation chain initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize chain: {e}")
            raise SQLGenerationError(f"Chain initialization failed: {e}", e)
    
    def generate_sql(self, final_prompt: str) -> SQLGenerationResult:
        """
        Generate SQL from the final prompt
        
        Args:
            final_prompt: Complete prompt from chat_handler containing system, tool, and user context
            
        Returns:
            SQLGenerationResult with generated SQL or error
        """
        start_time = time.time()
        
        try:
            logger.info("[SQL_GEN_DEBUG] 🚀 Starting SQL generation")
            
            # Validate input
            if not final_prompt or not final_prompt.strip():
                logger.error("[SQL_GEN_DEBUG] ❌ Empty final_prompt provided")
                return SQLGenerationResult(
                    success=False,
                    error="Empty final_prompt provided"
                )
            
            # Enhanced prompt analysis
            logger.info(f"[SQL_GEN_DEBUG] 📝 Input Analysis:")
            logger.info(f"[SQL_GEN_DEBUG]   - Prompt length: {len(final_prompt)} characters")
            logger.info(f"[SQL_GEN_DEBUG]   - Prompt lines: {len(final_prompt.splitlines())} lines")
            logger.debug(f"[SQL_GEN_DEBUG]   - First 300 chars: {final_prompt[:300]}...")
            logger.debug(f"[SQL_GEN_DEBUG]   - Last 200 chars: ...{final_prompt[-200:]}")
            
            # Check for key sections in prompt
            has_system = "[SYSTEM CONTEXT]" in final_prompt
            has_tool = "[TOOL CONTEXT]" in final_prompt
            has_user = "[USER CONTEXT]" in final_prompt
            logger.info(f"[SQL_GEN_DEBUG] 📋 Prompt sections: System={has_system}, Tool={has_tool}, User={has_user}")
            
            # LLM invocation with detailed logging
            logger.info(f"[SQL_GEN_DEBUG] 🤖 Invoking LLM chain...")
            logger.info(f"[SQL_GEN_DEBUG]   - Model: {self.config.model_name}")
            logger.info(f"[SQL_GEN_DEBUG]   - Temperature: {self.config.sql_generation_temperature}")
            
            try:
                sql_query = self.chain.invoke({"final_prompt": final_prompt})
                logger.info(f"[SQL_GEN_DEBUG] ✅ LLM call completed successfully")
            except Exception as llm_error:
                logger.error(f"[SQL_GEN_DEBUG] ❌ LLM call failed: {type(llm_error).__name__}: {llm_error}")
                
                # Detailed error analysis
                error_str = str(llm_error).lower()
                if "authentication" in error_str or "unauthorized" in error_str:
                    logger.error("[SQL_GEN_DEBUG] 🔑 Authentication issue detected - check API key")
                elif "rate limit" in error_str or "quota" in error_str:
                    logger.error("[SQL_GEN_DEBUG] 🚫 Rate limit/quota issue detected")
                elif "model" in error_str or "not found" in error_str:
                    logger.error("[SQL_GEN_DEBUG] 🤖 Model issue detected - check model name")
                elif "timeout" in error_str:
                    logger.error("[SQL_GEN_DEBUG] ⏰ Timeout issue detected")
                elif "network" in error_str or "connection" in error_str:
                    logger.error("[SQL_GEN_DEBUG] 🌐 Network/connection issue detected")
                
                raise llm_error
            
            # Raw response analysis
            logger.info(f"[SQL_GEN_DEBUG] 📤 Raw LLM Response Analysis:")
            logger.info(f"[SQL_GEN_DEBUG]   - Response type: {type(sql_query).__name__}")
            logger.info(f"[SQL_GEN_DEBUG]   - Response length: {len(str(sql_query))} characters")
            logger.info(f"[SQL_GEN_DEBUG]   - Is empty: {not sql_query or not str(sql_query).strip()}")
            logger.debug(f"[SQL_GEN_DEBUG]   - Raw response: '{sql_query}'")
            
            # Clean up the generated SQL with detailed logging
            logger.info(f"[SQL_GEN_DEBUG] 🧹 Cleaning SQL output...")
            original_sql = sql_query
            cleaned_sql = self._clean_sql_output(sql_query)
            
            logger.info(f"[SQL_GEN_DEBUG] 📋 Cleaning Results:")
            logger.info(f"[SQL_GEN_DEBUG]   - Original length: {len(str(original_sql))}")
            logger.info(f"[SQL_GEN_DEBUG]   - Cleaned length: {len(str(cleaned_sql))}")
            logger.debug(f"[SQL_GEN_DEBUG]   - Before cleaning: '{original_sql}'")
            logger.debug(f"[SQL_GEN_DEBUG]   - After cleaning: '{cleaned_sql}'")
            
            # Validate the generated SQL
            if not cleaned_sql or not cleaned_sql.strip():
                logger.error("[SQL_GEN_DEBUG] ❌ Final validation failed - empty SQL after cleaning")
                logger.error(f"[SQL_GEN_DEBUG] Debug info:")
                logger.error(f"[SQL_GEN_DEBUG]   - Original was empty: {not original_sql}")
                logger.error(f"[SQL_GEN_DEBUG]   - Original content: '{original_sql}'")
                logger.error(f"[SQL_GEN_DEBUG]   - Cleaned content: '{cleaned_sql}'")
                
                return SQLGenerationResult(
                    success=False,
                    error="LLM returned empty SQL query"
                )
            
            # Determine query type
            query_type = self._determine_query_type(cleaned_sql)
            
            # Calculate processing time
            generation_time_ms = (time.time() - start_time) * 1000
            
            logger.info(f"[SQL_GEN_DEBUG] ✅ SQL generation completed successfully!")
            logger.info(f"[SQL_GEN_DEBUG]   - Processing time: {generation_time_ms:.2f}ms")
            logger.info(f"[SQL_GEN_DEBUG]   - Query type: {query_type}")
            logger.info(f"[SQL_GEN_DEBUG]   - Final SQL length: {len(cleaned_sql)} chars")
            logger.debug(f"[SQL_GEN_DEBUG]   - Final SQL: {cleaned_sql[:200]}...")
            
            return SQLGenerationResult(
                success=True,
                sql_query=cleaned_sql,
                query_type=query_type,
                generation_time_ms=generation_time_ms,
                # Note: Token counting would require additional API calls
                # For now, we'll estimate based on content length
                prompt_tokens=self._estimate_tokens(final_prompt),
                completion_tokens=self._estimate_tokens(cleaned_sql)
            )
            
        except Exception as e:
            generation_time_ms = (time.time() - start_time) * 1000
            error_msg = f"SQL generation failed: {str(e)}"
            
            logger.error(f"[SQL_GEN_DEBUG] ❌ Generation failed after {generation_time_ms:.2f}ms")
            logger.error(f"[SQL_GEN_DEBUG] Error type: {type(e).__name__}")
            logger.error(f"[SQL_GEN_DEBUG] Error message: {str(e)}")
            
            return SQLGenerationResult(
                success=False,
                error=error_msg,
                generation_time_ms=generation_time_ms
            )
    
    def _clean_sql_output(self, sql_output: str) -> str:
        """
        Clean and normalize the SQL output from LLM
        
        Args:
            sql_output: Raw SQL output from LLM
            
        Returns:
            Cleaned SQL query
        """
        if not sql_output:
            return ""
        
        # Remove common markdown formatting
        sql_output = sql_output.strip()
        
        # Remove markdown code blocks
        if sql_output.startswith("```sql"):
            sql_output = sql_output[6:]
        elif sql_output.startswith("```"):
            sql_output = sql_output[3:]
        
        if sql_output.endswith("```"):
            sql_output = sql_output[:-3]
        
        # Remove trailing semicolons
        sql_output = sql_output.rstrip(";").strip()
        
        # Remove extra whitespace
        sql_output = " ".join(sql_output.split())
        
        return sql_output
    
    def _determine_query_type(self, sql_query: str) -> QueryType:
        """
        Determine the type of SQL query
        
        Args:
            sql_query: SQL query string
            
        Returns:
            QueryType enum value
        """
        sql_lower = sql_query.lower()
        
        if "count(" in sql_lower or "sum(" in sql_lower or "avg(" in sql_lower:
            return QueryType.ANALYTICS
        elif "group by" in sql_lower or "order by" in sql_lower:
            return QueryType.REPORTING
        elif "limit" in sql_lower and ("order by" in sql_lower or "desc" in sql_lower):
            return QueryType.SUMMARY
        else:
            return QueryType.UNKNOWN
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text (rough approximation)
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        # Rough estimation: ~4 characters per token for English text
        return len(text) // 4
    
    def update_config(self, new_config: LLMConfig) -> None:
        """
        Update LLM configuration and reinitialize if needed
        
        Args:
            new_config: New LLM configuration
        """
        self.config = new_config
        self._initialize_llm()
        self._initialize_chain()
        logger.info("SQL Generator configuration updated")
    
    def health_check(self) -> dict:
        """
        Perform health check on the SQL generator
        
        Returns:
            Health status dictionary
        """
        try:
            if not self.llm or not self.chain:
                return {
                    "status": "unhealthy",
                    "error": "LLM or chain not initialized"
                }
            
            # Test with a simple prompt
            test_result = self.generate_sql("Generate a simple SELECT query for payment_intent table")
            
            if test_result.success:
                return {
                    "status": "healthy",
                    "model": self.config.model_name,
                    "generation_time_ms": test_result.generation_time_ms
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": test_result.error
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
