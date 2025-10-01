"""
Unit tests for ChatHandler
Tests all major functionality including prompt construction, error handling, and caching
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import json
from datetime import datetime, timedelta

# Add server directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chat_handler import (
    ChatHandler,
    ChatHandlerError,
    ValidationError,
    ContextBuildError,
    SchemaFetchError,
    ChatHandlerCache,
    process_chat_request,
)


class TestChatHandlerCache(unittest.TestCase):
    """Test ChatHandlerCache functionality"""

    def setUp(self):
        self.cache = ChatHandlerCache()

    def test_cache_initialization(self):
        """Test cache initializes correctly"""
        self.assertEqual(len(self.cache.schema_cache), 0)
        self.assertIsNone(self.cache.system_context_cache)
        self.assertEqual(len(self.cache.cache_timestamps), 0)
        self.assertEqual(self.cache.schema_ttl, 300)
        self.assertEqual(self.cache.system_context_ttl, 600)

    def test_schema_cache_operations(self):
        """Test schema caching and retrieval"""
        test_schema = {"payment_intent": {"columns": []}}

        # Test cache miss
        result = self.cache.get_schema()
        self.assertIsNone(result)

        # Test cache set and hit
        self.cache.set_schema(test_schema)
        result = self.cache.get_schema()
        self.assertEqual(result, test_schema)

    def test_system_context_cache_operations(self):
        """Test system context caching and retrieval"""
        test_context = "Test system context"

        # Test cache miss
        result = self.cache.get_system_context()
        self.assertIsNone(result)

        # Test cache set and hit
        self.cache.set_system_context(test_context)
        result = self.cache.get_system_context()
        self.assertEqual(result, test_context)

    def test_cache_clear(self):
        """Test cache clearing functionality"""
        # Set some cache data
        self.cache.set_schema({"test": "data"})
        self.cache.set_system_context("test context")

        # Verify data is cached
        self.assertIsNotNone(self.cache.get_schema())
        self.assertIsNotNone(self.cache.get_system_context())

        # Clear cache
        self.cache.clear_cache()

        # Verify cache is empty
        self.assertIsNone(self.cache.get_schema())
        self.assertIsNone(self.cache.get_system_context())
        self.assertEqual(len(self.cache.cache_timestamps), 0)

    def test_cache_expiry(self):
        """Test cache expiry functionality"""
        # Set cache with very short TTL for testing
        self.cache.schema_ttl = 1  # 1 second
        self.cache.set_schema({"test": "data"})

        # Should be available immediately
        self.assertIsNotNone(self.cache.get_schema())

        # Manually expire the cache by setting old timestamp
        old_time = datetime.now() - timedelta(seconds=2)
        self.cache.cache_timestamps["default"] = old_time

        # Should be expired now
        self.assertIsNone(self.cache.get_schema())


class TestChatHandler(unittest.TestCase):
    """Test ChatHandler main functionality"""

    def setUp(self):
        self.handler = ChatHandler()
        self.mock_app_state = Mock()
        self.mock_app_state.get_mysql_connection = Mock()

    def test_handler_initialization(self):
        """Test handler initializes correctly"""
        self.assertIsNotNone(self.handler.cache)
        self.assertIsNotNone(self.handler.logger)
        self.assertIsInstance(self.handler.processing_stats, dict)
        self.assertEqual(self.handler.processing_stats["total_requests"], 0)

    def test_input_validation_success(self):
        """Test successful input validation"""
        try:
            self.handler._validate_inputs(self.mock_app_state, "test query")
        except ValidationError:
            self.fail("Validation should have passed")

    def test_input_validation_failures(self):
        """Test input validation error cases"""
        # Test None app_state
        with self.assertRaises(ValidationError) as context:
            self.handler._validate_inputs(None, "test query")
        self.assertIn("app_state cannot be None", str(context.exception))

        # Test empty query
        with self.assertRaises(ValidationError) as context:
            self.handler._validate_inputs(self.mock_app_state, "")
        self.assertIn("user_query cannot be empty", str(context.exception))

        # Test short query
        with self.assertRaises(ValidationError) as context:
            self.handler._validate_inputs(self.mock_app_state, "a")
        self.assertIn("user_query too short", str(context.exception))

        # Test long query
        long_query = "a" * 10001
        with self.assertRaises(ValidationError) as context:
            self.handler._validate_inputs(self.mock_app_state, long_query)
        self.assertIn("user_query too long", str(context.exception))

        # Test missing method
        bad_app_state = Mock()
        del bad_app_state.get_mysql_connection
        with self.assertRaises(ValidationError) as context:
            self.handler._validate_inputs(bad_app_state, "test query")
        self.assertIn("missing get_mysql_connection method", str(context.exception))

    @patch("chat_handler.is_analytics_related_query")
    @patch("chat_handler.build_user_context")
    def test_build_user_context_analytics(self, mock_build_context, mock_is_analytics):
        """Test user context building for analytics queries"""
        # Mock analytics query
        mock_is_analytics.return_value = (True, "analytics_keywords_detected")
        mock_build_context.return_value = "Analytics context"

        result = self.handler._build_user_context("show me payments")

        self.assertTrue(result["is_analytics"])
        self.assertEqual(result["reason"], "analytics_keywords_detected")
        self.assertEqual(result["context"], "Analytics context")
        self.assertEqual(result["query"], "show me payments")

    @patch("chat_handler.is_analytics_related_query")
    def test_build_user_context_non_analytics(self, mock_is_analytics):
        """Test user context building for non-analytics queries"""
        # Mock non-analytics query
        mock_is_analytics.return_value = (False, "greeting")

        result = self.handler._build_user_context("hello")

        self.assertFalse(result["is_analytics"])
        self.assertEqual(result["reason"], "greeting")
        self.assertIsNone(result["context"])
        self.assertEqual(result["query"], "hello")

    @patch("chat_handler.build_internal_user_context")
    def test_build_system_context_cache_miss(self, mock_build_context):
        """Test system context building with cache miss"""
        mock_build_context.return_value = "System context"

        result = self.handler._build_system_context()

        self.assertEqual(result, "System context")
        mock_build_context.assert_called_once()

        # Verify it's cached
        cached_result = self.handler.cache.get_system_context()
        self.assertEqual(cached_result, "System context")

    def test_build_system_context_cache_hit(self):
        """Test system context building with cache hit"""
        # Pre-populate cache
        self.handler.cache.set_system_context("Cached context")

        with patch("chat_handler.build_internal_user_context") as mock_build:
            result = self.handler._build_system_context()

            self.assertEqual(result, "Cached context")
            mock_build.assert_not_called()  # Should not call if cached

    @patch("chat_handler.get_schema")
    def test_build_tool_context_success(self, mock_get_schema):
        """Test tool context building success"""
        mock_schema = {
            "payment_intent": {
                "columns": [
                    {
                        "name": "payment_id",
                        "data_type": "varchar",
                        "nullable": "NO",
                        "key": "PRI",
                    }
                ],
                "indexes": [],
                "foreign_keys": [],
            }
        }
        mock_get_schema.return_value = mock_schema

        result = self.handler._build_tool_context(self.mock_app_state)

        self.assertIn("DATABASE SCHEMA INFORMATION", result)
        self.assertIn("PAYMENT_INTENT TABLE", result)
        self.assertIn("payment_id", result)

    @patch("chat_handler.get_schema")
    def test_build_tool_context_error_raises_exception(self, mock_get_schema):
        """Test tool context building raises SchemaFetchError when schema fetch fails"""
        mock_get_schema.side_effect = Exception("Database error")

        # Should raise SchemaFetchError when no cache and schema fetch fails
        with self.assertRaises(SchemaFetchError) as context:
            self.handler._build_tool_context(self.mock_app_state)

        self.assertIn(
            "Failed to build tool context and no cached schema available",
            str(context.exception),
        )

    @patch("chat_handler.get_schema")
    def test_build_tool_context_none_schema_raises_exception(self, mock_get_schema):
        """Test tool context building raises SchemaFetchError when get_schema returns None"""
        mock_get_schema.return_value = None

        # Should raise SchemaFetchError when get_schema returns None
        with self.assertRaises(SchemaFetchError) as context:
            self.handler._build_tool_context(self.mock_app_state)

        self.assertIn(
            "Failed to fetch schema from database: get_schema returned None",
            str(context.exception),
        )

    @patch("chat_handler.get_schema")
    def test_build_tool_context_schema_with_errors_raises_exception(
        self, mock_get_schema
    ):
        """Test tool context building raises SchemaFetchError when schema has errors"""
        mock_get_schema.return_value = {
            "payment_intent": {"error": "Connection failed"},
            "payment_attempt": {"error": "Table not found"},
        }

        # Should raise SchemaFetchError when schema contains errors
        with self.assertRaises(SchemaFetchError) as context:
            self.handler._build_tool_context(self.mock_app_state)

        self.assertIn("Schema fetch failed with errors", str(context.exception))

    @patch("chat_handler.get_schema")
    def test_build_tool_context_fallback_to_cache(self, mock_get_schema):
        """Test tool context building falls back to cache when fresh fetch fails"""
        # Pre-populate cache
        cached_schema = {
            "payment_intent": {"columns": [{"name": "id", "data_type": "varchar"}]}
        }
        self.handler.cache.set_schema(cached_schema)

        # Make fresh fetch fail
        mock_get_schema.side_effect = Exception("Database error")

        result = self.handler._build_tool_context(self.mock_app_state)

        # Should use cached schema
        self.assertIn("DATABASE SCHEMA INFORMATION", result)
        self.assertIn("PAYMENT_INTENT TABLE", result)

    def test_format_schema_for_prompt(self):
        """Test schema formatting for prompt"""
        schema_info = {
            "payment_intent": {
                "columns": [
                    {
                        "name": "payment_id",
                        "data_type": "varchar",
                        "nullable": "NO",
                        "key": "PRI",
                    },
                    {
                        "name": "amount",
                        "data_type": "bigint",
                        "nullable": "NO",
                        "key": "",
                    },
                ],
                "indexes": [
                    {"name": "idx_status", "columns": ["status"], "unique": False}
                ],
                "foreign_keys": [
                    {
                        "column": "customer_id",
                        "referenced_table": "customers",
                        "referenced_column": "id",
                    }
                ],
            }
        }

        result = self.handler._format_schema_for_prompt(schema_info)

        self.assertIn("DATABASE SCHEMA INFORMATION", result)
        self.assertIn("PAYMENT_INTENT TABLE", result)
        self.assertIn("payment_id: varchar NOT NULL (PRI)", result)
        self.assertIn("amount: bigint NOT NULL", result)
        self.assertIn("INDEX idx_status (status)", result)
        self.assertIn("customer_id → customers.id", result)

    def test_construct_final_prompt(self):
        """Test final prompt construction"""
        system_ctx = "System context"
        tool_ctx = "Tool context"
        user_ctx = {"context": "User context", "query": "test query"}

        result = self.handler._construct_final_prompt(system_ctx, tool_ctx, user_ctx)

        self.assertIn("[SYSTEM CONTEXT]", result)
        self.assertIn("System context", result)
        self.assertIn("[TOOL CONTEXT]", result)
        self.assertIn("Tool context", result)
        self.assertIn("[USER CONTEXT]", result)
        self.assertIn("User context", result)

    @patch("chat_handler.handle_non_analytics_query_direct")
    def test_handle_non_analytics_query(self, mock_handler):
        """Test non-analytics query handling"""
        mock_handler.return_value = {"response": "Hello! I can help with analytics."}

        result = self.handler._handle_non_analytics_query("hello", "greeting")

        self.assertEqual(result, "Hello! I can help with analytics.")
        mock_handler.assert_called_once_with("hello", "greeting", self.handler.logger)

    def test_get_fallback_response(self):
        """Test fallback response generation"""
        result = self.handler._get_fallback_response("Test error")

        self.assertIn("I apologize", result)
        self.assertIn("Test error", result)
        self.assertIn("Payment analytics", result)

    def test_get_stats(self):
        """Test statistics retrieval"""
        # Simulate some processing
        self.handler.processing_stats["total_requests"] = 5
        self.handler.processing_stats["analytics_requests"] = 3

        stats = self.handler.get_stats()

        self.assertIn("processing_stats", stats)
        self.assertIn("cache_stats", stats)
        self.assertEqual(stats["processing_stats"]["total_requests"], 5)
        self.assertEqual(stats["processing_stats"]["analytics_requests"], 3)

    def test_clear_cache(self):
        """Test cache clearing"""
        # Add some cache data
        self.handler.cache.set_schema({"test": "data"})
        self.handler.cache.set_system_context("test context")

        # Clear cache
        self.handler.clear_cache()

        # Verify cache is empty
        self.assertIsNone(self.handler.cache.get_schema())
        self.assertIsNone(self.handler.cache.get_system_context())


class TestChatHandlerIntegration(unittest.TestCase):
    """Integration tests for ChatHandler"""

    def setUp(self):
        self.mock_app_state = Mock()
        self.mock_app_state.get_mysql_connection = Mock()

    @patch("chat_handler.process_chat_request")
    def test_process_chat_request_convenience_function(self, mock_process):
        """Test the convenience function"""
        mock_process.return_value = "Test response"

        result = process_chat_request(self.mock_app_state, "test query")

        self.assertEqual(result, "Test response")
        mock_process.assert_called_once()

    @patch("chat_handler.is_analytics_related_query")
    @patch("chat_handler.handle_non_analytics_query_direct")
    def test_full_non_analytics_flow(self, mock_handler, mock_is_analytics):
        """Test complete flow for non-analytics query"""
        # Mock non-analytics query
        mock_is_analytics.return_value = (False, "greeting")
        mock_handler.return_value = {"response": "Hello! I can help with analytics."}

        handler = ChatHandler()
        result = handler.process_chat_request(self.mock_app_state, "hello")

        self.assertEqual(result, "Hello! I can help with analytics.")
        self.assertEqual(handler.processing_stats["non_analytics_requests"], 1)
        self.assertEqual(handler.processing_stats["total_requests"], 1)

    @patch("chat_handler.is_analytics_related_query")
    @patch("chat_handler.build_user_context")
    @patch("chat_handler.build_internal_user_context")
    @patch("chat_handler.get_schema")
    def test_full_analytics_flow(
        self, mock_get_schema, mock_build_system, mock_build_user, mock_is_analytics
    ):
        """Test complete flow for analytics query"""
        # Mock analytics query
        mock_is_analytics.return_value = (True, "analytics_keywords_detected")
        mock_build_user.return_value = "User context"
        mock_build_system.return_value = "System context"
        mock_get_schema.return_value = {"payment_intent": {"columns": []}}

        handler = ChatHandler()
        result = handler.process_chat_request(self.mock_app_state, "show me payments")

        self.assertIn("[SYSTEM CONTEXT]", result)
        self.assertIn("[TOOL CONTEXT]", result)
        self.assertIn("[USER CONTEXT]", result)
        self.assertEqual(handler.processing_stats["analytics_requests"], 1)
        self.assertEqual(handler.processing_stats["total_requests"], 1)

    def test_error_handling_invalid_input(self):
        """Test error handling for invalid inputs"""
        handler = ChatHandler()

        # Test with None app_state
        result = handler.process_chat_request(None, "test query")

        self.assertIn("I apologize", result)
        self.assertIn("app_state cannot be None", result)
        self.assertEqual(handler.processing_stats["errors"], 1)


class TestWebSocketIntegration(unittest.TestCase):
    """Test WebSocket integration functions"""

    def setUp(self):
        # Import here to avoid circular imports during test discovery
        from websocket.events import (
            classify_and_format_response,
            handle_chat_error,
            store_query_history,
        )

        self.classify_and_format_response = classify_and_format_response
        self.handle_chat_error = handle_chat_error
        self.store_query_history = store_query_history

    def test_classify_analytics_prompt(self):
        """Test classification of analytics prompt response"""
        response = "[SYSTEM CONTEXT]\nSystem info\n[TOOL CONTEXT]\nTool info"

        response_type, formatted = self.classify_and_format_response("test", response)

        self.assertEqual(response_type, "analytics_prompt")
        self.assertEqual(formatted, response)

    def test_classify_greeting_response(self):
        """Test classification of greeting response"""
        response = "Hello! I'm your analytics assistant for Payment."

        response_type, formatted = self.classify_and_format_response("hello", response)

        self.assertEqual(response_type, "greeting")
        self.assertEqual(formatted, response)

    def test_classify_error_response(self):
        """Test classification of error response"""
        response = "Error: Unable to process your request"

        response_type, formatted = self.classify_and_format_response("test", response)

        self.assertEqual(response_type, "error")
        self.assertEqual(formatted, response)

    def test_handle_validation_error(self):
        """Test handling of validation errors"""
        base_response = {
            "query": "test",
            "session_id": "test_session",
            "timestamp": datetime.now().isoformat(),
            "status": "processed",
        }

        error = ValidationError("Invalid query format")
        result = self.handle_chat_error(base_response, error)

        self.assertEqual(result["status"], "validation_error")
        self.assertIn("Invalid query", result["response"])
        self.assertEqual(result["type"], "validation_error")

    def test_store_query_history(self):
        """Test query history storage"""
        mock_app_state = Mock()
        mock_redis = Mock()
        mock_app_state.get_redis_client.return_value = mock_redis

        self.store_query_history(
            "test_session", "test query", "test response", mock_app_state
        )

        # Verify Redis calls
        mock_redis.set.assert_called()
        mock_redis.incr.assert_called()
        mock_redis.expire.assert_called()


if __name__ == "__main__":
    # Create test suite
    test_suite = unittest.TestSuite()

    # Add test classes
    test_classes = [
        TestChatHandlerCache,
        TestChatHandler,
        TestChatHandlerIntegration,
        TestWebSocketIntegration,
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Print summary
    print(f"\n{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(
        f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%"
    )
    print(f"{'='*50}")
