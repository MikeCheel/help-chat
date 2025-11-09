# Help Chat Python - Requirements Document

## Overview

The help-chat-python package provides document indexing, vector embeddings, and LLM-based question answering with Retrieval Augmented Generation (RAG) support. It enables developers to build intelligent help systems that answer questions based on document collections.

## Package Information

- **Package Name**: help-chat-python
- **Directory**: `help-chat-python`
- **Python Version**: 3.10 or higher
- **License**: MIT (free for commercial use)

## Architecture

The package consists of three core modules:

1. **KeyRing** - Configuration management
2. **DocIndexer** - Document indexing and vector embeddings
3. **LLM** - Language model integration with RAG

---

## Module 1: KeyRing

### Purpose

Provides configuration management for the help-chat system, validating and structuring configuration data for use by other modules.

### Module Location

`src/help_chat/keyring.py`

### Class: KeyRing

#### Static Method: build

**Signature**:
```python
@staticmethod
def build(json_string: str) -> Dict[str, str]:
```

**Purpose**: Parse and validate configuration from JSON string, returning a typed dictionary for use by DocIndexer and LLM modules.

**Parameters**:
- `json_string` (str): JSON-formatted configuration string

**JSON Format**:
```json
{
  "root_path": "/path/to/documents",
  "temp_path": "/path/to/temp",
  "api_path": "https://api.openai.com/v1",
  "embeddings_path": "/path/to/embeddings.db",
  "api_key": "optional-api-key"
}
```

**Required Fields**:
- `root_path` (str): Directory containing documents to index
- `temp_path` (str): Temporary directory for document processing
- `api_path` (str): LLM API endpoint URL
- `embeddings_path` (str): Path to SQLite embeddings database file

**Optional Fields**:
- `api_key` (str): API key for LLM provider
  - Defaults to empty string if not provided
  - Required for OpenAI
  - Optional for local providers (Ollama, LM Studio)

**Return Value**:
```python
{
    "root_path": str,
    "temp_path": str,
    "api_path": str,
    "embeddings_path": str,
    "api_key": str  # Empty string if not provided
}
```

**Error Handling**:
- Raise `ValueError` if JSON is malformed
- Raise `ValueError` if any required field is missing
- Raise `ValueError` if field types are incorrect (must be strings)

**Validation Rules**:
1. All required fields must be present
2. All values must be strings (no null/None values for required fields)
3. Empty strings are valid for paths (validation happens in DocIndexer/LLM)
4. api_key defaults to "" if not present or null

**Example Usage**:
```python
from help_chat.keyring import KeyRing
import json

config_json = json.dumps({
    "root_path": "/home/user/docs",
    "temp_path": "/tmp/help-chat",
    "api_path": "https://api.openai.com/v1",
    "embeddings_path": "/var/lib/help-chat/embeddings.db",
    "api_key": "sk-your-key-here"
})

config = KeyRing.build(config_json)
# Returns: Dictionary with all fields as strings
```

---

## Module 2: DocIndexer

### Purpose

Handles document discovery, conversion to markdown, vector embedding generation, and storage in a SQLite database. Tracks file changes using SHA256 hashing to enable incremental updates.

### Module Location

`src/help_chat/doc_indexer.py`

### Class: DocIndexer

#### Method: reindex

**Signature**:
```python
def reindex(
    self,
    config: Optional[Dict[str, str]] = None,
    root_path: Optional[str] = None,
    temp_path: Optional[str] = None,
    embeddings_path: Optional[str] = None
) -> None:
```

**Purpose**: Scan, convert, embed, and index all supported documents from the root directory.

**Parameters** (two usage patterns):

**Pattern 1 - Using Config Dictionary**:
- `config` (Dict[str, str]): Configuration dictionary from KeyRing.build()
  - Must contain: root_path, temp_path, embeddings_path

**Pattern 2 - Using Individual Parameters**:
- `root_path` (str): Directory containing documents to index
- `temp_path` (str): Temporary directory for processing
- `embeddings_path` (str): Path to SQLite database file

**Note**: Either provide `config` OR the three individual parameters. If `config` is provided, individual parameters are ignored.

---

### Reindexing Workflow

#### Step 1: Validate Root Path

**Requirements**:
- Verify `root_path` directory exists
- Raise `FileNotFoundError` if directory doesn't exist
- Raise `ValueError` if root_path is not a directory

