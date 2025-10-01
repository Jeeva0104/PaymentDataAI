"""
LangChain Integration Module

This module provides LangChain-based sequential chaining for:
1. SQL generation from natural language
2. SQL validation using security checks
3. SQL execution against MySQL database
4. Data summarization using LLM

Components:
- models: Data models and response structures
- services: Individual processing services
- chains: Sequential chain orchestrator
- validators: SQL validation logic
"""

__version__ = "1.0.0"
__author__ = "Payment Analytics Team"

# Import main components for easy access
from .chains.sequential_chain import SequentialChain
from .models.response_models import SequentialChainResult, SQLValidationResult

__all__ = [
    'SequentialChain',
    'SequentialChainResult', 
    'SQLValidationResult'
]
