"""
Data Summarizer Service

Uses LangChain with LLM to generate summaries of SQL query results.
This is the second LLM call in the sequential chain.
"""

import logging
import time
import os
import json
from typing import Optional, List, Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from ..models.response_models import (
    DataSummaryResult,
    DataSummarizationError,
    LLMConfig,
    SQLExecutionResult
)

logger = logging.getLogger(__name__)


class DataSummarizerService:
    """Service for generating summaries of SQL query results using LLM"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """
        Initialize Data Summarizer Service
        
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
            
            # Check if configuration is available
            if not api_key or not api_base or not model_name:
                logger.warning(f"[DATA_SUMMARIZER] LLM configuration incomplete - "
                             f"API Key: {'SET' if api_key else 'MISSING'}, "
                             f"API Base: {'SET' if api_base else 'MISSING'}, "
                             f"Model: {'SET' if model_name else 'MISSING'}")
                logger.warning("[DATA_SUMMARIZER] LLM will be initialized when proper config is available")
                self.llm = None
                return
            
            # Initialize ChatOpenAI with Google AI endpoint
            # Use slightly higher temperature for more creative summaries
            self.llm = ChatOpenAI(
                model=model_name,
                openai_api_base=api_base,
                openai_api_key=api_key,
                temperature=self.config.summary_temperature,
                timeout=self.config.timeout_seconds
            )
            
            logger.info(f"Data Summarizer LLM initialized with model: {model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            self.llm = None
            logger.warning("[DATA_SUMMARIZER] LLM initialization failed, will retry when config is updated")
    
    def _initialize_chain(self) -> None:
        """Initialize the LangChain chain for data summarization"""
        try:
            # Create prompt template for data summarization
            summary_prompt_template = """
You are an expert data analyst specializing in payment analytics. Your task is to analyze SQL query results and provide clear, actionable insights.

Original User Query: {user_query}

SQL Query Executed: {sql_query}

Query Results:
{data_summary}

Data Details:
- Total Rows: {row_count}
- Columns: {columns}
- Execution Time: {execution_time_ms}ms

INSTRUCTIONS:
1. Provide a clear, concise summary of the data in EXACTLY 60 words or less (2-3 sentences maximum)
2. Format your response as HTML using basic tags: <p>, <strong>, <em>, <span>
3. Highlight key insights and patterns with <strong> tags
4. Use business-friendly language (avoid technical jargon)
5. Include specific numbers and percentages where relevant
6. Focus on the most important findings only

Example format: <p><strong>Sales analysis</strong> reveals 1,250 transactions totaling <em>$45,678</em>. Peak activity occurred on weekends with <strong>15% higher volume</strong> than weekdays.</p>

HTML Summary:"""

            # Create prompt template
            prompt = PromptTemplate(
                input_variables=[
                    "user_query", "sql_query", "data_summary", 
                    "row_count", "columns", "execution_time_ms"
                ],
                template=summary_prompt_template
            )
            
            # Create chain with output parser
            output_parser = StrOutputParser()
            self.chain = prompt | self.llm | output_parser
            
            logger.info("Data summarization chain initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize chain: {e}")
            raise DataSummarizationError(f"Chain initialization failed: {e}", e)
    
    def summarize_data(self, execution_result: SQLExecutionResult, 
                      user_query: str = "", sql_query: str = "") -> DataSummaryResult:
        """
        Generate summary of SQL execution results
        
        Args:
            execution_result: Result from SQL execution
            user_query: Original user query for context
            sql_query: SQL query that was executed
            
        Returns:
            DataSummaryResult with summary or error
        """
        start_time = time.time()
        
        try:
            logger.info("[DATA_SUMMARIZER] Starting data summarization")
            
            # Validate input
            if not execution_result:
                return DataSummaryResult(
                    success=False,
                    error="No execution result provided"
                )
            
            if not execution_result.success:
                return DataSummaryResult(
                    success=False,
                    error=f"Cannot summarize failed execution: {execution_result.error}"
                )
            
            # Check if LLM is initialized
            if not self.llm or not self.chain:
                logger.warning("[DATA_SUMMARIZER] LLM not initialized, creating fallback summary")
                fallback_summary = self.create_fallback_summary(execution_result, user_query)
                markdown_data = self.convert_data_to_markdown_table(execution_result.data)
                
                summary_time_ms = (time.time() - start_time) * 1000
                
                return DataSummaryResult(
                    success=True,
                    summary=fallback_summary,  # Keep for backward compatibility
                    html_summary=f"<p>{fallback_summary.replace('•', '<strong>•</strong>')}</p>",  # Basic HTML format
                    markdown_data=markdown_data,  # NEW: Markdown table
                    key_insights=["LLM summarization not available - using fallback"],
                    data_points_analyzed=execution_result.row_count,
                    summary_time_ms=summary_time_ms,
                    prompt_tokens=0,
                    completion_tokens=0
                )
            
            # Prepare data for summarization
            data_summary = self._prepare_data_summary(execution_result.data)
            
            # Prepare input for the chain
            chain_input = {
                "user_query": user_query or "Data analysis query",
                "sql_query": sql_query or execution_result.query_executed or "SQL query",
                "data_summary": data_summary,
                "row_count": execution_result.row_count,
                "columns": ", ".join(execution_result.columns or []),
                "execution_time_ms": execution_result.execution_time_ms or 0
            }
            
            logger.debug(f"[DATA_SUMMARIZER] Summarizing {execution_result.row_count} rows of data")
            
            # Generate HTML summary using the chain
            html_summary_text = self.chain.invoke(chain_input)
            
            # Generate markdown table from data
            markdown_data = self.convert_data_to_markdown_table(execution_result.data)
            
            # Extract key insights
            key_insights = self._extract_key_insights(html_summary_text, execution_result.data)
            
            # Calculate processing time
            summary_time_ms = (time.time() - start_time) * 1000
            
            logger.info(f"[DATA_SUMMARIZER] Successfully generated summary in {summary_time_ms:.2f}ms")
            
            return DataSummaryResult(
                success=True,
                summary=html_summary_text.strip(),  # Keep for backward compatibility
                html_summary=html_summary_text.strip(),  # NEW: HTML formatted summary
                markdown_data=markdown_data,  # NEW: Markdown table
                key_insights=key_insights,
                data_points_analyzed=execution_result.row_count,
                summary_time_ms=summary_time_ms,
                # Estimate token usage
                prompt_tokens=self._estimate_tokens(str(chain_input)),
                completion_tokens=self._estimate_tokens(html_summary_text)
            )
            
        except Exception as e:
            summary_time_ms = (time.time() - start_time) * 1000
            error_msg = f"Data summarization failed: {str(e)}"
            
            logger.error(f"[DATA_SUMMARIZER] {error_msg} (after {summary_time_ms:.2f}ms)")
            
            return DataSummaryResult(
                success=False,
                error=error_msg,
                html_summary=None,  # NEW: Ensure new fields are None on error
                markdown_data=None,  # NEW: Ensure new fields are None on error
                summary_time_ms=summary_time_ms,
                data_points_analyzed=execution_result.row_count if execution_result else 0
            )
    
    def _prepare_data_summary(self, data: List[Dict[str, Any]]) -> str:
        """
        Prepare data for summarization by creating a concise representation
        
        Args:
            data: Raw data from SQL execution
            
        Returns:
            Formatted data summary string
        """
        if not data:
            return "No data returned from query"
        
        try:
            # Limit data size for LLM processing
            max_rows_for_summary = 50
            sample_data = data[:max_rows_for_summary]
            
            # Create a structured summary
            summary_parts = []
            
            # Add sample rows
            if len(sample_data) <= 10:
                # Show all rows if small dataset
                summary_parts.append("Complete Dataset:")
                for i, row in enumerate(sample_data, 1):
                    summary_parts.append(f"Row {i}: {json.dumps(row, default=str)}")
            else:
                # Show first few and last few rows for larger datasets
                summary_parts.append("Sample Data (First 5 rows):")
                for i, row in enumerate(sample_data[:5], 1):
                    summary_parts.append(f"Row {i}: {json.dumps(row, default=str)}")
                
                if len(data) > max_rows_for_summary:
                    summary_parts.append(f"\n... ({len(data) - max_rows_for_summary} more rows not shown)")
                
                if len(sample_data) > 5:
                    summary_parts.append("\nLast 3 rows from sample:")
                    for i, row in enumerate(sample_data[-3:], len(sample_data) - 2):
                        summary_parts.append(f"Row {i}: {json.dumps(row, default=str)}")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            logger.warning(f"[DATA_SUMMARIZER] Error preparing data summary: {e}")
            return f"Data summary preparation failed: {str(e)}"
    
    def _extract_key_insights(self, summary_text: str, data: List[Dict[str, Any]]) -> List[str]:
        """
        Extract key insights from the summary and data
        
        Args:
            summary_text: Generated summary text
            data: Original data
            
        Returns:
            List of key insights
        """
        insights = []
        
        try:
            # Data volume insight
            if data:
                insights.append(f"Dataset contains {len(data)} records")
                
                # Check for numeric columns and provide basic stats
                numeric_insights = self._analyze_numeric_data(data)
                insights.extend(numeric_insights)
                
                # Check for categorical patterns
                categorical_insights = self._analyze_categorical_data(data)
                insights.extend(categorical_insights)
            
            # Extract insights from summary text
            text_insights = self._extract_insights_from_text(summary_text)
            insights.extend(text_insights)
            
        except Exception as e:
            logger.warning(f"[DATA_SUMMARIZER] Error extracting insights: {e}")
            insights.append("Insight extraction encountered an error")
        
        return insights[:10]  # Limit to top 10 insights
    
    def _analyze_numeric_data(self, data: List[Dict[str, Any]]) -> List[str]:
        """Analyze numeric columns for insights"""
        insights = []
        
        if not data:
            return insights
        
        try:
            # Find numeric columns
            numeric_columns = []
            for key, value in data[0].items():
                if isinstance(value, (int, float)) and key.lower() not in ['id', 'count']:
                    numeric_columns.append(key)
            
            # Analyze each numeric column
            for col in numeric_columns[:3]:  # Limit to 3 columns
                values = [row.get(col, 0) for row in data if isinstance(row.get(col), (int, float))]
                if values:
                    avg_val = sum(values) / len(values)
                    max_val = max(values)
                    min_val = min(values)
                    insights.append(f"{col}: avg={avg_val:.2f}, range={min_val}-{max_val}")
                    
        except Exception as e:
            logger.debug(f"Numeric analysis error: {e}")
        
        return insights
    
    def _analyze_categorical_data(self, data: List[Dict[str, Any]]) -> List[str]:
        """Analyze categorical columns for insights"""
        insights = []
        
        if not data:
            return insights
        
        try:
            # Find categorical columns
            categorical_columns = []
            for key, value in data[0].items():
                if isinstance(value, str) and key.lower() not in ['id', 'description', 'notes']:
                    categorical_columns.append(key)
            
            # Analyze each categorical column
            for col in categorical_columns[:2]:  # Limit to 2 columns
                values = [row.get(col) for row in data if row.get(col)]
                if values:
                    unique_count = len(set(values))
                    most_common = max(set(values), key=values.count)
                    insights.append(f"{col}: {unique_count} unique values, most common: {most_common}")
                    
        except Exception as e:
            logger.debug(f"Categorical analysis error: {e}")
        
        return insights
    
    def _extract_insights_from_text(self, summary_text: str) -> List[str]:
        """Extract insights from the generated summary text"""
        insights = []
        
        try:
            # Look for key phrases that indicate insights
            lines = summary_text.split('\n')
            for line in lines:
                line = line.strip()
                if any(keyword in line.lower() for keyword in ['shows', 'indicates', 'reveals', 'suggests']):
                    if len(line) < 150:  # Keep insights concise
                        insights.append(line)
                        
        except Exception as e:
            logger.debug(f"Text insight extraction error: {e}")
        
        return insights[:5]  # Limit to 5 text insights
    
    def convert_data_to_markdown_table(self, data: List[Dict[str, Any]], max_rows: int = 50) -> str:
        """
        Convert SQL execution results to markdown table format
        
        Args:
            data: List of dictionaries representing SQL results
            max_rows: Maximum number of rows to include in table
            
        Returns:
            Markdown formatted table string
        """
        if not data:
            return "No data available"
        
        try:
            # Limit data size for readability
            limited_data = data[:max_rows]
            
            # Get column headers from first row
            headers = list(limited_data[0].keys())
            
            # Create markdown table header
            header_row = "| " + " | ".join(headers) + " |"
            separator_row = "|" + "|".join([" --- " for _ in headers]) + "|"
            
            # Create data rows
            data_rows = []
            for row in limited_data:
                formatted_values = []
                for header in headers:
                    value = row.get(header, "")
                    # Handle different data types
                    if value is None:
                        formatted_value = "null"
                    elif isinstance(value, (int, float)):
                        formatted_value = str(value)
                    elif isinstance(value, str):
                        # Escape special markdown characters
                        formatted_value = value.replace("|", "\\|").replace("\n", " ")
                    else:
                        formatted_value = str(value)
                    formatted_values.append(formatted_value)
                
                data_rows.append("| " + " | ".join(formatted_values) + " |")
            
            # Combine all parts
            table_parts = [header_row, separator_row] + data_rows
            
            # Add summary info if data was truncated
            if len(data) > max_rows:
                table_parts.append(f"\n*Showing {max_rows} of {len(data)} total rows*")
            
            return "\n".join(table_parts)
            
        except Exception as e:
            logger.warning(f"Error converting data to markdown table: {e}")
            return f"Error creating markdown table: {str(e)}"

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text (rough approximation)
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        # Rough estimation: ~4 characters per token for English text
        return len(str(text)) // 4
    
    def create_fallback_summary(self, execution_result: SQLExecutionResult, 
                               user_query: str = "") -> str:
        """
        Create a fallback summary when LLM summarization fails
        
        Args:
            execution_result: Result from SQL execution
            user_query: Original user query
            
        Returns:
            Basic summary string
        """
        try:
            if not execution_result or not execution_result.success:
                return "Query execution failed - no data to summarize"
            
            summary_parts = [
                f"Query Results Summary:",
                f"• Total rows returned: {execution_result.row_count}",
                f"• Execution time: {execution_result.execution_time_ms:.2f}ms"
            ]
            
            if execution_result.columns:
                summary_parts.append(f"• Columns: {', '.join(execution_result.columns)}")
            
            if execution_result.data and len(execution_result.data) > 0:
                summary_parts.append(f"• Sample data available for {len(execution_result.data)} records")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            return f"Unable to create summary: {str(e)}"
    
    def update_config(self, new_config: LLMConfig) -> None:
        """
        Update LLM configuration and reinitialize if needed
        
        Args:
            new_config: New LLM configuration
        """
        self.config = new_config
        self._initialize_llm()
        self._initialize_chain()
        logger.info("Data Summarizer configuration updated")
    
    def health_check(self) -> dict:
        """
        Perform health check on the data summarizer
        
        Returns:
            Health status dictionary
        """
        try:
            if not self.llm or not self.chain:
                return {
                    "status": "unhealthy",
                    "error": "LLM or chain not initialized"
                }
            
            # Create a test execution result
            test_data = [{"test_column": "test_value", "count": 1}]
            test_execution_result = SQLExecutionResult(
                success=True,
                data=test_data,
                row_count=1,
                execution_time_ms=10.0,
                query_executed="SELECT 'test' as test_column, 1 as count",
                columns=["test_column", "count"]
            )
            
            # Test summarization
            test_result = self.summarize_data(test_execution_result, "test query", "test sql")
            
            if test_result.success:
                return {
                    "status": "healthy",
                    "model": self.config.model_name,
                    "summary_time_ms": test_result.summary_time_ms
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