**Error Messages**:
- `"Root path '{root_path}' does not exist"`
- `"Root path '{root_path}' is not a directory"`

---

#### Step 2: Prepare Temporary Directory

**Requirements**:
- Check if `temp_path` directory exists
- Create directory if it doesn't exist (including parent directories)
- Ensure directory is empty before processing
  - Delete all files and subdirectories within temp_path
  - Keep the temp_path directory itself

**Behavior**:
```python
if not os.path.exists(temp_path):
    os.makedirs(temp_path, exist_ok=True)
else:
    # Empty the directory
    for item in os.listdir(temp_path):
        item_path = os.path.join(temp_path, item)
        if os.path.isfile(item_path):
            os.remove(item_path)
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)
```

**Error Handling**:
- Handle permission errors gracefully
- Provide clear error messages for I/O failures

---

#### Step 3: Initialize Embeddings Database

**Database**: SQLite database at `embeddings_path`

**Requirements**:
1. Create parent directories if they don't exist
2. Create database file if it doesn't exist
3. Create schema if tables don't exist

**Database Schema**:
```sql
CREATE TABLE IF NOT EXISTS embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,
    file_hash TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding BLOB NOT NULL,
    last_modified REAL NOT NULL
)
```

**Field Descriptions**:
- `id`: Auto-incrementing primary key
- `file_path`: Relative path from root_path to document (unique)
- `file_hash`: SHA256 hash of file contents (hex string)
- `content`: Markdown-converted document content
- `embedding`: Vector embedding as binary blob (numpy array)
- `last_modified`: File modification timestamp (Unix epoch)

**Index Creation** (for performance):
```sql
CREATE INDEX IF NOT EXISTS idx_file_path ON embeddings(file_path);
CREATE INDEX IF NOT EXISTS idx_file_hash ON embeddings(file_hash);
```

---

#### Step 4: Build File List with Hashes

**Requirements**:
1. Recursively scan `root_path` and all subdirectories
2. Identify files supported by Markitdown library
3. Calculate SHA256 hash for each file
4. Build list of tuples: `(relative_path, file_hash, absolute_path, mtime)`

**Supported File Types** (via Markitdown):
- **Documents**: .pdf, .docx, .doc, .pptx, .ppt, .xlsx, .xls
- **Text**: .txt, .md, .markdown
- **Web**: .html, .htm
- **Code**: .py, .js, .java, .c, .cpp, .cs, .go, .rs, etc.
- **Images**: .jpg, .jpeg, .png (with OCR if available)
- **Other**: Various formats supported by Markitdown

**File Path Handling**:
- Store relative paths from root_path (for portability)
- Use forward slashes (/) in database (cross-platform compatibility)
- Handle Windows and Unix path separators

**SHA256 Hash Calculation**:
```python
def calculate_hash(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()
```

**Error Handling**:
- Skip files that can't be read (permissions, corruption)
- Log warnings for skipped files
- Continue processing remaining files

---

#### Step 5: Remove Deleted Files from Database

**Purpose**: Clean up database records for files that no longer exist.

**Algorithm**:
1. Query all file_path values from database
2. Compare against current file list
3. Delete records where file no longer exists

**SQL Query**:
```sql
DELETE FROM embeddings WHERE file_path NOT IN (?, ?, ?, ...)
```

**Optimization**: Use parameterized query with list of current file paths.

---

#### Step 6: Process Each File

For each file in the file list:

**6a. Check if Record Exists**:
```sql
SELECT id, file_hash FROM embeddings WHERE file_path = ?
```

**6b. Determine Action**:
- **File Not in Database**: Process and insert new record
- **File Hash Changed**: Process and update existing record
- **File Hash Unchanged**: Skip (no changes)

**6c. Process File** (if needed):

1. **Convert to Markdown**:
   ```python
   from markitdown import MarkItDown

   md = MarkItDown()
   result = md.convert(file_path)
   markdown_content = result.text_content
   ```

2. **Generate Vector Embedding**:
   ```python
   from sentence_transformers import SentenceTransformer

   model = SentenceTransformer('all-MiniLM-L6-v2')
   embedding = model.encode(markdown_content)
   # embedding is numpy array of shape (384,)
   ```

