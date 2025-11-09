"""
LLM Module

Provides LLM integration with RAG (Retrieval Augmented Generation) support.
"""

import heapq
import re
import numpy as np
import sqlite3
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple, Union

from openai import OpenAI, APIConnectionError, APITimeoutError
from sentence_transformers import SentenceTransformer


class HelpChat:
    """
    LLM interface with RAG support for multiple providers.

    Supports:
        - OpenAI API
        - Ollama (local LLMs)
        - LM Studio (local LLMs)
    """

    def __init__(
        self,
        config: Optional[Dict[str, Union[str, int, float]]] = None,
        api_path: Optional[str] = None,
        api_key: Optional[str] = None,
        embeddings_path: Optional[str] = None,
        model_name: Optional[str] = None,
        root_path: Optional[str] = None,
        temp_path: Optional[str] = None,
    ) -> None:
        """
        Initialize HelpChat with LLM configuration.

        Args:
            config: Configuration dictionary from KeyRing.build() containing
                   api_path, api_key, embeddings_path, and optionally model_name,
                   max_tokens, temperature, top_p, timeout
            api_path: API endpoint URL (alternative to config)
            api_key: API authentication key (alternative to config)
            embeddings_path: Path to embeddings database (alternative to config)
            model_name: LLM model name (alternative to config, empty string for auto-detection)
            root_path: Root directory for indexed documents (alternative to config)
            temp_path: Temporary path containing markdown snapshots (alternative to config)

        Raises:
            ValueError: If neither config nor individual parameters are provided
        """
        # Extract parameters from config or use individual parameters
        if config:
            self.api_path = config.get("api_path", api_path)
            self.api_key = config.get("api_key", api_key)
            self.embeddings_path = config.get("embeddings_path", embeddings_path)
            self.model_name = config.get("model_name", model_name) or ""
            # capture root/temp for context retrieval
            self.root_path = config.get("root_path", root_path)
            self.temp_path = config.get("temp_path", temp_path)
            raw_context_docs = config.get("context_documents")
            raw_max_tokens = config.get("max_tokens")
            raw_temperature = config.get("temperature")
            raw_top_p = config.get("top_p")
            raw_timeout = config.get("timeout")
        else:
            self.api_path = api_path
            self.api_key = api_key
            self.embeddings_path = embeddings_path
            self.model_name = model_name or ""
            self.root_path = root_path
            self.temp_path = temp_path
            raw_context_docs = None
            raw_max_tokens = None
            raw_temperature = None
            raw_top_p = None
            raw_timeout = None

        try:
            self.context_documents = int(raw_context_docs) if raw_context_docs is not None else 5
        except Exception:
            self.context_documents = 5

        # LLM generation parameters with optimized defaults
        try:
            self.max_tokens = int(raw_max_tokens) if raw_max_tokens is not None else 2000
        except Exception:
            self.max_tokens = 2000

        try:
            self.temperature = float(raw_temperature) if raw_temperature is not None else 0.7
        except Exception:
            self.temperature = 0.7

        try:
            self.top_p = float(raw_top_p) if raw_top_p is not None else 0.9
        except Exception:
            self.top_p = 0.9

        try:
            self.timeout = float(raw_timeout) if raw_timeout is not None else 60.0
        except Exception:
            self.timeout = 60.0

        # Validate that we have all required parameters
        if not self.api_path or self.embeddings_path is None:
            raise ValueError(
                "Must provide either config dict or all required parameters (api_path, embeddings_path)"
            )

        # Lazy-load embedding model for RAG only when needed (speeds up startup)
        self._model: Optional[SentenceTransformer] = None

        # Initialize OpenAI client (works with OpenAI, Ollama, and LM Studio)
        self.client = OpenAI(
            api_key=self.api_key if self.api_key else "not-needed",
            base_url=self.api_path,
            timeout=self.timeout
        )

    @property
    def model(self) -> SentenceTransformer:
        """Get embedding model, loading it on first access (lazy loading)."""
        if self._model is None:
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._model

    def make_request(self, prompt: str, stream: bool = True) -> Union[str, 'Iterator[str]']:
        """
        Make a request to the LLM with RAG support.

        Args:
            prompt: Text prompt/query to send to the LLM
            stream: Whether to stream the response (default: True)

        Returns:
            If stream=False: Complete LLM response text
            If stream=True: Iterator yielding response chunks

        Raises:
            ConnectionError: If unable to connect to the API endpoint
            TimeoutError: If the request times out
            RuntimeError: For other API errors

        Notes:
            - Uses embeddings_path for retrieval augmented generation
            - Automatically detects provider based on api_path
            - Retrieves relevant document chunks from embeddings database
            - Augments prompt with retrieved context before sending to LLM
            - Streaming is enabled by default for better responsiveness
        """
        # Retrieve relevant context from embeddings
        context = self._retrieve_context(prompt)

        # Augment prompt with context
        augmented_prompt = self._augment_prompt(prompt, context)

        # Determine model based on provider
        model_name = self._get_model_name()

        # Improved system prompt for more detailed responses
        system_prompt = (
            "You are a knowledgeable assistant that provides comprehensive, detailed, and accurate answers. "
            "Use the provided context from the documentation to answer questions thoroughly. "
            "When relevant information is available in the context, cite it and explain it clearly. "
            "Provide complete explanations with examples when appropriate. "
            "If the context doesn't contain enough information, acknowledge what you know and what you don't know."
        )

        # Make request to LLM with proper error handling
        try:
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": augmented_prompt},
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
                stream=stream,
            )

            if stream:
                # Return generator for streaming
                return self._stream_response(response)
            else:
                # Return complete response
                return response.choices[0].message.content or ""

        except APIConnectionError as e:
            raise ConnectionError(
                f"Failed to connect to API endpoint '{self.api_path}'. "
                f"Please verify the endpoint is correct and accessible. Error: {str(e)}"
            ) from e
        except APITimeoutError as e:
            raise TimeoutError(
                f"Request to API endpoint '{self.api_path}' timed out. "
                f"The server may be overloaded or unreachable. Error: {str(e)}"
            ) from e
        except Exception as e:
            # Catch other OpenAI API errors (authentication, rate limits, etc.)
            raise RuntimeError(
                f"API request failed: {type(e).__name__}: {str(e)}"
            ) from e

    def _stream_response(self, response):
        """
        Stream response chunks from the LLM.

        Args:
            response: OpenAI streaming response object

        Yields:
            Response text chunks
        """
        try:
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            # If streaming fails, yield error message
            yield f"\n[Error during streaming: {str(e)}]"

    def _retrieve_context(self, query: str, top_k: Optional[int] = None) -> List[Tuple[str, float]]:
        """
        Retrieve relevant document chunks from embeddings database.

        Args:
            query: User query text
            top_k: Number of top results to retrieve

        Returns:
            List of tuples: (file_path, similarity_score)
        """
        # Generate query embedding
        query_embedding = self.model.encode(query)
        query_norm = float(np.linalg.norm(query_embedding))
        if query_norm == 0.0:
            return []

        # Connect to database (validated non-None in __init__)
        assert self.embeddings_path is not None
        conn = sqlite3.connect(str(self.embeddings_path))
        cursor = conn.cursor()

        # Get all embeddings
        cursor.execute("SELECT file_path, embedding_vector FROM embeddings")

        limit = top_k if top_k is not None else self.context_documents
        if limit <= 0:
            conn.close()
            return []

        heap: List[Tuple[float, str]] = []
        candidate_limit = max(limit, 1)

        try:
            for file_path, embedding_blob in cursor:
                stored_embedding = np.frombuffer(embedding_blob, dtype=np.float32)
                stored_norm = float(np.linalg.norm(stored_embedding))
                if stored_norm == 0.0:
                    continue

                similarity = float(np.dot(query_embedding, stored_embedding) / (query_norm * stored_norm))

                if len(heap) < candidate_limit:
                    heapq.heappush(heap, (similarity, file_path))
                elif similarity > heap[0][0]:
                    heapq.heapreplace(heap, (similarity, file_path))
        finally:
            conn.close()

        if not heap:
            return []

        ranked = sorted(heap, key=lambda item: item[0], reverse=True)
        return [(file_path, score) for score, file_path in ranked[:limit]]

    def _augment_prompt(self, prompt: str, context: List[Tuple[str, float]]) -> str:
        """
        Augment user prompt with retrieved context.

        Args:
            prompt: Original user prompt
            context: Retrieved context (file_path, similarity_score) tuples

        Returns:
            Augmented prompt string
        """
        if not context:
            return prompt

        context_text = "Relevant documentation:\n\n"
        for file_path, score in context:
            snippet = self._load_markdown_excerpt(file_path, prompt)
            context_text += f"- Source: {file_path} (relevance: {score:.2f})\n"
            if snippet:
                indented = "\n".join(f"    {line}" for line in snippet.splitlines())
                context_text += f"  Content excerpt:\n{indented}\n"

        return f"{context_text}\n\nUser question: {prompt}"

    def _get_model_name(self) -> str:
        """
        Determine model name based on configuration or API path.

        Returns:
            Model name string

        Notes:
            If model_name was explicitly configured, use that.
            Otherwise, auto-detect based on api_path.
            Defaults to gpt-4o for better quality and detailed responses.
        """
        # Use configured model name if provided
        if self.model_name:
            return str(self.model_name)

        # Auto-detect based on API path (validated non-None in __init__)
        assert self.api_path is not None
        api_lower = str(self.api_path).lower()

        if "openai.com" in api_lower:
            return "gpt-4o"
        elif "localhost:11434" in api_lower or "ollama" in api_lower:
            return "llama3.2"
        elif "localhost:1234" in api_lower or "lmstudio" in api_lower:
            return "local-model"
        else:
            # Default to gpt-4o for quality responses
            return "gpt-4o"

    def _load_markdown_excerpt(self, file_path: str, query: str, limit: int = 1500) -> str:
        """
        Load a relevant excerpt from the markdown snapshot corresponding to a file path.
        When root/temp paths are unavailable the method returns an empty string.
        """
        markdown_path = self._resolve_markdown_path(file_path)
        if markdown_path is None or not markdown_path.exists():
            return ""

        try:
            raw_text = markdown_path.read_text(encoding="utf-8")
        except OSError:
            return ""

        text = raw_text.strip()
        if not text:
            return ""

        normalized = text.replace("\r\n", "\n")
        lower_text = normalized.lower()
        keywords = [token for token in re.findall(r"\w+", query.lower()) if len(token) > 3]

        match_index: Optional[int] = None
        for keyword in keywords:
            idx = lower_text.find(keyword)
            if idx != -1:
                match_index = idx
                break

        if match_index is None:
            excerpt = normalized[: limit * 2]
        else:
            half_window = max(limit // 2, 1)
            start = max(0, match_index - half_window)
            end = min(len(normalized), match_index + half_window)
            excerpt = normalized[start:end]
            if start > 0:
                excerpt = "…" + excerpt
            if end < len(normalized):
                excerpt = excerpt + "…"

        excerpt = excerpt.strip()
        if len(excerpt) > limit:
            excerpt = excerpt[:limit].rstrip() + "…"

        return excerpt

    def _resolve_markdown_path(self, file_path: str) -> Optional[Path]:
        """
        Resolve the markdown snapshot path for an indexed file.
        """
        if not self.root_path or not self.temp_path:
            return None

        try:
            root = Path(str(self.root_path)).resolve()
            temp = Path(str(self.temp_path)).resolve()
            source = Path(file_path).resolve()
        except Exception:
            return None

        try:
            relative = source.relative_to(root)
        except ValueError:
            return None

        markdown_dir = temp / "_markdown"
        base = markdown_dir / relative
        if source.suffix:
            return base.with_suffix(f"{source.suffix}.md")
        return base.with_suffix(".md")
