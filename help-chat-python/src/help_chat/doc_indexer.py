"""
DocIndexer Module

Provides document indexing and vector embedding storage functionality.
"""

import hashlib
import logging
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Set, Tuple, Union
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FuturesTimeoutError

from help_chat._compat import aifc as _compat_aifc  # noqa: F401

sys.modules.setdefault("aifc", _compat_aifc)

from markitdown import MarkItDown
from markitdown._markitdown import UnsupportedFormatException
from sentence_transformers import SentenceTransformer

from .debug_logger import DebugLogger

if TYPE_CHECKING:
    import numpy as np
    import numpy.typing as npt


def _convert_file_subprocess(file_path: str) -> Tuple[str, str]:
    """
    Subprocess worker function to convert a file to markdown.

    Args:
        file_path: Path to file to convert

    Returns:
        Tuple of (status, data):
        - ("success", text_content) on successful conversion
        - ("unsupported", error_message) for unsupported formats
        - ("error", error_message) for other errors
    """
    try:
        # MarkItDown supports images WITHOUT LLM config (via EXIF metadata + OCR).
        # LLM is only needed for AI-generated captions (llm_client= parameter).
        # Current implementation: basic image processing (metadata/OCR) only.
        markitdown = MarkItDown()
        result = markitdown.convert(file_path)
        return ("success", result.text_content)
    except UnsupportedFormatException as e:
        return ("unsupported", str(e))
    except Exception as e:
        return ("error", f"{type(e).__name__}: {str(e)}")


def _encode_text_subprocess(text_content: str, model_name: str) -> Tuple[str, Union[bytes, str]]:
    """
    Subprocess worker function to generate embeddings for text.

    Args:
        text_content: Text to encode
        model_name: SentenceTransformer model name

    Returns:
        Tuple of (status, data):
        - ("success", embedding_bytes) on successful encoding
        - ("error", error_message) for errors
    """
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(model_name)
        embedding = model.encode(text_content)
        return ("success", embedding.tobytes())  # type: ignore[attr-defined,union-attr]
    except Exception as e:
        return ("error", f"{type(e).__name__}: {str(e)}")