3. **Store Embedding**:
   ```python
   import numpy as np

   embedding_blob = embedding.tobytes()
   # Store as BLOB in SQLite
   ```

**6d. Database Operations**:

**Insert New Record**:
```sql
INSERT INTO embeddings (file_path, file_hash, content, embedding, last_modified)
VALUES (?, ?, ?, ?, ?)
```

**Update Existing Record**:
```sql
UPDATE embeddings
SET file_hash = ?, content = ?, embedding = ?, last_modified = ?
WHERE file_path = ?
```

**6e. Performance Considerations**:
- Use transaction for batch operations
- Commit after processing all files
- Consider progress callbacks for large document sets (future enhancement)

---

### Error Handling

**File Processing Errors**:
- Skip individual files that fail conversion
- Log error with file path and exception
- Continue processing remaining files
- Raise `RuntimeError` if entire operation fails

**Database Errors**:
- Rollback transaction on error
- Raise `RuntimeError` with descriptive message
- Ensure database is not left in inconsistent state

**Embedding Errors**:
- Retry with exponential backoff for transient failures
- Raise `RuntimeError` if embedding model fails to load
- Skip files that produce invalid embeddings

---

### Dependencies

**Required Libraries**:
- `markitdown`: Document conversion
- `sentence-transformers`: Vector embeddings (all-MiniLM-L6-v2 model)
- `sqlite3`: Database storage (Python standard library)
- `numpy`: Array operations
- `hashlib`: SHA256 hashing (Python standard library)

**Model Download**:
- On first run, sentence-transformers downloads all-MiniLM-L6-v2 model (~80MB)
- Model cached in ~/.cache/torch/sentence_transformers/

---

### Example Usage

```python
from help_chat.doc_indexer import DocIndexer
from help_chat.keyring import KeyRing
import json

# Using config dictionary
config = KeyRing.build(json.dumps({
    "root_path": "/home/user/docs",
    "temp_path": "/tmp/help-chat",
    "api_path": "https://api.openai.com/v1",
    "embeddings_path": "/var/lib/help-chat/embeddings.db",
    "api_key": "sk-key"
}))

indexer = DocIndexer()
indexer.reindex(config)

# Or using individual parameters
indexer.reindex(
    root_path="/home/user/docs",
    temp_path="/tmp/help-chat",
    embeddings_path="/var/lib/help-chat/embeddings.db"
)
```

---

## Module 3: LLM

### Purpose

Integrates with Large Language Models (OpenAI, Ollama, LM Studio) using Retrieval Augmented Generation (RAG) to provide context-aware answers based on indexed documents.

### Module Location

`src/help_chat/llm.py`

### Class: HelpChat

#### Constructor

**Signature**:
```python
def __init__(
    self,
    config: Optional[Dict[str, str]] = None,
    api_path: Optional[str] = None,
    api_key: Optional[str] = None,
    embeddings_path: Optional[str] = None
):
```

**Purpose**: Initialize the LLM integration with configuration.

**Parameters** (two usage patterns):

**Pattern 1 - Using Config Dictionary**:
- `config` (Dict[str, str]): Configuration dictionary from KeyRing.build()
  - Must contain: api_path, api_key, embeddings_path

**Pattern 2 - Using Individual Parameters**:
- `api_path` (str): LLM API endpoint URL
- `api_key` (str): API key for authentication (empty for local providers)
- `embeddings_path` (str): Path to SQLite embeddings database

**Note**: Either provide `config` OR the three individual parameters.

**Initialization Tasks**:
1. Store configuration
2. Load sentence-transformers model (same as DocIndexer: all-MiniLM-L6-v2)
3. Verify embeddings database exists
4. Initialize OpenAI client with provided api_path and api_key

**Error Handling**:
- Raise `FileNotFoundError` if embeddings database doesn't exist
- Raise `RuntimeError` if embedding model fails to load
- Raise `ValueError` if required configuration is missing

---

#### Method: make_request

**Signature**:
```python
def make_request(self, prompt: str) -> str:
```

**Purpose**: Answer user questions using RAG (Retrieval Augmented Generation) by retrieving relevant document context and querying the LLM.

**Parameters**:
- `prompt` (str): User's question or request

**Return Value**:
- `str`: LLM's response text

---

### RAG Workflow

#### Step 1: Generate Query Embedding

