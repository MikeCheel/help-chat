"""
Unit tests for KeyRing module
"""

import json
import pytest
from help_chat.keyring import KeyRing


class TestKeyRing:
    """Test cases for KeyRing.build() method."""

    def test_build_with_all_fields(self) -> None:
        """Test build with all required fields including api_key."""
        config_json = json.dumps(
            {
                "root_path": "/path/to/docs",
                "temp_path": "/path/to/temp",
                "api_path": "https://api.openai.com/v1",
                "api_key": "test-api-key",
                "embeddings_path": "/path/to/embeddings.db",
                "supported_extensions": ".txt,.md",
            }
        )

        result = KeyRing.build(config_json)

        assert result["root_path"] == "/path/to/docs"
        assert result["temp_path"] == "/path/to/temp"
        assert result["api_path"] == "https://api.openai.com/v1"
        assert result["api_key"] == "test-api-key"
        assert result["embeddings_path"] == "/path/to/embeddings.db"

    def test_build_without_api_key(self) -> None:
        """Test build without api_key defaults to empty string."""
        config_json = json.dumps(
            {
                "root_path": "/path/to/docs",
                "temp_path": "/path/to/temp",
                "api_path": "https://api.openai.com/v1",
                "embeddings_path": "/path/to/embeddings.db",
                "supported_extensions": ".txt",
            }
        )

        result = KeyRing.build(config_json)

        assert result["api_key"] == ""

    def test_build_with_empty_api_key(self) -> None:
        """Test build with explicitly empty api_key."""
        config_json = json.dumps(
            {
                "root_path": "/path/to/docs",
                "temp_path": "/path/to/temp",
                "api_path": "https://api.openai.com/v1",
                "api_key": "",
                "embeddings_path": "/path/to/embeddings.db",
                "supported_extensions": ".txt",
            }
        )

        result = KeyRing.build(config_json)

        assert result["api_key"] == ""

    def test_build_with_invalid_json(self) -> None:
        """Test build raises error with invalid JSON."""
        with pytest.raises(json.JSONDecodeError):
            KeyRing.build("not valid json")

    def test_build_with_missing_required_field(self) -> None:
        """Test build raises error when required field is missing."""
        config_json = json.dumps(
            {
                "root_path": "/path/to/docs",
                "temp_path": "/path/to/temp",
                # Missing api_path
                "embeddings_path": "/path/to/embeddings.db",
                "supported_extensions": ".txt",
            }
        )

        with pytest.raises(ValueError):
            KeyRing.build(config_json)

    def test_build_all_values_are_correct_types(self) -> None:
        """Test that all returned values have the correct types."""
        config_json = json.dumps(
            {
                "root_path": "/path/to/docs",
                "temp_path": "/path/to/temp",
                "api_path": "https://api.openai.com/v1",
                "api_key": "test-key",
                "embeddings_path": "/path/to/embeddings.db",
                "supported_extensions": ".txt",
            }
        )

        result = KeyRing.build(config_json)

        # Most values should be strings, conversion_timeout should be int, enable_debug_log should be bool
        for key, value in result.items():
            if key == "conversion_timeout":
                assert isinstance(value, int), f"{key} should be an integer, got {type(value)}"
            elif key == "enable_debug_log":
                assert isinstance(value, bool), f"{key} should be a boolean, got {type(value)}"
            else:
                assert isinstance(value, str), f"{key} should be a string, got {type(value)}"