class DocIndexer:
    """Manages document indexing and vector embeddings."""

    _ARCHIVE_EXTENSIONS: Set[str] = {".zip", ".tar", ".gz", ".bz2", ".xz"}
    _MAX_ARCHIVE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB safety threshold
    _CONVERSION_STARTUP_BUFFER = 15  # seconds
    _EMBEDDING_STARTUP_BUFFER = 20  # seconds
    _LOG_FILE_NAME = "program_debug.log"

    def __init__(self) -> None:
        """Initialize DocIndexer with embedding model."""
        # Configure logging if not already configured
        if not logging.getLogger().handlers:
            logging.basicConfig(
                level=logging.INFO,
                format='%(levelname)s: %(message)s'
            )
        # Lazy-load the model only when needed (speeds up startup)
        self._model: Optional[SentenceTransformer] = None
        self._embedding_model_name: str = "all-MiniLM-L6-v2"  # Default model
        self.markitdown = MarkItDown()
        self._conversion_warmup_used = False
        self._conversion_executor: Optional[ProcessPoolExecutor] = None
        self._embedding_warmup_used = False
        self._embedding_executor: Optional[ProcessPoolExecutor] = None

    @property
    def model(self) -> SentenceTransformer:
        """Get embedding model, loading it on first access (lazy loading)."""
        if self._model is None:
            import sys
            print(f"Loading embedding model '{self._embedding_model_name}' (downloads on first run, cached thereafter)...", file=sys.stderr, flush=True)
            try:
                self._model = SentenceTransformer(self._embedding_model_name)
                print(f"Model '{self._embedding_model_name}' loaded successfully", file=sys.stderr, flush=True)
            except Exception as e:
                print(f"Failed to load embedding model '{self._embedding_model_name}': {e}", file=sys.stderr, flush=True)
                raise
        return self._model

    def reindex(
        self,
        config: Optional[Dict[str, Union[str, int]]] = None,
        root_path: Optional[str] = None,
        temp_path: Optional[str] = None,
        embeddings_path: Optional[str] = None,
        conversion_timeout: int = 5,
        supported_extensions: Optional[str] = None,
        embedding_model: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
        enable_debug_log: bool = False
    ) -> None:
        """
        Reindex documents and update embeddings database.

        Args:
            config: Configuration dictionary from KeyRing.build() containing
                   root_path, temp_path, embeddings_path, conversion_timeout, supported_extensions, and embedding_model
            root_path: Root directory to scan for documents (alternative to config)
            temp_path: Temporary directory path (alternative to config)
            embeddings_path: Path to embeddings database (alternative to config)
            conversion_timeout: Timeout in seconds for file conversion (default: 5)
            supported_extensions: Comma-separated list of file extensions to index (alternative to config)
            embedding_model: SentenceTransformer model name (default: "all-MiniLM-L6-v2")
            progress_callback: Optional callback function called for each file being processed.
                             Receives the file path as a string argument.

        Raises:
            ValueError: If neither config nor individual parameters are provided
            FileNotFoundError: If root_path does not exist

        Notes:
            - Accepts either a config dictionary OR individual parameters
            - Creates temp_path if it doesn't exist and ensures it's empty
            - Preserves .help_chat_temp sentinel, _markdown directory, and embeddings database during cleanup
            - Best practice: Configure embeddings_path outside temp_path to avoid confusion
            - If embeddings_path is inside temp_path, it will be automatically protected
            - Creates embeddings database if it doesn't exist
            - Database schema: file_path (TEXT PRIMARY KEY), file_hash (TEXT),
              embedding_vector (BLOB), last_updated (TIMESTAMP), file_extension (TEXT)
            - Recursively scans root_path for Markitdown-supported files
            - Updates/inserts records based on file hash changes
            - Removes records for files that no longer exist
            - Progress callback is invoked for each file being processed (if provided)
        """
        # Extract parameters from config or use individual parameters
        if config:
            try:
                root_path = str(config.get("root_path"))
            except Exception:
                root_path = None

            try:
                temp_path = str(config.get("temp_path"))
            except Exception:
                temp_path = None
            try:
                embeddings_path = str(config.get("embeddings_path"))
            except Exception:
                embeddings_path = None

            try:
                conversion_timeout = int(config.get("conversion_timeout", 5))
            except Exception:
                conversion_timeout = 5
            try:
                supported_extensions = str(config.get("supported_extensions"))
            except Exception:
                supported_extensions = None

            try:
                embedding_model = str(config.get("embedding_model")) if config.get("embedding_model") else None
            except Exception:
                embedding_model = None

            try:
                enable_debug_log = bool(config.get("enable_debug_log", False))
            except Exception:
                enable_debug_log = False

        # Validate that we have all required parameters
        if not root_path or not temp_path or not embeddings_path:
            raise ValueError("Must provide either config dict or all individual parameters")

        # Set embedding model if provided
        if embedding_model:
            self._embedding_model_name = embedding_model

        # Print embedding model info to stderr so it shows in .NET console
        import sys
        from pathlib import Path
        cache_dir = Path.home() / ".cache" / "huggingface"
        print(f"Using embedding model: {self._embedding_model_name}", file=sys.stderr, flush=True)
        print(f"Model cache location: {cache_dir}", file=sys.stderr, flush=True)

        # 1. Ensure root_path exists
        if not os.path.exists(root_path):
            DebugLogger.log(f"ERROR: Root path does not exist: {root_path}")
            raise FileNotFoundError(f"Root path does not exist: {root_path}")

        # 2. Ensure temp_path exists and is empty (preserve embeddings database)
        markdown_dir = self._prepare_temp_path(temp_path, embeddings_path)

        # Initialize debug logger once temp_path is safe to use
        DebugLogger.initialize(enable_debug_log, temp_path)
        DebugLogger.log(f"DocIndexer.reindex() started - root_path: {root_path}")
        DebugLogger.log(f"Temp path prepared: {temp_path}, markdown_dir: {markdown_dir}")

        # 3. Setup embeddings database
        self._setup_database(embeddings_path)
        DebugLogger.log(f"Embeddings database setup complete: {embeddings_path}")

        extensions_set = self._parse_supported_extensions(supported_extensions)

        # 4. Build file list and update database
        file_list = self._scan_files(root_path, extensions_set)
        DebugLogger.log(f"Scanned {len(file_list)} files from root path")
        try:
            self._update_database(
                embeddings_path,
                file_list,
                markdown_dir,
                root_path,
                conversion_timeout,
                progress_callback,
            )
        finally:
            self._shutdown_conversion_executor()
            self._shutdown_embedding_executor()
        DebugLogger.log("DocIndexer.reindex() completed successfully")

    def _prepare_temp_path(self, temp_path: str, embeddings_path: str) -> str:
        """
        Safely prepare the temporary directory used during indexing.

        Args:
            temp_path: Directory to use for temporary files during indexing
            embeddings_path: Path to embeddings database (protected from cleanup)

        Returns:
            Path to the markdown subdirectory within temp_path

        Notes:
            - Creates temp_path if it doesn't exist
            - Validates directory safety using .help_chat_temp sentinel file
            - Preserves: .help_chat_temp, _markdown, and embeddings database
            - Removes all other files and directories in temp_path
            - Best practice: Configure embeddings_path outside temp_path when possible
        """
        sentinel_name = ".help_chat_temp"
        sentinel_path = os.path.join(temp_path, sentinel_name)

        log_file_name = self._LOG_FILE_NAME

        if os.path.exists(temp_path):
            if not os.path.isdir(temp_path):
                raise ValueError(f"Temp path must be a directory: {temp_path}")

            if not os.path.exists(sentinel_path):
                existing_items = os.listdir(temp_path)
                removable_items = [item for item in existing_items if item == log_file_name]
                if len(removable_items) != len(existing_items):
                    raise RuntimeError(
                        f"Temp path '{temp_path}' is not managed by Help Chat. Choose an empty directory or one previously created by Help Chat."
                    )
                # Only legacy log files present; remove them and mark sentinel
                for item in removable_items:
                    try:
                        os.unlink(os.path.join(temp_path, item))
                    except OSError:
                        pass
                Path(sentinel_path).touch()
        else:
            os.makedirs(temp_path, exist_ok=True)
            Path(sentinel_path).touch()

        # Determine embeddings database name/path to protect
        embeddings_basename = None
        if embeddings_path:
            try:
                embeddings_abs = os.path.abspath(embeddings_path)
                temp_abs = os.path.abspath(temp_path)
                # Check if embeddings_path is inside temp_path
                if embeddings_abs.startswith(temp_abs + os.sep) or embeddings_abs == temp_abs:
                    embeddings_basename = os.path.basename(embeddings_path)
            except Exception:
                pass

        for item in os.listdir(temp_path):
            if item == sentinel_name or item == "_markdown":
                continue
            if item == log_file_name:
                item_path = os.path.join(temp_path, item)
                try:
                    os.unlink(item_path)
                except OSError:
                    pass
                continue

            # Protect embeddings database if it's inside temp_path
            if embeddings_basename and item == embeddings_basename:
                continue

            item_path = os.path.join(temp_path, item)
            try:
                if os.path.islink(item_path):
                    os.unlink(item_path)
                elif os.path.isfile(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            except OSError:
                DebugLogger.log(f"WARNING: Failed to remove temp artifact '{item_path}'")

        markdown_dir = os.path.join(temp_path, "_markdown")
        os.makedirs(markdown_dir, exist_ok=True)
        return markdown_dir

    def _setup_database(self, embeddings_path: str) -> None:
        """Create database and table if they don't exist."""
        # Create directory path if it doesn't exist
        db_dir = os.path.dirname(embeddings_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        # Create database and table
        conn = sqlite3.connect(embeddings_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS embeddings (
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

    def _delete_markdown_snapshot(self, file_path: str, markdown_dir: str, root_path: str) -> None:
        """Remove markdown snapshot associated with a deleted file."""
        try:
            root = Path(root_path).resolve()
            source = Path(file_path).resolve()
        except Exception:
            return

        try:
            relative = source.relative_to(root)
        except ValueError:
            return

        markdown_root = Path(markdown_dir).resolve()
        candidate = markdown_root / relative
        if source.suffix:
            snapshot = candidate.with_suffix(f"{source.suffix}.md")
        else:
            snapshot = candidate.with_suffix(".md")

        try:
            if snapshot.exists():
                snapshot.unlink()
                self._prune_empty_markdown_dirs(snapshot.parent, markdown_root)
        except OSError:
            pass

    def _prune_empty_markdown_dirs(self, current_dir: Path, markdown_root: Path) -> None:
        """Remove empty directories inside markdown hierarchy after snapshot deletion."""
        try:
            current_dir = current_dir.resolve()
            markdown_root = markdown_root.resolve()
        except Exception:
            return

        while markdown_root != current_dir and markdown_root in current_dir.parents:
            try:
                current_dir.rmdir()
            except OSError:
                break
            current_dir = current_dir.parent

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _parse_supported_extensions(self, supported_extensions: Optional[str]) -> Set[str]:
        """
        Parse supported_extensions string into a normalized set.

        Args:
            supported_extensions: Comma-separated list of extensions.

        Returns:
            A set of normalized extensions (lowercase, prefixed with '.').

        Raises:
            ValueError: When no extensions are provided.
        """
        if supported_extensions is None:
            raise ValueError("supported_extensions must be provided in configuration")

        tokens = [
            token.strip().lower()
            for token in str(supported_extensions).split(",")
            if token and token.strip()
        ]

        normalized = {
            token if token.startswith(".") else f".{token}"
            for token in tokens
        }

        if not normalized:
            raise ValueError("supported_extensions configuration cannot be empty")

        return normalized

    def _scan_files(self, root_path: str, extensions_set: Set[str]) -> List[Tuple[str, str, str]]:
        """
        Recursively scan root_path for supported files.

        Args:
            root_path: Directory to scan
            extensions_set: Set of normalized extensions to include.

        Returns:
            List of tuples: (file_path, file_hash, file_extension)
        """
        file_list: List[Tuple[str, str, str]] = []

        for root, dirs, files in os.walk(root_path):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1].lower()

                if file_ext in extensions_set:
                    try:
                        file_hash = self._calculate_file_hash(file_path)
                        file_list.append((file_path, file_hash, file_ext))
                    except (OSError, IOError) as e:
                        # Skip files that can't be read
                        DebugLogger.log(f"Skipped unreadable file: {file_path} ({type(e).__name__}: {str(e)})")
                        logging.warning(f"Skipping unreadable file: {file_path}")
                        continue

        return file_list

    def _generate_embedding(self, file_path: str, markdown_dir: str, root_path: str, timeout: int = 5) -> Optional[bytes]:
        """
        Generate embedding vector for a file and persist markdown snapshot.

        Args:
            file_path: Path to the file to process
            markdown_dir: Directory where markdown snapshots are stored
            root_path: Root directory being indexed
            timeout: Timeout in seconds for file conversion (default: 5)

        Returns:
            Embedding vector as bytes, or None if conversion fails/times out

        Notes:
            - Logs warnings for unsupported file types, conversion failures, or timeouts
            - Returns None if file cannot be converted (caller should skip the file)
        """
        source_path = Path(file_path).resolve()
        root = Path(root_path).resolve()

        try:
            relative_path = source_path.relative_to(root)
        except ValueError:
            relative_path = Path(source_path.name)

        markdown_base = Path(markdown_dir) / relative_path
        if source_path.suffix:
            markdown_path = markdown_base.with_suffix(f"{source_path.suffix}.md")
        else:
            markdown_path = markdown_base.with_suffix(".md")
        markdown_path.parent.mkdir(parents=True, exist_ok=True)

        text_content = ""

        file_ext = source_path.suffix.lower()
        fast_formats = {'.txt', '.md', '.json', '.csv', '.html', '.htm', '.xml'}

        if file_ext in self._ARCHIVE_EXTENSIONS:
            try:
                archive_size = source_path.stat().st_size
            except OSError:
                archive_size = self._MAX_ARCHIVE_SIZE_BYTES + 1

            if archive_size > self._MAX_ARCHIVE_SIZE_BYTES:
                logging.warning(
                    "Skipping archive exceeding size limit (%s bytes): %s",
                    archive_size,
                    file_path,
                )
                DebugLogger.log(
                    f"Archive exceeds size limit ({archive_size} bytes): {file_path}"
                )
                return None

        if file_ext in fast_formats:
            try:
                DebugLogger.log(f"Inline conversion start: {file_path}")
                result = self.markitdown.convert(file_path)
                DebugLogger.log(f"Inline conversion finished: {file_path}")
                text_content = result.text_content
            except UnsupportedFormatException as e:
                logging.warning(f"Skipping unsupported file format: {file_path} - {e}")
                DebugLogger.log(f"Unsupported format: {file_path} - {e}")
                return None
            except Exception as e:
                logging.warning(f"Skipping file due to conversion error: {file_path} ({type(e).__name__}: {e})")
                DebugLogger.log(f"Conversion error: {file_path} ({type(e).__name__}: {e})")
                return None
        else:
            text_content = self._convert_to_markdown(file_path, timeout)
            if text_content is None:
                return None

        if not text_content.strip():
            logging.warning(
                f"Skipping file with empty content: {file_path}"
            )
            DebugLogger.log(f"Empty content after conversion: {file_path}")
            return None

        try:
            markdown_path.write_text(text_content, encoding="utf-8")
            DebugLogger.log(f"Markdown snapshot written: {markdown_path}")
        except OSError:
            pass

        try:
            DebugLogger.log(f"Embedding generation start: {file_path}")
            embedding = self._encode_with_timeout(text_content, timeout, file_path)
            if embedding is None:
                return None
            DebugLogger.log(f"Embedding generation finished: {file_path}")
        except Exception as e:
            logging.warning(
                f"Skipping file due to embedding generation error: {file_path} ({type(e).__name__}: {str(e)})"
            )
            DebugLogger.log(f"Embedding generation error: {file_path} ({type(e).__name__}: {str(e)})")
            return None

        return embedding

    def _convert_to_markdown(self, file_path: str, timeout: int) -> Optional[str]:
        """
        Convert a file to markdown using a process pool executor with timeout.
        Reuses worker processes for better performance.
        """
        executor = self._ensure_conversion_executor()

        effective_timeout = timeout
        if not self._conversion_warmup_used:
            effective_timeout += self._CONVERSION_STARTUP_BUFFER

        try:
            # Submit conversion task to process pool
            future = executor.submit(_convert_file_subprocess, file_path)

            # Wait for result with timeout
            status, data = future.result(timeout=effective_timeout)

            if status == "success":
                self._conversion_warmup_used = True
                return data
            if status == "unsupported":
                logging.warning(
                    f"Skipping unsupported file format: {file_path} - {data}"
                )
                DebugLogger.log(f"Unsupported format: {file_path} - {data}")
                return None

            logging.warning(
                f"Skipping file due to conversion error: {file_path} ({data})"
            )
            DebugLogger.log(f"Conversion error: {file_path} ({data})")
            return None

        except FuturesTimeoutError:
            DebugLogger.log(f"Conversion timeout after {effective_timeout}s: {file_path}")
            logging.warning(
                f"Skipping file due to conversion timeout ({effective_timeout}s): {file_path}"
            )
            # Abandon hung executor without shutdown (prevents hanging)
            self._conversion_executor = None
            self._conversion_warmup_used = False
            return None
        except Exception as e:
            DebugLogger.log(f"Conversion error: {file_path} ({type(e).__name__}: {str(e)})")
            logging.warning(
                f"Skipping file due to conversion error: {file_path} ({type(e).__name__}: {str(e)})"
            )
            return None

    def _update_database(
        self,
        embeddings_path: str,
        file_list: List[Tuple[str, str, str]],
        markdown_dir: str,
        root_path: str,
        conversion_timeout: int,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Update database with file list.

        Args:
            embeddings_path: Path to embeddings database
            file_list: List of (file_path, file_hash, file_extension) tuples
            markdown_dir: Directory for markdown snapshots
            root_path: Root directory being indexed
            conversion_timeout: Timeout in seconds for file conversion
            progress_callback: Optional callback invoked for each file being processed
        """
        conn = sqlite3.connect(embeddings_path)
        cursor = conn.cursor()

        # Load all existing file paths and hashes from database into memory
        # This eliminates the need for individual queries per file
        cursor.execute("SELECT file_path, file_hash FROM embeddings")
        db_file_hashes = {row[0]: row[1] for row in cursor.fetchall()}

        # Get file paths from current scan
        scanned_files = {file_path for file_path, _, _ in file_list}

        # Remove records for files that no longer exist
        files_to_remove = set(db_file_hashes.keys()) - scanned_files
        for file_path in files_to_remove:
            cursor.execute("DELETE FROM embeddings WHERE file_path = ?", (file_path,))
            self._delete_markdown_snapshot(file_path, markdown_dir, root_path)
            DebugLogger.log(f"Removed missing file from index: {file_path}")

        # Pre-warm process pools to eliminate startup delay on first file
        self._warmup_process_pools()

        # Process each file in the list
        for index, (file_path, file_hash, file_ext) in enumerate(file_list, start=1):
            DebugLogger.log(f"Processing file #{index}: {file_path}")

            # Check if file exists in database using in-memory hash lookup
            db_hash = db_file_hashes.get(file_path)

            if db_hash is None:
                # New file - insert record
                embedding = self._generate_embedding(file_path, markdown_dir, root_path, conversion_timeout)
                if embedding is None:
                    # Skip file if conversion failed/timed out
                    DebugLogger.log(f"Skipped indexing due to earlier errors: {file_path}")
                    continue
                # Show progress only after successful processing
                if progress_callback:
                    progress_callback(file_path)
                timestamp = datetime.now(timezone.utc).isoformat()
                cursor.execute(
                    """
                    INSERT INTO embeddings (file_path, file_hash, embedding_vector, last_updated, file_extension)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (file_path, file_hash, embedding, timestamp, file_ext),
                )
                DebugLogger.log(f"Indexed file (new): {file_path}")
            elif db_hash != file_hash:
                # File exists but hash changed - update record
                embedding = self._generate_embedding(file_path, markdown_dir, root_path, conversion_timeout)
                if embedding is None:
                    # Skip file if conversion failed/timed out (keep old record in database)
                    DebugLogger.log(f"Retained previous embedding due to errors: {file_path}")
                    continue
                # Show progress only after successful processing
                if progress_callback:
                    progress_callback(file_path)
                timestamp = datetime.now(timezone.utc).isoformat()
                cursor.execute(
                    """
                    UPDATE embeddings
                    SET file_hash = ?, embedding_vector = ?, last_updated = ?, file_extension = ?
                    WHERE file_path = ?
                """,
                    (file_hash, embedding, timestamp, file_ext, file_path),
                )
                DebugLogger.log(f"Indexed file (updated): {file_path}")
            # If hash hasn't changed, skip embedding generation (file already processed)
            else:
                DebugLogger.log(f"No changes detected: {file_path}")

        try:
            conn.commit()
            DebugLogger.log("Database changes committed successfully")
        except sqlite3.Error as e:
            DebugLogger.log(f"ERROR: Database commit failed: {type(e).__name__}: {str(e)}")
            logging.error(f"Failed to commit database changes: {str(e)}")
            conn.rollback()
            raise
        finally:
            conn.close()
    def _encode_with_timeout(self, text_content: str, timeout: int, file_path: str) -> Optional[bytes]:
        """
        Generate embeddings using a process pool executor with timeout.
        Reuses worker processes with loaded models for better performance.
        """
        executor = self._ensure_embedding_executor()

        effective_timeout = timeout
        if not self._embedding_warmup_used:
            effective_timeout += self._EMBEDDING_STARTUP_BUFFER

        try:
            # Submit encoding task to process pool
            future = executor.submit(_encode_text_subprocess, text_content, self._embedding_model_name)

            # Wait for result with timeout
            status, data = future.result(timeout=effective_timeout)

            if status == "success":
                self._embedding_warmup_used = True
                return data  # type: ignore[return-value]

            # Error occurred in subprocess
            DebugLogger.log(f"Embedding generation error: {file_path} ({data})")
            logging.warning(f"Skipping file due to embedding generation error: {file_path} ({data})")
            return None

        except FuturesTimeoutError:
            DebugLogger.log(f"Embedding generation timeout after {effective_timeout}s: {file_path}")
            logging.warning(f"Skipping file due to embedding timeout ({effective_timeout}s): {file_path}")
            # Abandon hung executor without shutdown (prevents hanging)
            self._embedding_executor = None
            self._embedding_warmup_used = False
            return None
        except Exception as exc:  # noqa: BLE001
            DebugLogger.log(f"Embedding generation error: {file_path} ({type(exc).__name__}: {str(exc)})")
            logging.warning(f"Skipping file due to embedding generation error: {file_path} ({type(exc).__name__}: {str(exc)})")
            return None
    def _ensure_conversion_executor(self) -> ProcessPoolExecutor:
        """Ensure conversion process pool executor exists and return it."""
        if self._conversion_executor is None:
            self._conversion_executor = ProcessPoolExecutor(max_workers=2)
        return self._conversion_executor

    def _shutdown_conversion_executor(self) -> None:
        """Shutdown the conversion executor without waiting."""
        if self._conversion_executor is not None:
            # Don't wait - prevents hanging on cleanup
            self._conversion_executor = None

    def _ensure_embedding_executor(self) -> ProcessPoolExecutor:
        """Ensure embedding process pool executor exists and return it."""
        if self._embedding_executor is None:
            self._embedding_executor = ProcessPoolExecutor(max_workers=1)
        return self._embedding_executor

    def _shutdown_embedding_executor(self) -> None:
        """Shutdown the embedding executor without waiting."""
        if self._embedding_executor is not None:
            # Don't wait - prevents hanging on cleanup
            self._embedding_executor = None

    def _warmup_process_pools(self) -> None:
        """
        Pre-warm process pools by submitting simple tasks.
        This eliminates the startup delay on the first file.
        """
        DebugLogger.log("Pre-warming process pools...")

        # Warmup embedding executor with a small test encoding
        embedding_executor = self._ensure_embedding_executor()
        try:
            warmup_future = embedding_executor.submit(
                _encode_text_subprocess,
                "warmup test",
                self._embedding_model_name
            )
            # Wait for warmup with the startup buffer timeout
            warmup_future.result(timeout=self._EMBEDDING_STARTUP_BUFFER)
            self._embedding_warmup_used = True
            DebugLogger.log("Embedding process pool warmed up")
        except Exception as e:
            DebugLogger.log(f"Warning: Embedding warmup failed: {type(e).__name__}: {str(e)}")
            # Don't fail - will fall back to normal startup buffer on first real file
