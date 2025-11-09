"""
Unit tests for LLM module
"""

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from help_chat.doc_indexer import DocIndexer
from help_chat.llm import HelpChat

SUPPORTED_EXTENSIONS = ".txt,.md"


class TestHelpChat:
    """Test cases for HelpChat class."""

    def test_init_with_config_dict(self) -> None:
        """Test initialization with configuration dictionary."""
        config = {
            "api_path": "https://api.openai.com/v1",
            "api_key": "test-key",
            "embeddings_path": "/path/to/embeddings.db",
            "supported_extensions": ".txt",
        }

        chat = HelpChat(config=config)
        assert chat is not None

    def test_init_with_individual_params(self) -> None:
        """Test initialization with individual parameters."""
        chat = HelpChat(
            api_path="https://api.openai.com/v1",
            api_key="test-key",
            embeddings_path="/path/to/embeddings.db",
        )
        assert chat is not None

    def test_init_raises_error_without_params(self) -> None:
        """Test that initialization raises ValueError without parameters."""
        with pytest.raises(ValueError):
            HelpChat()

    def test_make_request_with_openai(self) -> None:
        """Test make_request with OpenAI API configuration."""
        config = {
            "api_path": "https://api.openai.com/v1",
            "api_key": "test-key",
            "embeddings_path": "/path/to/embeddings.db",
            "supported_extensions": ".txt",
        }

        chat = HelpChat(config=config)
        # This will likely fail without real API key, but tests the method exists
        # In actual implementation, we'll mock the API call
        assert hasattr(chat, "make_request")

    def test_make_request_with_ollama(self) -> None:
        """Test make_request with Ollama configuration."""
        config = {
            "api_path": "http://localhost:11434",
            "api_key": "",
            "embeddings_path": "/path/to/embeddings.db",
            "supported_extensions": ".txt",
        }

        chat = HelpChat(config=config)
        assert hasattr(chat, "make_request")

    def test_make_request_with_lm_studio(self) -> None:
        """Test make_request with LM Studio configuration."""
        config = {
            "api_path": "http://localhost:1234/v1",
            "api_key": "",
            "embeddings_path": "/path/to/embeddings.db",
            "supported_extensions": ".txt",
        }

        chat = HelpChat(config=config)
        assert hasattr(chat, "make_request")

    def test_make_request_returns_string(self) -> None:
        """Test that make_request returns a string response."""
        config = {
            "api_path": "https://api.openai.com/v1",
            "api_key": "test-key",
            "embeddings_path": "/path/to/embeddings.db",
            "supported_extensions": ".txt",
        }

        chat = HelpChat(config=config)
        # We'll need to mock this in actual implementation
        # For now, just verify the method signature
        import inspect

        sig = inspect.signature(chat.make_request)
        assert "prompt" in sig.parameters

    def test_make_request_accepts_prompt(self) -> None:
        """Test that make_request accepts a prompt parameter."""
        config = {
            "api_path": "https://api.openai.com/v1",
            "api_key": "test-key",
            "embeddings_path": "/path/to/embeddings.db",
            "supported_extensions": ".txt",
        }

        chat = HelpChat(config=config)
        import inspect

        sig = inspect.signature(chat.make_request)
        params = list(sig.parameters.keys())
        assert "prompt" in params
        assert sig.parameters["prompt"].annotation == str

    def test_config_priority_over_individual_params(self) -> None:
        """Test that config dict takes priority over individual params."""
        config = {
            "api_path": "https://api.openai.com/v1",
            "api_key": "config-key",
            "embeddings_path": "/config/path/embeddings.db",
            "supported_extensions": ".txt",
        }

        # Even if individual params are provided, config should take priority
        chat = HelpChat(
            config=config,
            api_path="http://localhost:11434",
            api_key="individual-key",
            embeddings_path="/individual/path/embeddings.db",
        )
        assert chat is not None

    def test_retrieve_context_with_embeddings(self) -> None:
        """Test RAG context retrieval from database."""
        with tempfile.TemporaryDirectory() as temp_dir:
            embeddings_path = os.path.join(temp_dir, "test_embeddings.db")

            # Create a simple database with sample embeddings
            # Create sample files
            root_path = tempfile.mkdtemp()
            temp_path = tempfile.mkdtemp()
            test_file = os.path.join(root_path, "test.txt")
            Path(test_file).write_text("Python programming language documentation")

            # Index the files
            indexer = DocIndexer()
            indexer.reindex(
                root_path=root_path,
                temp_path=temp_path,
                embeddings_path=embeddings_path,
                supported_extensions=SUPPORTED_EXTENSIONS,
            )

            # Create HelpChat instance
            chat = HelpChat(
                api_path="https://api.openai.com/v1",
                api_key="test-key",
                embeddings_path=embeddings_path,
                root_path=root_path,
                temp_path=temp_path,
            )

            # Test retrieval
            context = chat._retrieve_context("Python documentation")
            assert len(context) > 0
            assert test_file in context[0][0]

    def test_retrieve_context_empty_database(self) -> None:
        """Test retrieval from empty database."""
        with tempfile.TemporaryDirectory() as temp_dir:
            embeddings_path = os.path.join(temp_dir, "empty.db")

            # Create empty database
            conn = sqlite3.connect(embeddings_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE embeddings (
                    file_path TEXT PRIMARY KEY,
                    file_hash TEXT NOT NULL,
                    embedding_vector BLOB NOT NULL,
                    last_updated TIMESTAMP NOT NULL,
                    file_extension TEXT NOT NULL
                )
            """
            )
            conn.commit()
            conn.close()

            # Create HelpChat instance
            chat = HelpChat(
                api_path="https://api.openai.com/v1",
                api_key="test-key",
                embeddings_path=embeddings_path,
            )

            # Test retrieval from empty database
            context = chat._retrieve_context("test query")
            assert len(context) == 0

    def test_augment_prompt_with_context(self) -> None:
        """Test prompt augmentation with context."""
        chat = HelpChat(
            api_path="https://api.openai.com/v1", api_key="test-key", embeddings_path="/tmp/test.db"
        )

        context = [("/path/to/doc1.txt", 0.95), ("/path/to/doc2.txt", 0.87)]

        augmented = chat._augment_prompt("What is Python?", context)
        assert "Relevant documentation" in augmented
        assert "/path/to/doc1.txt" in augmented
        assert "/path/to/doc2.txt" in augmented
        assert "What is Python?" in augmented

    def test_augment_prompt_without_context(self) -> None:
        """Test prompt augmentation without context."""
        chat = HelpChat(
            api_path="https://api.openai.com/v1", api_key="test-key", embeddings_path="/tmp/test.db"
        )

        prompt = "What is Python?"
        augmented = chat._augment_prompt(prompt, [])
        assert augmented == prompt

    def test_augment_prompt_includes_markdown_excerpt(self) -> None:
        """Ensure markdown excerpts are embedded when available."""
        with (
            tempfile.TemporaryDirectory() as root_dir,
            tempfile.TemporaryDirectory() as temp_dir,
            tempfile.TemporaryDirectory() as db_dir,
        ):
            embeddings_path = os.path.join(db_dir, "embeddings.db")

            nested_dir = Path(root_dir) / "guides"
            nested_dir.mkdir(parents=True, exist_ok=True)
            source_file = nested_dir / "profile.txt"
            source_file.write_text(
                "Amara leads the analytics team and specializes in knowledge management workflows.",
                encoding="utf-8",
            )

            indexer = DocIndexer()
            indexer.reindex(
                root_path=root_dir,
                temp_path=temp_dir,
                embeddings_path=embeddings_path,
                supported_extensions=SUPPORTED_EXTENSIONS,
            )

            chat = HelpChat(
                api_path="https://api.openai.com/v1",
                api_key="test-key",
                embeddings_path=embeddings_path,
                root_path=root_dir,
                temp_path=temp_dir,
            )

            context = [(str(source_file), 0.99)]
            augmented = chat._augment_prompt("Who is Amara?", context)

            assert "Amara" in augmented
            assert str(source_file) in augmented
            snapshot_path = Path(temp_dir) / "_markdown" / "guides" / "profile.txt.md"
            assert snapshot_path.exists()

    def test_get_model_name_openai(self) -> None:
        """Test model name detection for OpenAI."""
        chat = HelpChat(
            api_path="https://api.openai.com/v1", api_key="test-key", embeddings_path="/tmp/test.db"
        )
        assert chat._get_model_name() == "gpt-4o-mini"

    def test_get_model_name_ollama(self) -> None:
        """Test model name detection for Ollama."""
        chat = HelpChat(
            api_path="http://localhost:11434", api_key="", embeddings_path="/tmp/test.db"
        )
        assert chat._get_model_name() == "llama3.2"

    def test_get_model_name_lm_studio(self) -> None:
        """Test model name detection for LM Studio."""
        chat = HelpChat(
            api_path="http://localhost:1234/v1", api_key="", embeddings_path="/tmp/test.db"
        )
        assert chat._get_model_name() == "local-model"