**Purpose**: Convert user's prompt into vector embedding for similarity search.

**Implementation**:
```python
query_embedding = self.model.encode(prompt)
# Returns numpy array of shape (384,)
```

---

#### Step 2: Retrieve Relevant Context

**Purpose**: Find the most relevant document chunks based on cosine similarity.

**Algorithm**:
1. Load all embeddings from database
2. Calculate cosine similarity between query and each document
3. Sort by similarity score (descending)
4. Return top N most relevant documents (default: top 5)

**SQL Query**:
```sql
SELECT file_path, content, embedding FROM embeddings
```

**Similarity Calculation**:
```python
from sklearn.metrics.pairwise import cosine_similarity

# Compare query_embedding with all document embeddings
similarities = []
for row in database_results:
    doc_embedding = np.frombuffer(row['embedding'], dtype=np.float32)
    similarity = cosine_similarity(
        query_embedding.reshape(1, -1),
        doc_embedding.reshape(1, -1)
    )[0][0]
    similarities.append((similarity, row['file_path'], row['content']))

# Sort by similarity and take top 5
top_contexts = sorted(similarities, reverse=True)[:5]
```

**Context Size Considerations**:
- Limit total context to ~4000 tokens (rough estimate: 16000 characters)
- Truncate individual documents if too long
- Prioritize highest-similarity documents

---

#### Step 3: Augment Prompt with Context

**Purpose**: Construct enhanced prompt with relevant document context.

**Prompt Template**:
```
Context from your documentation:

---
File: {file_path_1}
{content_1}

---
File: {file_path_2}
{content_2}

---
File: {file_path_3}
{content_3}

---

Based on the above context, please answer the following question:

{user_prompt}
```

**Requirements**:
- Include file paths for attribution
- Separate documents with clear delimiters (---)
- Place user's original question at the end
- Keep total prompt under LLM's context limit

---

#### Step 4: Detect LLM Provider

**Purpose**: Auto-detect LLM provider based on api_path and configure accordingly.

**Provider Detection**:
```python
def _detect_provider(self, api_path: str) -> str:
    if "openai.com" in api_path.lower():
        return "openai"
    elif "11434" in api_path:  # Default Ollama port
        return "ollama"
    elif "1234" in api_path:   # Default LM Studio port
        return "lmstudio"
    else:
        # Assume OpenAI-compatible API
        return "openai-compatible"
```

---

#### Step 5: Determine Model Name

**Purpose**: Select appropriate model based on provider.

**Model Selection**:
```python
def _get_model_name(self, provider: str) -> str:
    if provider == "openai":
        return "gpt-4-turbo-preview"  # or configurable default
    elif provider == "ollama":
        return "llama2"  # or query Ollama for available models
    elif provider == "lmstudio":
        return "local-model"  # LM Studio uses whatever model is loaded
    else:
        return "gpt-3.5-turbo"  # Generic default
```

**Note**: Future enhancement: Allow model name configuration.

---

#### Step 6: Make LLM API Request

**Purpose**: Send augmented prompt to LLM and retrieve response.

**Implementation** (using OpenAI client for all providers):
```python
from openai import OpenAI

client = OpenAI(
    base_url=self.api_path,
    api_key=self.api_key
)

response = client.chat.completions.create(
    model=model_name,
    messages=[
        {
            "role": "system",
            "content": "You are a helpful assistant that answers questions based on provided documentation."
        },
        {
            "role": "user",
            "content": augmented_prompt
        }
    ],
    temperature=0.7,
    max_tokens=1000
)

return response.choices[0].message.content
```

**Why Use OpenAI Client for All Providers**:
- Ollama and LM Studio implement OpenAI-compatible APIs
- Single code path for all providers
- Simplified maintenance and testing

---

### Error Handling

**Database Errors**:
- Raise `RuntimeError` if embeddings database is inaccessible
- Raise `RuntimeError` if no embeddings found (suggest running reindex)

**API Request Errors**:
- Raise `RuntimeError` for network failures
- Raise `RuntimeError` for authentication failures
- Raise `RuntimeError` for API quota/rate limit errors
- Include original error message in exception

**Embedding Errors**:
- Raise `RuntimeError` if query embedding fails
- Handle model loading failures gracefully

**Response Parsing Errors**:
- Handle missing or malformed API responses
- Provide default error message if response is empty

