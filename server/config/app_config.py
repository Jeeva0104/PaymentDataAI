import os
from dotenv import load_dotenv
from typing import Dict, Any


def load_dot():
    load_dotenv()


def load_config() -> Dict[str, Any]:
    """
    Load environment configuration from .env file and environment variables.

    Returns:
        Dict containing all configuration values
    """
    # Load .env file
    load_dot()

    config = {
        # MySQL Configuration
        "mysql": {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", 3306)),
            "user": os.getenv("MYSQL_USER", "payment_user"),
            "password": os.getenv("MYSQL_PASSWORD", ""),
            "database": os.getenv("MYSQL_DATABASE", "payment_system"),
            "charset": os.getenv("MYSQL_CHARSET", "utf8mb4"),
            "max_connections": int(os.getenv("MYSQL_MAX_CONNECTIONS", 100)),
        },
        # Redis Configuration
        "redis": {
            "host": os.getenv("REDIS_HOST", "localhost"),
            "port": int(os.getenv("REDIS_PORT", 6379)),
            "password": os.getenv("REDIS_PASSWORD", None),
            "db": int(os.getenv("REDIS_DB", 0)),
            "max_connections": int(os.getenv("REDIS_MAX_CONNECTIONS", 10)),
        },
        # WebSocket Configuration
        "websocket": {
            "cors_origins": os.getenv("WEBSOCKET_CORS_ORIGINS", "*"),
            "async_mode": os.getenv("WEBSOCKET_ASYNC_MODE", "eventlet"),
            "ping_timeout": int(os.getenv("WEBSOCKET_PING_TIMEOUT", 60)),
            "ping_interval": int(os.getenv("WEBSOCKET_PING_INTERVAL", 25)),
        },
        # AI/LangChain Configuration
        "ai": {
            "model_name": os.getenv("AI_MODEL", ""),
            "api_key": os.getenv("AI_API_KEY", ""),
            "api_base": os.getenv("AI_BASE_URL", ""),
            "temperature": float(os.getenv("AI_TEMPERATURE", "0.1")),
            "timeout_seconds": int(os.getenv("AI_TIMEOUT", "30")),
            "sql_generation_temperature": float(os.getenv("AI_SQL_TEMPERATURE", "0.1")),
            "summary_temperature": float(os.getenv("AI_SUMMARY_TEMPERATURE", "0.3")),
        },
        # General Configuration
        "timezone": os.getenv("TZ", "Asia/Calcutta"),
        "debug": os.getenv("FLASK_DEBUG", "False").lower() == "true",
        "environment": os.getenv("FLASK_ENV", "development"),
    }

    return config


def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validate required configuration values.

    Args:
        config: Configuration dictionary

    Returns:
        True if configuration is valid, False otherwise
    """
    required_fields = [
        ("mysql", "host"),
        ("mysql", "user"),
        ("mysql", "password"),
        ("mysql", "database"),
        ("redis", "host"),
    ]

    for section, field in required_fields:
        if section not in config or field not in config[section]:
            print(f"Missing required configuration: {section}.{field}")
            return False

        if not config[section][field]:
            print(f"Empty required configuration: {section}.{field}")
            return False

    return True
