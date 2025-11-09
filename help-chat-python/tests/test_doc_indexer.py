"""
Unit tests for DocIndexer module
"""

import os
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path

import pytest
from help_chat.doc_indexer import DocIndexer

SUPPORTED_EXTENSIONS = ".txt,.md,.json"


class TestDocIndexer:
    """Test cases for DocIndexer.reindex() method."""

    @pytest.fixture
    def temp_dirs(self) -> tuple:
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as root_dir:
            with tempfile.TemporaryDirectory() as temp_dir:
                with tempfile.TemporaryDirectory() as db_dir:
                    embeddings_path = os.path.join(db_dir, "embeddings.db")
                    yield root_dir, temp_dir, embeddings_path

    def test_reindex_with_config_dict(self, temp_dirs: tuple) -> None:
        """Test reindex using configuration dictionary."""
        root_path, temp_path, embeddings_path = temp_dirs

        config = {
            "root_path": root_path,
            "temp_path": temp_path,
            "embeddings_path": embeddings_path,
            "supported_extensions": SUPPORTED_EXTENSIONS,
        }

        indexer = DocIndexer()
        # Should not raise any exceptions
        indexer.reindex(config=config)

    def test_reindex_with_individual_params(self, temp_dirs: tuple) -> None:
        """Test reindex using individual parameters."""
        root_path, temp_path, embeddings_path = temp_dirs

        indexer = DocIndexer()
        # Should not raise any exceptions
        indexer.reindex(root_path=root_path, temp_path=temp_path, embeddings_path=embeddings_path, supported_extensions=SUPPORTED_EXTENSIONS)

    def test_reindex_creates_temp_path(self, temp_dirs: tuple) -> None:
        """Test that reindex creates temp_path if it doesn't exist."""
        root_path, _, embeddings_path = temp_dirs
        temp_path = os.path.join(tempfile.gettempdir(), "test_temp_dir_12345")

        try:
            indexer = DocIndexer()
            indexer.reindex(
                root_path=root_path,
                temp_path=temp_path,
                embeddings_path=embeddings_path,
                supported_extensions=SUPPORTED_EXTENSIONS,
            )

            assert os.path.exists(temp_path)
            assert os.path.isdir(temp_path)
        finally:
            if os.path.exists(temp_path):
                shutil.rmtree(temp_path, ignore_errors=True)

    def test_reindex_empties_temp_path(self, temp_dirs: tuple) -> None:
        """Test that reindex empties temp_path if it contains files."""
        root_path, temp_path, embeddings_path = temp_dirs

        # Create a file in temp_path
        test_file = os.path.join(temp_path, "test.txt")
        Path(test_file).write_text("test content")
        Path(os.path.join(temp_path, ".help_chat_temp")).touch()
        os.makedirs(os.path.join(temp_path, "_markdown"), exist_ok=True)

        indexer = DocIndexer()
        indexer.reindex(root_path=root_path, temp_path=temp_path, embeddings_path=embeddings_path, supported_extensions=SUPPORTED_EXTENSIONS)

        # temp_path should only contain the sentinel marker and markdown folder
        remaining = [
            item for item in os.listdir(temp_path) if item not in {".help_chat_temp", "_markdown"}
        ]
        assert not remaining
        assert os.path.isdir(os.path.join(temp_path, "_markdown"))

    def test_reindex_creates_embeddings_database(self, temp_dirs: tuple) -> None:
        """Test that reindex creates embeddings database if it doesn't exist."""
        root_path, temp_path, embeddings_path = temp_dirs

        indexer = DocIndexer()
        indexer.reindex(root_path=root_path, temp_path=temp_path, embeddings_path=embeddings_path, supported_extensions=SUPPORTED_EXTENSIONS)

        assert os.path.exists(embeddings_path)

        # Verify database schema
        conn = sqlite3.connect(embeddings_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        conn.close()

        assert len(tables) > 0

    def test_reindex_raises_error_for_missing_root_path(self, temp_dirs: tuple) -> None:
        """Test that reindex raises FileNotFoundError if root_path doesn't exist."""
        _, temp_path, embeddings_path = temp_dirs
        non_existent_path = "/path/that/does/not/exist"

        indexer = DocIndexer()
        with pytest.raises(FileNotFoundError):
            indexer.reindex(
                root_path=non_existent_path, temp_path=temp_path, embeddings_path=embeddings_path
            )

    def test_reindex_raises_error_without_params(self) -> None:
        """Test that reindex raises ValueError if no parameters provided."""
        indexer = DocIndexer()
        with pytest.raises(ValueError):
            indexer.reindex()

    def test_database_schema_correct(self, temp_dirs: tuple) -> None:
        """Test that database has correct schema."""
        root_path, temp_path, embeddings_path = temp_dirs

        indexer = DocIndexer()
        indexer.reindex(root_path=root_path, temp_path=temp_path, embeddings_path=embeddings_path, supported_extensions=SUPPORTED_EXTENSIONS)

        conn = sqlite3.connect(embeddings_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(embeddings)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        conn.close()

        expected_columns = {
            "file_path": "TEXT",
            "file_hash": "TEXT",
            "embedding_vector": "BLOB",
            "last_updated": "TIMESTAMP",
            "file_extension": "TEXT",
        }

        for col_name, col_type in expected_columns.items():
            assert col_name in columns
            assert col_type in columns[col_name]

    def test_reindex_processes_supported_files(self, temp_dirs: tuple) -> None:
        """Test that reindex processes supported file types."""
        root_path, temp_path, embeddings_path = temp_dirs

        # Create test files
        test_txt_file = os.path.join(root_path, "test.txt")
        test_md_file = os.path.join(root_path, "test.md")
        Path(test_txt_file).write_text("Test content")
        Path(test_md_file).write_text("# Test markdown")

        indexer = DocIndexer()
        indexer.reindex(root_path=root_path, temp_path=temp_path, embeddings_path=embeddings_path, supported_extensions=SUPPORTED_EXTENSIONS)

        # Check database has records
        conn = sqlite3.connect(embeddings_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM embeddings")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 2

        markdown_dir = os.path.join(temp_path, "_markdown")
        assert os.path.isdir(markdown_dir)
        markdown_files = os.listdir(markdown_dir)
        assert len(markdown_files) == 2

    def test_markdown_snapshots_preserve_relative_structure(self, temp_dirs: tuple) -> None:
        """Ensure markdown exports mirror root_path structure."""
        root_path, temp_path, embeddings_path = temp_dirs

        nested_dir = Path(root_path) / "nested"
        nested_dir.mkdir(parents=True, exist_ok=True)

        root_file = Path(root_path) / "shared.txt"
        nested_file = nested_dir / "shared.txt"

        root_file.write_text("Root level content", encoding="utf-8")
        nested_file.write_text("Nested content", encoding="utf-8")

        indexer = DocIndexer()
        indexer.reindex(root_path=root_path, temp_path=temp_path, embeddings_path=embeddings_path, supported_extensions=SUPPORTED_EXTENSIONS)

        markdown_dir = Path(temp_path) / "_markdown"
        root_markdown = markdown_dir / "shared.txt.md"
        nested_markdown = markdown_dir / "nested" / "shared.txt.md"

        assert root_markdown.is_file()
        assert nested_markdown.is_file()
        assert "Root level content" in root_markdown.read_text(encoding="utf-8")
        assert "Nested content" in nested_markdown.read_text(encoding="utf-8")

    def test_reindex_preserves_markdown_for_unchanged_files(self, temp_dirs: tuple) -> None:
        """Ensure reindex does not rewrite markdown for unchanged documents."""
        root_path, temp_path, embeddings_path = temp_dirs

        note = Path(root_path) / "note.txt"
        note.write_text("Important content about Amara and the analytics team.", encoding="utf-8")

        indexer = DocIndexer()
        indexer.reindex(root_path=root_path, temp_path=temp_path, embeddings_path=embeddings_path, supported_extensions=SUPPORTED_EXTENSIONS)

        markdown_dir = Path(temp_path) / "_markdown"
        snapshot = markdown_dir / "note.txt.md"
        assert snapshot.exists()

        original_text = snapshot.read_text(encoding="utf-8")
        original_mtime = snapshot.stat().st_mtime

        time.sleep(1)
        indexer.reindex(root_path=root_path, temp_path=temp_path, embeddings_path=embeddings_path, supported_extensions=SUPPORTED_EXTENSIONS)

        assert snapshot.exists()
        assert snapshot.read_text(encoding="utf-8") == original_text
        assert abs(snapshot.stat().st_mtime - original_mtime) < 1e-6

    def test_reindex_updates_changed_files(self, temp_dirs: tuple) -> None:
        """Test that reindex updates records when files change."""
        root_path, temp_path, embeddings_path = temp_dirs

        # Create initial file
        test_file = os.path.join(root_path, "test.txt")
        Path(test_file).write_text("Initial content")

        indexer = DocIndexer()
        indexer.reindex(root_path=root_path, temp_path=temp_path, embeddings_path=embeddings_path, supported_extensions=SUPPORTED_EXTENSIONS)

        # Get initial hash
        conn = sqlite3.connect(embeddings_path)
        cursor = conn.cursor()
        cursor.execute("SELECT file_hash FROM embeddings WHERE file_path = ?", (test_file,))
        initial_hash = cursor.fetchone()[0]
        conn.close()

        # Modify file
        Path(test_file).write_text("Modified content")

        # Reindex
        indexer.reindex(root_path=root_path, temp_path=temp_path, embeddings_path=embeddings_path, supported_extensions=SUPPORTED_EXTENSIONS)

        # Get new hash
        conn = sqlite3.connect(embeddings_path)
        cursor = conn.cursor()
        cursor.execute("SELECT file_hash FROM embeddings WHERE file_path = ?", (test_file,))
        new_hash = cursor.fetchone()[0]
        conn.close()

        assert new_hash != initial_hash

    def test_reindex_removes_deleted_files(self, temp_dirs: tuple) -> None:
        """Test that reindex removes records for deleted files."""
        root_path, temp_path, embeddings_path = temp_dirs

        # Create test file
        test_file = os.path.join(root_path, "test.txt")
        Path(test_file).write_text("Test content")

        indexer = DocIndexer()
        indexer.reindex(root_path=root_path, temp_path=temp_path, embeddings_path=embeddings_path, supported_extensions=SUPPORTED_EXTENSIONS)

        # Verify file is in database
        conn = sqlite3.connect(embeddings_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM embeddings")
        count_before = cursor.fetchone()[0]
        conn.close()
        assert count_before == 1

        markdown_dir = Path(temp_path) / "_markdown"
        snapshot = markdown_dir / "test.txt.md"
        assert snapshot.exists()

        # Delete file
        os.remove(test_file)

        # Reindex
        indexer.reindex(root_path=root_path, temp_path=temp_path, embeddings_path=embeddings_path, supported_extensions=SUPPORTED_EXTENSIONS)

        # Verify file is removed from database
        conn = sqlite3.connect(embeddings_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM embeddings")
        count_after = cursor.fetchone()[0]
        conn.close()

        assert count_after == 0
        assert not snapshot.exists()

    def test_reindex_cleans_nested_markdown_directories(self, temp_dirs: tuple) -> None:
        """Ensure markdown snapshots and empty folders are removed for deleted nested files."""
        root_path, temp_path, embeddings_path = temp_dirs

        nested_dir = Path(root_path) / "dept" / "analytics"
        nested_dir.mkdir(parents=True, exist_ok=True)
        nested_file = nested_dir / "brief.txt"
        nested_file.write_text("Analytics brief for Amara's team.", encoding="utf-8")

        indexer = DocIndexer()
        indexer.reindex(root_path=root_path, temp_path=temp_path, embeddings_path=embeddings_path, supported_extensions=SUPPORTED_EXTENSIONS)

        markdown_root = Path(temp_path) / "_markdown"
        snapshot = markdown_root / "dept" / "analytics" / "brief.txt.md"
        assert snapshot.exists()
        assert snapshot.parent.exists()

        nested_file.unlink()
        indexer.reindex(root_path=root_path, temp_path=temp_path, embeddings_path=embeddings_path, supported_extensions=SUPPORTED_EXTENSIONS)

        assert not snapshot.exists()
        assert not snapshot.parent.exists()

    def test_reindex_skips_unsupported_files(self, temp_dirs: tuple) -> None:
        """Test that reindex skips unsupported file types."""
        root_path, temp_path, embeddings_path = temp_dirs

        # Create supported and unsupported files
        supported_file = os.path.join(root_path, "test.txt")
        unsupported_file = os.path.join(root_path, "test.xyz")
        Path(supported_file).write_text("Supported content")
        Path(unsupported_file).write_text("Unsupported content")

        indexer = DocIndexer()
        indexer.reindex(root_path=root_path, temp_path=temp_path, embeddings_path=embeddings_path, supported_extensions=SUPPORTED_EXTENSIONS)

        # Check database only has supported file
        conn = sqlite3.connect(embeddings_path)
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM embeddings")
        files = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert len(files) == 1
        assert supported_file in files
        assert unsupported_file not in files

    def test_embeddings_database_protected_in_temp_path(self) -> None:
        """Test that embeddings database is preserved when located inside temp_path."""
        with tempfile.TemporaryDirectory() as root_dir:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Place embeddings database INSIDE temp_path
                embeddings_path = os.path.join(temp_dir, "embeddings.db")

                # Create test file
                test_file = os.path.join(root_dir, "test.txt")
                Path(test_file).write_text("Test content")

                # First reindex - creates database
                indexer = DocIndexer()
                indexer.reindex(
                    root_path=root_dir,
                    temp_path=temp_dir,
                    embeddings_path=embeddings_path,
                    supported_extensions=SUPPORTED_EXTENSIONS,
                )

                # Verify database exists and has data
                assert os.path.exists(embeddings_path)
                conn = sqlite3.connect(embeddings_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM embeddings")
                count_first = cursor.fetchone()[0]
                cursor.execute("SELECT file_hash FROM embeddings WHERE file_path = ?", (test_file,))
                first_hash = cursor.fetchone()[0]
                conn.close()
                assert count_first == 1

                # Create an extra file in temp_path that should be deleted
                extra_file = os.path.join(temp_dir, "should_be_deleted.txt")
                Path(extra_file).write_text("This should be deleted")

                # Second reindex - should preserve database but delete extra file
                indexer.reindex(
                    root_path=root_dir,
                    temp_path=temp_dir,
                    embeddings_path=embeddings_path,
                    supported_extensions=SUPPORTED_EXTENSIONS,
                )

                # Verify database still exists and has same data
                assert os.path.exists(embeddings_path)
                conn = sqlite3.connect(embeddings_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM embeddings")
                count_second = cursor.fetchone()[0]
                cursor.execute("SELECT file_hash FROM embeddings WHERE file_path = ?", (test_file,))
                second_hash = cursor.fetchone()[0]
                conn.close()

                # Database should be preserved (same count and hash)
                assert count_second == count_first
                assert second_hash == first_hash

                # Extra file should be deleted
                assert not os.path.exists(extra_file)

                # Verify only protected items remain
                remaining = [
                    item
                    for item in os.listdir(temp_dir)
                    if item not in {".help_chat_temp", "_markdown", "embeddings.db"}
                ]
                assert not remaining

    def test_unsupported_file_extension_does_not_crash(self, temp_dirs: tuple) -> None:
        """Test that unsupported file extensions are handled gracefully with warnings."""
        root_path, temp_path, embeddings_path = temp_dirs

        # Create a file with unsupported extension
        unsupported_file = os.path.join(root_path, "test.xyz")
        with open(unsupported_file, "wb") as f:
            f.write(b"Binary content that cannot be converted")

        # Also create a supported file to verify indexing continues
        supported_file = os.path.join(root_path, "test.txt")
        with open(supported_file, "w", encoding="utf-8") as f:
            f.write("This is a supported text file")

        indexer = DocIndexer()

        # Should not crash, should complete successfully
        indexer.reindex(root_path=root_path, temp_path=temp_path, embeddings_path=embeddings_path, supported_extensions=SUPPORTED_EXTENSIONS)

        # Verify database was created and contains the supported file
        conn = sqlite3.connect(embeddings_path)
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM embeddings")
        results = cursor.fetchall()
        conn.close()

        # Should have indexed the supported .txt file
        # The .xyz file should not be in the database since it's not in supported_extensions list
        file_paths = [row[0] for row in results]
        assert supported_file in file_paths
        # .xyz is not in supported_extensions, so it won't even be scanned
        assert unsupported_file not in file_paths