---

### LLM Provider Configuration

#### OpenAI

**Configuration**:
```json
{
  "api_path": "https://api.openai.com/v1",
  "api_key": "sk-your-openai-api-key"
}
```

**Requirements**:
- Valid OpenAI API key
- Internet connection
- API usage billing enabled

---

#### Ollama (Local)

**Configuration**:
```json
{
  "api_path": "http://localhost:11434",
  "api_key": ""
}
```

**Requirements**:
- Ollama installed and running locally
- At least one model pulled (e.g., `ollama pull llama2`)
- Default port 11434 (configurable)

**Installation**:
```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama2

# Start server (runs automatically on install)
ollama serve
```

---

#### LM Studio (Local)

**Configuration**:
```json
{
  "api_path": "http://localhost:1234/v1",
  "api_key": ""
}
```

**Requirements**:
- LM Studio installed and running
- Model loaded in LM Studio
- Local server enabled in LM Studio settings
- Default port 1234 (configurable)

**Setup**:
1. Download and install LM Studio
2. Download a model (e.g., Llama 2, Mistral)
3. Load model in LM Studio
4. Enable "Local Server" in settings
5. Note the port (default 1234)

---

### Example Usage

```python
from help_chat.llm import HelpChat
from help_chat.keyring import KeyRing
import json

# Using config dictionary
config = KeyRing.build(json.dumps({
    "root_path": "/home/user/docs",
    "temp_path": "/tmp/help-chat",
    "api_path": "https://api.openai.com/v1",
    "embeddings_path": "/var/lib/help-chat/embeddings.db",
    "api_key": "sk-your-key"
}))

chat = HelpChat(config)
response = chat.make_request("How do I configure the API key?")
print(response)

# Or using individual parameters (Ollama example)
chat = HelpChat(
    api_path="http://localhost:11434",
    api_key="",
    embeddings_path="/var/lib/help-chat/embeddings.db"
)

response = chat.make_request("What file formats are supported?")
print(response)
```

---

## Testing Requirements

### Test Framework

- **Framework**: pytest
- **Coverage**: pytest-cov
- **Target**: Minimum 70% code coverage (target 90%+)

### Test Organization

**Directory**: `tests/`

**Test Files**:
- `tests/test_keyring.py` - KeyRing module tests (6 tests)
- `tests/test_doc_indexer.py` - DocIndexer module tests (12 tests)
- `tests/test_llm.py` - LLM module tests (16 tests)

### Test Categories

#### 1. KeyRing Tests (6 tests)

- Valid JSON configuration parsing
- Missing required fields
- Invalid JSON format
- Optional api_key handling (defaults to "")
- Type validation (all fields must be strings)
- Empty string handling

#### 2. DocIndexer Tests (12 tests)

- Root path validation (exists, is directory)
- Temp path creation and cleanup
- Database creation and schema
- File discovery (recursive scanning)
- SHA256 hash calculation
- Markitdown conversion
- Vector embedding generation
- Database insert operations
- Database update operations (hash change detection)
- Deletion of missing files
- Config dictionary usage
- Individual parameter usage

#### 3. LLM Tests (16 tests)

- Constructor with config dictionary
- Constructor with individual parameters
- Embeddings database validation
- Query embedding generation
- Context retrieval (top-N selection)
- Cosine similarity calculation
- Prompt augmentation
- Provider detection (OpenAI, Ollama, LM Studio)
- Model name selection
- API request formatting
- Response parsing
- Error handling (network, auth, API errors)
- Empty database handling
- Invalid prompt handling
- Long context handling (truncation)
- Integration test with mock LLM

### Test Coverage Goals

**Total Tests**: 34 tests
**Overall Coverage**: 90%

**Module Coverage**:
- KeyRing: 100% (simple module, full coverage achievable)
- DocIndexer: 92% (some error paths difficult to test)
- LLM: 85% (network/API mocking complexity)

---

## Development Requirements

### Code Quality

1. **Type Hints**
   - All function signatures must include type hints
   - Use `Optional[]` for optional parameters
   - Use `Dict[str, str]` for config dictionaries

2. **Docstrings**
   - All public classes and methods must have docstrings
   - Use Google-style docstring format
   - Include parameter descriptions and return values

3. **Code Formatting**
   - Use `black` for code formatting
   - Line length: 100 characters (black default)
   - Run: `black src/ tests/`

