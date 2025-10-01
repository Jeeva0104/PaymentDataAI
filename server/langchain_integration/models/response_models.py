"""
Response Models for LangChain Integration

Contains all data models and response structures used throughout
the sequential chaining process for SQL generation, validation,
execution, and summarization.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class QueryType(Enum):
    """Types of queries supported"""
    ANALYTICS = "analytics"
    REPORTING = "reporting" 
    SUMMARY = "summary"
    UNKNOWN = "unknown"


# SQL Validation Result (referenced in your validation code)
@dataclass
class SQLValidationResult:
    """Result of SQL validation process"""
    isValid: bool
    error: Optional[str] = None
    warnings: Optional[List[str]] = None
    validated_tables: Optional[List[str]] = None


# SQL Generation Result
@dataclass
class SQLGenerationResult:
    """Result from LLM SQL generation"""
    success: bool
    sql_query: Optional[str] = None
    error: Optional[str] = None
    confidence_score: Optional[float] = None
    query_type: QueryType = QueryType.UNKNOWN
    generation_time_ms: Optional[float] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


# SQL Execution Result  
@dataclass
class SQLExecutionResult:
    """Result from SQL execution against database"""
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    row_count: int = 0
    execution_time_ms: Optional[float] = None
    error: Optional[str] = None
    query_executed: Optional[str] = None
    columns: Optional[List[str]] = None
    data_types: Optional[Dict[str, str]] = None


# Data Summary Result
@dataclass  
class DataSummaryResult:
    """Result from LLM data summarization"""
    success: bool
    summary: Optional[str] = None
    key_insights: Optional[List[str]] = None
    error: Optional[str] = None
    data_points_analyzed: int = 0
    summary_time_ms: Optional[float] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    
    # NEW FIELDS for enhanced output format
    html_summary: Optional[str] = None    # HTML formatted summary (60 words max)
    markdown_data: Optional[str] = None   # Markdown table of SQL results


# Final Pipeline Result
@dataclass
class SequentialChainResult:
    """Complete result from the sequential chain pipeline"""
    success: bool
    final_response: 'DataSummaryResult'  # Changed from str to DataSummaryResult object
    response_type: str  # 'summary', 'data', 'error'
    
    # Individual stage results
    sql_generation: Optional[SQLGenerationResult] = None
    sql_validation: Optional[SQLValidationResult] = None  
    sql_execution: Optional[SQLExecutionResult] = None
    data_summary: Optional[DataSummaryResult] = None
    
    # Metadata
    total_processing_time_ms: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    user_query: Optional[str] = None
    session_id: Optional[str] = None
    
    # Token usage tracking
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    
    def __post_init__(self):
        """Calculate total token usage from individual stages"""
        if self.sql_generation and self.sql_generation.prompt_tokens:
            self.total_prompt_tokens += self.sql_generation.prompt_tokens
        if self.sql_generation and self.sql_generation.completion_tokens:
            self.total_completion_tokens += self.sql_generation.completion_tokens
            
        if self.data_summary and self.data_summary.prompt_tokens:
            self.total_prompt_tokens += self.data_summary.prompt_tokens
        if self.data_summary and self.data_summary.completion_tokens:
            self.total_completion_tokens += self.data_summary.completion_tokens


# Configuration Models
@dataclass
class LLMConfig:
    """Configuration for LLM calls"""
    model_name: str = ""
    temperature: float = 0.1
    timeout_seconds: int = 30
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    
    # Generation-specific settings
    sql_generation_temperature: float = 0.1
    
    # Summary-specific settings  
    summary_temperature: float = 0.3
    
    @classmethod
    def from_app_state(cls, app_state):
        """
        Create LLMConfig from app_state configuration
        
        Args:
            app_state: Application state instance with loaded configuration
            
        Returns:
            LLMConfig instance with values from app_state
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[LLM_CONFIG_DEBUG] 🔧 Loading configuration from app_state...")
        
        ai_config = app_state.config.get('ai', {})
        
        logger.info(f"[LLM_CONFIG_DEBUG] 📋 AI config keys available: {list(ai_config.keys())}")
        logger.info(f"[LLM_CONFIG_DEBUG] 🤖 Model name: {ai_config.get('model_name', 'NOT_SET')}")
        logger.info(f"[LLM_CONFIG_DEBUG] 🔑 API key: {'SET (' + str(len(ai_config.get('api_key', ''))) + ' chars)' if ai_config.get('api_key') else 'NOT_SET'}")
        logger.info(f"[LLM_CONFIG_DEBUG] 🌐 API base: {ai_config.get('api_base', 'NOT_SET')}")
        logger.info(f"[LLM_CONFIG_DEBUG] 🌡️ Temperature: {ai_config.get('temperature', 'DEFAULT')}")
        logger.info(f"[LLM_CONFIG_DEBUG] ⏱️ Timeout: {ai_config.get('timeout_seconds', 'DEFAULT')}s")
        
        config = cls(
            model_name=ai_config.get('model_name', ''),
            api_key=ai_config.get('api_key', ''),
            api_base=ai_config.get('api_base', ''),
            temperature=ai_config.get('temperature', 0.1),
            timeout_seconds=ai_config.get('timeout_seconds', 30),
            sql_generation_temperature=ai_config.get('sql_generation_temperature', 0.1),
            summary_temperature=ai_config.get('summary_temperature', 0.3),
        )
        
        logger.info(f"[LLM_CONFIG_DEBUG] ✅ LLMConfig created successfully")
        return config


