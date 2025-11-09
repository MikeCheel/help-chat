# Help Chat Python

A Python package for document indexing, vector embeddings, and LLM-based help chat with Retrieval Augmented Generation (RAG) support.

## Features

- **KeyRing Module**: Configuration management for paths and API credentials
- **DocIndexer Module**: Automatic document indexing with vector embeddings using sentence-transformers
- **LLM Module**: Multi-provider LLM support with RAG capabilities
- **Multi-Format Support**: PDF, Word, Excel, PowerPoint, HTML, Markdown, and more via Markitdown
- **Vector Embeddings**: Uses sentence-transformers (all-MiniLM-L6-v2 model)
- **SQLite Storage**: Efficient embedding storage with SHA256-based change detection
- **Incremental Indexing**: Only reprocesses changed files

> **Compatibility Note**
> Python 3.13+ removed the standard `aifc` module. Help Chat ships a PSF-licensed backport (taken from CPython 3.12) to preserve audio transcription support without emitting deprecation warnings.

## Prerequisites

### To Run the Package

- **Python 3.10 or higher**
  - Download: [python.org](https://www.python.org/downloads/)
  - Verify: `python --version`
  - Recommended: Python 3.10-3.12 for best compatibility with the .NET wrapper
  - Python 3.13+ fully supported
- **pip** package manager (included with Python)
- **Internet connection** for first-time setup (downloads sentence-transformers model ~80MB)
- **Disk space**: At least 500MB free for models and embeddings
- **LLM Provider Access** (choose one):
  - **Cloud**: API key for OpenAI, DeepSeek, or other OpenAI-compatible service
  - **Local**: Ollama or LM Studio running with a downloaded model

### For Development

Additional requirements for contributing to the package:

- **Git** for version control
- **Python virtual environment** (venv or virtualenv)
- **Development tools**:
  - `pytest` - Testing framework
  - `black` - Code formatting
  - `flake8` - Linting
  - `mypy` - Type checking
  - All installed via `pip install -e ".[dev]"`

## Requirements

- Python 3.10 or higher
- Dependencies managed via `pyproject.toml`

## Development Setup

1. **Create a virtual environment**
   ```bash
   cd help-chat-python
   python -m venv .venv
   source .venv/bin/activate          # .venv\Scripts\activate on Windows
   pip install -e ".[dev]"
   pytest                              # optional smoke test
   ```
2. **Linting & typing**
   - `black src tests`
   - `flake8 src tests`
   - `mypy src`
3. **Deactivate when finished**
   ```bash
   deactivate
   ```

## Running Locally

1. **Install the package into your environment**
   ```bash
   cd help-chat-python
   source .venv/bin/activate
   pip install -e .
   ```
2. **Set up working directories**
   ```bash
   mkdir -p /opt/help-chat/{docs,temp,store}
   ```
3. **Reindex documents**
   ```bash
   python -m help_chat.cli --command reindex --config-file config.json
   ```
   Example `config.json` with optimized LLM parameters:
   ```json
   {
     "name": "My Project Docs",
     "root_path": "/opt/help-chat/docs",
     "temp_path": "/opt/help-chat/temp",
     "embeddings_path": "/opt/help-chat/store/embeddings.db",
     "api_path": "https://api.openai.com/v1",
     "api_key": "sk-your-key",
     "model_name": "",
     "conversion_timeout": 5,
     "supported_extensions": ".pdf,.docx,.pptx,.xlsx,.md,.txt",
     "enable_debug_log": false,
     "context_documents": 5,
     "max_tokens": 2000,
     "temperature": 0.7,
     "top_p": 0.9,
     "timeout": 60.0
   }
   ```
   Markdown snapshots are written to `<temp_path>/_markdown`, mirroring the `<root_path>` directory layout so identically named files never collide. Each export keeps the original extension and appends `.md` (for example, `report.pdf` -> `report.pdf.md`) for easy inspection. Re-running `reindex` only recomputes embeddings for documents whose content hash changes; untouched files keep their existing markdown exports so repeated runs stay fast.
4. **Automation tips**
   - Cron: `0 * * * * /opt/help-chat/.venv/bin/python -m help_chat.cli --command reindex --config-file /etc/help-chat/config.json`
   - Windows Task Scheduler: run `python.exe -m help_chat.cli --command reindex --config-file C:\help-chat\config.json`
5. **Share interpreter with the .NET console**
   - Export `HELPCHAT_PYTHON_PATH` (or set it via `setx`) so HelpChat.Console reuses the same runtime.

## Command Line Interface (CLI) Usage

The Python package includes a CLI for standalone use without the .NET wrapper:

### Available Commands

1. **validate** - Validate configuration file
   ```bash
   python -m help_chat.cli --command validate --config-file config.json
   ```

2. **reindex** - Index or reindex documents
   ```bash
   python -m help_chat.cli --command reindex --config-file config.json
   ```

3. **make-request** - Make a single LLM request (requires prompt file)
   ```bash
   # Create a prompt file
   echo "What are the system requirements?" > prompt.txt

   # Make request
   python -m help_chat.cli --command make-request --config-file config.json --prompt-file prompt.txt
   ```

### CLI Response Format

All CLI commands return JSON responses:

**Success:**
```json
{
  "status": "ok",
  "data": "response content here"
}
```

**Error:**
```json
{
  "status": "error",
  "message": "error description"
}
```

**Progress (during reindex):**
```json
{
  "status": "progress",
  "file": "/path/to/file.pdf"
}
```

### Example: Complete Workflow

```bash
# 1. Create config file
cat > config.json <<EOF
{
  "name": "My Docs",
  "root_path": "/home/user/documents",
  "temp_path": "/tmp/help-chat",
  "embeddings_path": "/tmp/help-chat/embeddings.db",
  "api_path": "https://api.openai.com/v1",
  "api_key": "sk-your-key",
  "model_name": "",
  "supported_extensions": ".pdf,.docx,.md,.txt",
  "context_documents": 5,
  "max_tokens": 2000,
  "temperature": 0.7,
  "top_p": 0.9,
  "timeout": 60.0
}
EOF

# 2. Validate configuration
python -m help_chat.cli --command validate --config-file config.json

# 3. Index documents
python -m help_chat.cli --command reindex --config-file config.json

# 4. Make a request
echo "How do I get started?" > question.txt
python -m help_chat.cli --command make-request --config-file config.json --prompt-file question.txt
```

### Automation with CLI

**Linux Cron (hourly reindex):**
```bash
0 * * * * /opt/help-chat/.venv/bin/python -m help_chat.cli --command reindex --config-file /etc/help-chat/config.json >> /var/log/help-chat-reindex.log 2>&1
```

**Windows Task Scheduler:**
```powershell
# Create scheduled task for daily 2 AM reindex
$action = New-ScheduledTaskAction -Execute "python.exe" -Argument "-m help_chat.cli --command reindex --config-file C:\help-chat\config.json"
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "HelpChat Reindex" -Description "Daily document reindex"
```

## Updating

If you already have help-chat-python installed and want to update to the latest version:

### 1. Backup Your Data (Recommended)

Before updating, back up important data:

```bash
# Backup embeddings database (preserves your indexed documents)
cp /opt/help-chat/store/embeddings.db /opt/help-chat/store/embeddings.db.backup

# Windows PowerShell:
# Copy-Item "C:\help-chat\store\embeddings.db" "C:\help-chat\store\embeddings.db.backup"
```

### 2. Update the Code

Pull the latest changes from the repository:

```bash
git pull origin main
```

### 3. Update Dependencies

**If using a virtual environment (recommended):**

```bash
cd help-chat-python
source .venv/bin/activate  # .venv\Scripts\activate on Windows
pip install -e . --upgrade
deactivate
```

**If using system Python:**

```bash
cd help-chat-python
pip install -e . --upgrade
```

**For development installations:**

```bash
pip install -e ".[dev]" --upgrade
```

### 4. Check Configuration

Review your configuration JSON files for any new settings. Compare with the [Configuration Settings Reference](#configuration-settings-reference) table below.

New optional settings can typically be left at their defaults:
- `name` - Configuration name for user identification (optional, defaults to empty)
- `model_name` - Added in recent versions (optional, auto-detects if empty)
- `conversion_timeout` - Timeout in seconds for file conversion (optional, defaults to 5)
- `supported_extensions` - **Required.** File types to index (comma-separated with leading dots)
- `context_documents` - Defaults to 3 if not specified

**Breaking Changes**: Check the release notes for any changes to required fields or API signatures.

### 5. When to Re-index

**You DON'T need to re-index if:**
- You're just updating the Python package code
- Your documents haven't changed
- No new documents were added to your `root_path`

**You SHOULD re-index if:**
- You've added new documents to your `root_path`
- You've modified existing documents
- Release notes mention improvements to embedding generation
- Release notes mention changes to the sentence-transformers model

**Your embeddings database is automatically preserved** during package updates. The reindex process uses SHA256 hashes to detect changes and only processes new or modified files.

To re-index:

```bash
# Using the CLI
python -m help_chat.cli --command reindex --config-file config.json

# Or programmatically
python -c "
from help_chat.keyring import KeyRing
from help_chat.doc_indexer import DocIndexer
import json

with open('config.json') as f:
    config = KeyRing.build(f.read())
indexer = DocIndexer()
indexer.reindex(config)
"
```

### 6. Run Tests

Verify the update succeeded:

```bash
cd help-chat-python
source .venv/bin/activate  # .venv\Scripts\activate on Windows

# Run tests
pytest

# Check code coverage (optional)
pytest --cov=help_chat --cov-report=term

# Expected: All 39+ tests pass, 91%+ coverage
```

### 7. Verify Your Application

Test basic functionality:

```bash
# Verify package imports correctly
python -c "import help_chat; print(f'help_chat version OK')"

# Test a simple indexing operation (adjust paths as needed)
python -m help_chat.cli --command reindex --config-file your-config.json
```

Check that:
- Package imports without errors
- Reindex completes successfully
- Embeddings database is updated
- No deprecation warnings or errors in output

### Rollback Procedure

If you encounter issues after updating:

```bash
# Restore your embeddings database
cp /opt/help-chat/store/embeddings.db.backup /opt/help-chat/store/embeddings.db
# Windows: Copy-Item "C:\help-chat\store\embeddings.db.backup" "C:\help-chat\store\embeddings.db"

# Revert to previous git commit
git log --oneline -10  # Find the commit hash you want
git checkout <previous-commit-hash>

# Reinstall the previous version
pip install -e . --force-reinstall
```

### Migration Notes

**Python Version Compatibility:**
- Python 3.10-3.12: Full native support
- Python 3.13+: Fully supported (includes backported `aifc` module)
- Upgrading Python version does NOT require re-indexing

**Sentence-Transformers Model:**
- The default model (`all-MiniLM-L6-v2`) is cached locally after first download
- Updating the package does NOT re-download the model
- If you want to force a model update: delete `~/.cache/torch/sentence_transformers/`

**Configuration Changes:**
- `model_name` parameter added in recent versions (optional)
- If your config doesn't have `model_name`, it will auto-detect (backward compatible)

### Updating from PyPI

If you installed from PyPI instead of source:

```bash
# Update to latest version
pip install --upgrade help-chat-python

# Or update to specific version
pip install --upgrade help-chat-python==<version>

# Verify version
python -c "import help_chat; print(help_chat.__version__)"
```

### Configuration Settings Reference

| Setting | Required | Description | Default |
| --- | --- | --- | --- |
| `name` | Optional | Configuration name for user identification. | `""` |
| `root_path` | Yes | Directory recursively scanned for documents to index. | n/a |
| `temp_path` | Yes | Working directory for temporary files and `_markdown` exports. Must be dedicated to Help Chat. | n/a |
| `embeddings_path` | Yes | SQLite database file for storing embeddings; created automatically if missing. | n/a |
| `api_path` | Yes | Base URL for the LLM provider (OpenAI, DeepSeek, Ollama, LM Studio, etc.). | n/a |
| `api_key` | Optional | Provider API key. Use an empty string for providers that do not require authentication. | `""` |
| `model_name` | Optional | Explicit model identifier. Leave blank to allow auto-detection from `api_path`. | `""` |
| `conversion_timeout` | Optional | Timeout in seconds for file conversion. Prevents hanging on problematic files. | `5` |
| `supported_extensions` | **Yes** | Comma-separated list of file extensions to index (e.g., ".pdf,.docx,.txt"). Must be explicitly configured. | n/a |
| `enable_debug_log` | Optional | Enable debug logging to `program_debug.log` inside `temp_path` for troubleshooting. | `false` |
| `context_documents` | Optional | Number of RAG documents to include as context. Higher = more detail but slower. | `5` |
| `max_tokens` | Optional | Maximum tokens for LLM response. Controls response length and prevents runaway generation. | `2000` |
| `temperature` | Optional | LLM temperature (0.0-2.0). Lower = more focused/deterministic, higher = more creative. | `0.7` |
| `top_p` | Optional | Top-p sampling parameter (0.0-1.0). Controls diversity of token selection. | `0.9` |
| `timeout` | Optional | Timeout in seconds for LLM requests. Prevents hanging on slow or unresponsive endpoints. | `60.0` |

> **Note on `conversion_timeout`:** This prevents the indexer from hanging indefinitely on problematic files (e.g., corrupted documents, extremely large files). Files that exceed the timeout are skipped and logged. The default of 5 seconds works well for most documents.

> **Note on `supported_extensions`:** **REQUIRED**. You must explicitly specify which file types to index. Extensions should be comma-separated with leading dots. Recommended value (known working): `".pdf,.docx,.pptx,.xlsx,.md,.txt"`. Exclude images (.jpg, .jpeg), archives (.zip), legacy binary formats (.doc), and audio files (.wav, .mp3) as these can cause performance issues or hanging. The application will fail with a `ValueError` if this setting is not configured.
>
> **Archive ingestion:** When you intentionally whitelist archive extensions (for example `.zip` or `.tar`), the indexer now enforces a 50 MB per-archive size ceiling and skips anything larger to reduce the risk of decompression bombs. Only enable archive processing when inputs come from trusted sources, otherwise prefer extracting the content manually and feeding the extracted documents to Help Chat.

> **Note on `enable_debug_log`:** When set to `true`, creates a `program_debug.log` file inside the configured temp directory with timestamped debug messages, including per-file skip reasons. The log is cleared at startup. Keep disabled (default) in production for better performance.

> **Ollama note:** Point `api_path` to `http://localhost:11434/v1` to use its OpenAI-compatible API.

## Deployment

Publish the package to PyPI (or an internal index) with `build` + `twine`:

1. **Version bump**
   - Update the `version` field in `help-chat-python/pyproject.toml`.
   - Commit the change with a changelog entry if applicable.
2. **Build artifacts**
   ```bash
   cd help-chat-python
   python -m build
   ```
3. **Verify and upload**
   ```bash
   python -m twine check dist/*
   python -m twine upload dist/*
   ```
   Use `--repository-url` for private indexes.
4. **Post-publish smoke test**
   ```bash
   python -m venv /tmp/help-chat-verify
   source /tmp/help-chat-verify/bin/activate
   pip install help-chat-python==<new-version>
   python -c "import help_chat; print(help_chat.__version__)"
   ```

> **Tip**: Run `pytest`, `flake8`, `mypy`, and `python -m build` in CI before tagging a release to guarantee repeatable wheels.

## Quick Start

```python
import json
from help_chat.keyring import KeyRing
from help_chat.doc_indexer import DocIndexer
from help_chat.llm import HelpChat

# Step 1: Configure
config = KeyRing.build(json.dumps({
    "name": "My Project",            # Optional: config name for identification
    "root_path": "/path/to/docs",
    "temp_path": "/tmp/help-chat",
    "api_path": "https://api.openai.com/v1",
    "api_key": "your-api-key",
    "embeddings_path": "/path/to/embeddings.db",
    "model_name": "",                # Optional: empty for auto-detect (defaults to gpt-4o for OpenAI)
    "conversion_timeout": 5,         # Optional: timeout for file conversion (seconds)
    "supported_extensions": ".pdf,.docx,.pptx,.xlsx,.md,.txt",  # Required: file types to index
    "enable_debug_log": false,       # Optional: enable debug logging to program_debug.log (in temp_path)
    "context_documents": 5,          # Optional: number of RAG documents for context
    "max_tokens": 2000,              # Optional: max response length
    "temperature": 0.7,              # Optional: LLM creativity (0.0-2.0)
    "top_p": 0.9,                    # Optional: token sampling diversity
    "timeout": 60.0                  # Optional: LLM request timeout (seconds)
}))

# Step 2: Index documents
indexer = DocIndexer()
indexer.reindex(config)

# Step 3: Ask questions
chat = HelpChat(config)
response = chat.make_request("How do I configure the system?")
print(response)
```

## Module Documentation

### KeyRing Module

Configuration management with validation.

```python
from help_chat.keyring import KeyRing
import json

config = KeyRing.build(json.dumps({
    "name": "My Config",                    # Optional: Configuration name
    "root_path": "/path/to/docs",           # Required: Document directory
    "temp_path": "/tmp/help-chat",          # Required: Temporary processing directory
    "api_path": "https://api.openai.com/v1", # Required: LLM API endpoint
    "embeddings_path": "/path/to/embeddings.db", # Required: SQLite database path
    "api_key": "your-api-key",              # Optional: API key (empty for local LLMs)
    "model_name": "",                       # Optional: Model name (empty for auto-detect to gpt-4o)
    "conversion_timeout": 5,                # Optional: File conversion timeout (seconds)
    "supported_extensions": ".pdf,.docx,.pptx,.xlsx,.md,.txt",  # Required: file types to index
    "enable_debug_log": false,              # Optional: enable debug logging to program_debug.log (in temp_path)
    "context_documents": 5,                 # Optional: RAG context documents
    "max_tokens": 2000,                     # Optional: Max response length
    "temperature": 0.7,                     # Optional: LLM creativity
    "top_p": 0.9,                           # Optional: Sampling diversity
    "timeout": 60.0                         # Optional: Request timeout
}))
```

**Required Fields**: `root_path`, `temp_path`, `api_path`, `embeddings_path`, `supported_extensions`
**Optional Fields**: `name`, `api_key`, `model_name`, `conversion_timeout`, `enable_debug_log`, `context_documents`, `max_tokens`, `temperature`, `top_p`, `timeout`

### DocIndexer Module

Document indexing with vector embeddings.

```python
from help_chat.doc_indexer import DocIndexer

indexer = DocIndexer()

# Using config dictionary
indexer.reindex(config)

# Or using individual parameters
indexer.reindex(
    root_path="/path/to/docs",
    temp_path="/tmp/help-chat",
    embeddings_path="/path/to/embeddings.db",
    conversion_timeout=5,  # Optional: timeout in seconds
    supported_extensions=".pdf,.docx,.txt"  # Required: file types to index
)

# With progress callback
def on_progress(file_path: str) -> None:
    print(f"Processing: {file_path}")

indexer.reindex(config, progress_callback=on_progress)
```

**Features**:
- Recursively scans document directory
- Converts documents to markdown using Markitdown
- Configurable timeout prevents hanging on problematic files
- Gracefully handles unsupported file types and conversion errors (logs warnings, skips files)
- Generates vector embeddings using sentence-transformers
- Stores embeddings in SQLite with SHA256 file hashes
- Incremental updates (only processes changed files)
- Progress callback support (fires only when files need processing)
- Removes deleted files from database

### LLM Module

Question answering with Retrieval Augmented Generation (RAG).

```python
from help_chat.llm import HelpChat

# Using config dictionary
chat = HelpChat(config)

# Or using individual parameters
chat = HelpChat(
    api_path="https://api.openai.com/v1",
    api_key="your-api-key",
    embeddings_path="/path/to/embeddings.db",
    model_name="gpt-4o"  # Optional
)

# Make requests
response = chat.make_request("What are the system requirements?")
print(response)
```

**Features**:
- Retrieves relevant document chunks using vector similarity
- Augments prompts with contextual information
- Supports multiple LLM providers
- Configurable or auto-detected model names

## Supported LLM Providers

The package supports any OpenAI-compatible API provider.

### OpenAI
```python
config = {
    "name": "OpenAI Docs",
    "root_path": "/path/to/docs",
    "temp_path": "/tmp/help-chat",
    "embeddings_path": "/path/to/embeddings.db",
    "api_path": "https://api.openai.com/v1",
    "api_key": "sk-your-openai-key",
    "model_name": "",  # Auto-detects to gpt-4o
    "conversion_timeout": 5,
    "supported_extensions": ".pdf,.docx,.pptx,.xlsx,.md,.txt",
    "enable_debug_log": false,
    "context_documents": 5,
    "max_tokens": 2000,
    "temperature": 0.7,
    "top_p": 0.9,
    "timeout": 60.0
}
```

### DeepSeek
```python
config = {
    "name": "DeepSeek Docs",
    "root_path": "/path/to/docs",
    "temp_path": "/tmp/help-chat",
    "embeddings_path": "/path/to/embeddings.db",
    "api_path": "https://api.deepseek.com",
    "api_key": "your-deepseek-key",
    "model_name": "deepseek-chat",  # or "deepseek-coder"
    "conversion_timeout": 5,
    "supported_extensions": ".pdf,.docx,.pptx,.xlsx,.md,.txt",
    "enable_debug_log": false,
    "context_documents": 5,
    "max_tokens": 2000,
    "temperature": 0.7,
    "top_p": 0.9,
    "timeout": 60.0
}
```

### Ollama (Local)
```python
config = {
    "name": "Ollama Local",
    "root_path": "/path/to/docs",
    "temp_path": "/tmp/help-chat",
    "embeddings_path": "/path/to/embeddings.db",
    "api_path": "http://localhost:11434/v1",
    "api_key": "",
    "model_name": "llama3.2",
    "conversion_timeout": 5,
    "supported_extensions": ".pdf,.docx,.pptx,.xlsx,.md,.txt",
    "enable_debug_log": false,
    "context_documents": 3,
    "max_tokens": 1500,
    "temperature": 0.8,
    "top_p": 0.9,
    "timeout": 120.0  # Local models may be slower
}
```

### LM Studio (Local)
```python
config = {
    "name": "LM Studio Local",
    "root_path": "/path/to/docs",
    "temp_path": "/tmp/help-chat",
    "embeddings_path": "/path/to/embeddings.db",
    "api_path": "http://localhost:1234/v1",
    "api_key": "",
    "model_name": "",  # Uses loaded model
    "conversion_timeout": 5,
    "supported_extensions": ".pdf,.docx,.pptx,.xlsx,.md,.txt",
    "enable_debug_log": false,
    "context_documents": 3,
    "max_tokens": 1500,
    "temperature": 0.8,
    "top_p": 0.9,
    "timeout": 120.0  # Local models may be slower
}
```

**Note**: If `model_name` is empty, the system auto-detects based on `api_path`.

## Development

### Running Tests
```bash
pytest
```

### Code Coverage
```bash
pytest --cov=help_chat --cov-report=html
```

Current coverage: **91%** (39 tests)

### Code Formatting
```bash
black src/ tests/
```

### Linting
```bash
flake8 src/ tests/
```

### Type Checking
```bash
mypy src/
```

## Dependencies

All dependencies are free for commercial use:

- **markitdown** (MIT) - Document conversion
- **sentence-transformers** (Apache 2.0) - Vector embeddings
- **openai** (MIT) - LLM API client
- **numpy** (BSD) - Array operations
- **scikit-learn** (BSD) - Similarity calculations

## Project Structure

```
help-chat-python/
├── src/
│   └── help_chat/
│       ├── __init__.py
│       ├── keyring.py      # Configuration management
│       ├── doc_indexer.py  # Document indexing & embeddings
│       └── llm.py          # LLM integration with RAG
├── tests/
│   ├── test_keyring.py
│   ├── test_doc_indexer.py
│   └── test_llm.py
├── pyproject.toml
└── README.md
```

## License

MIT License - Free for commercial use

## See Also

- **Main Documentation**: See [repository root README](../../README.md) for full system documentation
- **.NET Wrapper**: See [HelpChat.Lib](../help-chat-dotnet/README.md) for C# integration
- **Requirements**: See [help-chat-python.md](help-chat-python.md) for detailed requirements