4. **Linting**
   - Use `flake8` for linting
   - Allow SQL string literals >100 characters
   - Zero critical issues required

5. **Type Checking**
   - Use `mypy` for static type checking
   - Zero type errors required
   - Run: `mypy src/`

### Package Configuration

**File**: `pyproject.toml`

**Required Sections**:
```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "help-chat-python"
version = "0.1.0"
description = "Document indexing and LLM chat with RAG support"
requires-python = ">=3.10"
dependencies = [
    "markitdown>=0.1.0",
    "sentence-transformers>=2.0.0",
    "openai>=1.0.0",
    "numpy>=1.24.0",
    "scikit-learn>=1.3.0"
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "flake8>=6.0.0",
    "mypy>=1.0.0"
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=help_chat --cov-report=html --cov-report=term"

[tool.black]
line-length = 100

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
```

---

## Dependencies

### Production Dependencies

1. **markitdown** (>=0.1.0)
   - License: MIT
   - Purpose: Convert various document formats to markdown
   - Free for commercial use: ✅

2. **sentence-transformers** (>=2.0.0)
   - License: Apache 2.0
   - Purpose: Generate vector embeddings
   - Model: all-MiniLM-L6-v2
   - Free for commercial use: ✅

3. **openai** (>=1.0.0)
   - License: MIT
   - Purpose: LLM API client (works with OpenAI, Ollama, LM Studio)
   - Free for commercial use: ✅

4. **numpy** (>=1.24.0)
   - License: BSD
   - Purpose: Array operations for embeddings
   - Free for commercial use: ✅

5. **scikit-learn** (>=1.3.0)
   - License: BSD
   - Purpose: Cosine similarity calculations
   - Free for commercial use: ✅

### Development Dependencies

1. **pytest** (>=7.0.0) - Testing framework
2. **pytest-cov** (>=4.0.0) - Coverage reporting
3. **black** (>=23.0.0) - Code formatting
4. **flake8** (>=6.0.0) - Linting
5. **mypy** (>=1.0.0) - Type checking

All dependencies are free for commercial use.

---

## Installation

### For Development

```bash
cd help-chat-python
pip install -e ".[dev]"
```

This installs the package in editable mode with all development dependencies.

### For Production

```bash
cd help-chat-python
pip install .
```

This installs only production dependencies.

---

## Usage Examples

### Complete Workflow

```python
from help_chat.keyring import KeyRing
from help_chat.doc_indexer import DocIndexer
from help_chat.llm import HelpChat
import json

# Step 1: Build configuration
config_json = json.dumps({
    "root_path": "/home/user/documentation",
    "temp_path": "/tmp/help-chat-processing",
    "api_path": "https://api.openai.com/v1",
    "embeddings_path": "/var/lib/help-chat/embeddings.db",
    "api_key": "sk-your-openai-key"
})

config = KeyRing.build(config_json)

# Step 2: Index documents
indexer = DocIndexer()
indexer.reindex(config)

# Step 3: Ask questions
chat = HelpChat(config)
response = chat.make_request("How do I install the package?")
print(response)

# Step 4: Reindex after document changes
indexer.reindex(config)  # Only changed files are reprocessed
```

### Using Individual Parameters

```python
from help_chat.doc_indexer import DocIndexer
from help_chat.llm import HelpChat

# Index documents
indexer = DocIndexer()
indexer.reindex(
    root_path="/docs",
    temp_path="/tmp/help-chat",
    embeddings_path="/var/lib/embeddings.db"
)

# Ask questions using Ollama (local)
chat = HelpChat(
    api_path="http://localhost:11434",
    api_key="",
    embeddings_path="/var/lib/embeddings.db"
)

response = chat.make_request("What are the system requirements?")
print(response)
```

---

## Success Criteria

- ✅ All 34 tests pass
- ✅ 90% code coverage achieved
- ✅ Zero type errors (mypy)
- ✅ Zero critical lint errors (flake8)
- ✅ Code formatted with black
- ✅ All dependencies free for commercial use
- ✅ Package installable with pip
- ✅ Works with OpenAI, Ollama, and LM Studio
- ✅ Handles file changes incrementally (hash-based)
- ✅ Documentation complete and accurate

---

## License

MIT License - Free for commercial use
