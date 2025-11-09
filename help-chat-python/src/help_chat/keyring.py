"""
KeyRing Module

Provides configuration management for the Help Chat package.
"""

import json
from typing import Any, Dict, Union


class KeyRing:
    """Manages configuration for Help Chat components."""

    @staticmethod
    def build(json_string: str) -> Dict[str, Union[str, int, float, bool]]:
        """
        Build a configuration dictionary from a JSON string.

        Args:
            json_string: JSON string containing configuration parameters

        Returns:
            Dictionary containing:
                - name (str): Configuration name for user identification (defaults to empty string)
                - root_path (str): Root directory path for document scanning
                - temp_path (str): Temporary directory path
                - api_path (str): API endpoint URL for LLM
                - api_key (str): API key for authentication (defaults to empty string)
                - embeddings_path (str): Path to embeddings database file
                - model_name (str): LLM model name (defaults to empty string for auto-detection)
                - conversion_timeout (int): Timeout in seconds for file conversion (defaults to 5)
                - supported_extensions (str): Comma-separated list of file extensions to index (required)
                - enable_debug_log (bool): Enable debug logging to program_debug.log (defaults to False)
                - context_documents (int): Number of document chunks to retrieve for RAG (defaults to 5)
                - max_tokens (int): Maximum tokens for LLM response (defaults to 2000)
                - temperature (float): Temperature for LLM generation (defaults to 0.7)
                - top_p (float): Top-p sampling parameter (defaults to 0.9)
                - timeout (float): Timeout in seconds for LLM requests (defaults to 60.0)

        Raises:
            json.JSONDecodeError: If json_string is not valid JSON
            ValueError: If required fields are missing
        """
        # Parse the JSON string
        data = json.loads(json_string)

        # Define required fields (api_key, model_name, name, conversion_timeout, supported_extensions, enable_debug_log are optional)
        required_fields = ["root_path", "temp_path", "api_path", "embeddings_path", "supported_extensions"]

        # Check for missing required fields
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        # Build the configuration dictionary
        supported_extensions_value = str(data["supported_extensions"]).strip()
        if not supported_extensions_value:
            raise ValueError("supported_extensions must specify at least one extension")

        config: Dict[str, Union[str, int, float, bool]] = {
            "name": str(data.get("name", "")),
            "root_path": str(data["root_path"]),
            "temp_path": str(data["temp_path"]),
            "api_path": str(data["api_path"]),
            "api_key": str(data.get("api_key", "")),
            "embeddings_path": str(data["embeddings_path"]),
            "model_name": str(data.get("model_name", "")),
            "conversion_timeout": int(data.get("conversion_timeout", 5)),
            "supported_extensions": supported_extensions_value,
            "enable_debug_log": str(data.get("enable_debug_log", "false")).lower() in ("true", "1", "yes"),
            # LLM generation parameters (optional with defaults)
            "context_documents": int(data.get("context_documents", 5)),
            "max_tokens": int(data.get("max_tokens", 2000)),
            "temperature": float(data.get("temperature", 0.7)),
            "top_p": float(data.get("top_p", 0.9)),
            "timeout": float(data.get("timeout", 60.0)),
        }

        return config