@dataclass
class ValidationConfig:
    """Configuration for SQL validation"""
    enable_security_checks: bool = True
    allowed_tables: Optional[List[str]] = None
    require_where_clause: bool = True
    max_query_length: int = 5000
    enable_table_authorization: bool = True
    internal_id_field: str = "internal_id"


@dataclass
class ExecutionConfig:
    """Configuration for SQL execution"""
    max_rows: int = 1000
    timeout_seconds: int = 30
    enable_query_logging: bool = True
    enable_result_caching: bool = False
    cache_ttl_seconds: int = 300


@dataclass
class ChainConfig:
    """Overall configuration for the sequential chain"""
    llm_config: LLMConfig = field(default_factory=LLMConfig)
    validation_config: ValidationConfig = field(default_factory=ValidationConfig)
    execution_config: ExecutionConfig = field(default_factory=ExecutionConfig)
    
    # Chain behavior
    enable_fallback_to_data: bool = True  # Return data if summary fails
    enable_retry_on_failure: bool = False
    max_retries: int = 1
    
    # Logging and monitoring
    enable_detailed_logging: bool = True
    enable_performance_tracking: bool = True


# Error Types for better error handling
class ChainError(Exception):
    """Base exception for chain processing errors"""
    
    def __init__(self, message: str, stage: str = None, original_error: Exception = None):
        super().__init__(message)
        self.stage = stage
        self.original_error = original_error
        self.timestamp = datetime.now()


class SQLGenerationError(ChainError):
    """SQL generation specific errors"""
    
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message, "sql_generation", original_error)


class SQLValidationError(ChainError):
    """SQL validation specific errors"""
    
    def __init__(self, message: str, validation_details: str = None, original_error: Exception = None):
        super().__init__(message, "sql_validation", original_error)
        self.validation_details = validation_details


class SQLExecutionError(ChainError):
    """SQL execution specific errors"""
    
    def __init__(self, message: str, sql_query: str = None, original_error: Exception = None):
        super().__init__(message, "sql_execution", original_error)
        self.sql_query = sql_query


class DataSummarizationError(ChainError):
    """Data summarization specific errors"""
    
    def __init__(self, message: str, data_size: int = None, original_error: Exception = None):
        super().__init__(message, "data_summarization", original_error)
        self.data_size = data_size


# Utility functions for result creation
def create_error_result(error_message: str, error_type: str = "error", 
                       user_query: str = None, session_id: str = None) -> SequentialChainResult:
    """Create a standardized error result with DataSummaryResult"""
    error_summary = DataSummaryResult(
        success=False,
        error=error_message,
        html_summary=f"<p><strong>Error:</strong> {error_message}</p>",
        markdown_data="No data available due to error",
        key_insights=[f"Error occurred: {error_type}"],
        data_points_analyzed=0,
        summary_time_ms=0.0
    )
    
    return SequentialChainResult(
        success=False,
        final_response=error_summary,
        response_type=error_type,
        user_query=user_query,
        session_id=session_id,
        timestamp=datetime.now()
    )


def create_success_result(response: 'DataSummaryResult', response_type: str = "summary",
                         user_query: str = None, session_id: str = None) -> SequentialChainResult:
    """Create a standardized success result with DataSummaryResult"""
    return SequentialChainResult(
        success=True,
        final_response=response,
        response_type=response_type,
        user_query=user_query,
        session_id=session_id,
        timestamp=datetime.now()
    )
