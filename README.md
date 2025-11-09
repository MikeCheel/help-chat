# Help Chat

Help Chat lets you turn a folder of documents into a RAG-powered assistant. There are three pieces:

- `help-chat-python/` – Python package that indexes docs and talks to LLMs.
- `help-chat-dotnet/HelpChat.Lib` – .NET wrapper around the Python package.
- `help-chat-dotnet/HelpChat.Console` – CLI demo that uses the wrapper.

---
## Prerequisites

### To Run the Application

Minimum requirements to use Help Chat:

- **Python 3.10 or higher**
  - Download: [python.org](https://www.python.org/downloads/)
  - Verify: `python --version`
  - Note: Python 3.10-3.12 recommended for best performance (native pythonnet support)
  - Python 3.13+ supported via CLI fallback
  - The .NET wrapper now checks `python`, `python3`, and versioned `python3.x` executables automatically, so Linux/macOS environments that only expose `python3` work without extra configuration
- **.NET 8.0 Runtime or higher** (needed for all .NET components: HelpChat.Lib wrapper, HelpChat.Lib.Tests, and HelpChat.Console)
  - Download: [dotnet.microsoft.com](https://dotnet.microsoft.com/download)
  - Verify: `dotnet --version`
  - Note: The Python package can be used standalone without .NET
- **LLM Provider Access** (choose one):
  - **Cloud APIs**: OpenAI, DeepSeek, or any OpenAI-compatible API endpoint
  - **Local Models**: Ollama ([ollama.com](https://ollama.com)) or LM Studio ([lmstudio.ai](https://lmstudio.ai))
  - Note: For local models, ensure the model is downloaded and server is running

### For Development

Additional requirements if you want to modify or contribute to the project:

- **.NET 8.0 SDK** (not just runtime)
- **Git** for version control
- **pytest** for Python testing (installed via `pip install -e ".[dev]"`)
- **xUnit** for .NET testing (included with .NET SDK)
- **Code editors**: VS Code, Visual Studio, PyCharm, or similar

---
## Quick Start (fastest path to a demo)
1. **Clone + open a terminal in the repo.**
2. **Install the Python package** (pick one):
   - **Recommended (per-project venv):**
   ```powershell
   cd help-chat-python
   python -m venv .venv
   .venv\Scripts\activate
   python -m pip install -e .
   deactivate
   cd ..
   ```
   - **Alternative (global/site Python):**
    ```powershell
    python -m pip install -e path\to\help-chat-python
    ```
    Use this if you want the package available to every tool that runs `python`.
   > **If you see a “installing globally” warning:** it means the venv was not active. Reactivate it (`.\.venv\Scripts\Activate.ps1`) and rerun `python -m pip install -e .`, or call the venv’s interpreter explicitly: `.\.venv\Scripts\python.exe -m pip install -e .`.
3. **Run the console (choose one of these ways to tell it which Python to use):**
   - **Option A (recommended):** set an environment variable before launch.
   - **Option B:** put the interpreter path in `help-chat-dotnet/HelpChat.Console/appsettings.json` under `HelpChat:PythonPath`.
   - **Option C:** do nothing if `python` on PATH already has the package installed.
   ```powershell
   cd help-chat-dotnet/HelpChat.Console
   $Env:HELPCHAT_PYTHON_PATH = (Resolve-Path ..\..\help-chat-python\.venv\Scripts\python.exe)  # use when following Option A
   dotnet run
   ```
   - The console displays animated spinners during all long-running operations:
     - **Library initialization**: "Initializing HelpChat library" with spinner while detecting Python and configuring
     - **Reindexing**: "Reindexing" or "Building embeddings database" with spinner before file processing starts
     - **File processing**: Shows "Processing [/] filename" with file paths for files being actively processed
     - **Thinking**: "Thinking" with spinner while waiting for LLM response
   - After each question, displays response time (e.g., "Response (took 2.34s):")
   - The temporary folder contains a `_markdown` subfolder with converted markdown for each file—handy for debugging
   - Type `/list` to see indexed documents, or `/reindex` to refresh after adding or changing files
   - Database statistics show both size and file count (e.g., "Database: 24.00 KB, Files: 5")

If you see `ModuleNotFoundError: help_chat`, the console is still using a Python without the package—rerun step 3 and pick one of the options above (env var, appsettings, or install the package into the global interpreter).

### Configuration Settings (appsettings or JSON)

| Setting | Required | Description | Default |
| --- | --- | --- | --- |
| `Name` / `name` | Optional | Configuration name for user identification. | `""` |
| `RootPath` / `root_path` | Yes | Directory that will be recursively indexed for documents. | n/a |
| `TempPath` / `temp_path` | Yes | Working directory used for intermediate files and the `_markdown` cache. Must be dedicated to Help Chat. | n/a |
| `EmbeddingsPath` / `embeddings_path` | Yes | Full path to the SQLite embeddings database. File is created if missing. | n/a |
| `ApiPath` / `api_path` | Yes | Base URL for the LLM provider (OpenAI, DeepSeek, Ollama, LM Studio, etc.). | n/a |
| `ApiKey` / `api_key` | Optional | API key for providers that require authentication. Set to an empty string when not needed. | `""` |
| `ModelName` / `model_name` | Optional | Explicit model identifier. Leave blank to auto-detect (`gpt-4o` for OpenAI, `llama3.2` for Ollama). | `""` |
| `ConversionTimeout` / `conversion_timeout` | Optional | Timeout in seconds for file conversion. Prevents hanging on problematic files. | `5` |
| `SupportedExtensions` / `supported_extensions` | **Yes** | Comma-separated list of file extensions to index (e.g., ".pdf,.docx,.txt"). Must be explicitly configured. | n/a |
| `EmbeddingModel` / `embedding_model` | Optional | SentenceTransformer model name for embeddings. Models are cached after first download. | `"all-MiniLM-L6-v2"` |
| `EnableDebugLog` / `enable_debug_log` | Optional | Enable debug logging to `program_debug.log` inside the configured `TempPath` for troubleshooting. | `false` |
| `ContextDocuments` / `context_documents` | Optional | Number of top RAG documents to include as context. Higher = more detail but slower. | `5` |
| `MaxTokens` / `max_tokens` | Optional | Maximum tokens for LLM response. Controls response length and prevents runaway generation. | `2000` |
| `Temperature` / `temperature` | Optional | LLM temperature (0.0-2.0). Lower = more focused/deterministic, higher = more creative. | `0.7` |
| `TopP` / `top_p` | Optional | Top-p sampling parameter (0.0-1.0). Controls diversity of token selection. | `0.9` |
| `Timeout` / `timeout` | Optional | Timeout in seconds for LLM requests. Prevents hanging on slow or unresponsive endpoints. | `60.0` |
| `PythonPath` | Optional (`appsettings` only) | Absolute path to the Python interpreter the .NET console should run. Omit when using the system-wide interpreter or the `HELPCHAT_PYTHON_PATH` env var. | unset |

> **Note on `ConversionTimeout`:** This prevents the indexer from hanging indefinitely on problematic files (e.g., corrupted documents, extremely large files). Files that exceed the timeout are skipped and logged. The default of 5 seconds works well for most documents.

> **Note on `SupportedExtensions`:** **REQUIRED**. You must explicitly specify which file types to index. Extensions should be comma-separated with leading dots. Recommended value: `".pdf,.docx,.pptx,.xlsx,.md,.txt,.html,.htm,.xml,.json,.csv"`. Images (.jpg, .jpeg, .png) are also supported via EXIF metadata and OCR. Exclude archives (.zip), legacy binary formats (.doc), and audio files (.wav, .mp3) as these can cause performance issues or hanging. The application will fail if this setting is not configured.

> **Note on `EmbeddingModel`:** Specifies which SentenceTransformer model to use for generating embeddings. Common options: `"all-MiniLM-L6-v2"` (80MB, fast), `"all-mpnet-base-v2"` (420MB, better quality), `"multi-qa-mpnet-base-dot-v1"` (420MB, Q&A optimized). Models are downloaded once and cached locally. Default cache location: `~/.cache/huggingface/` (Linux/Mac) or `C:\Users\<username>\.cache\huggingface\` (Windows). To customize the cache location, set the `HF_HOME` environment variable (e.g., `HF_HOME=D:\MyModels`).
>
> **Archive ingestion:** If you intentionally include archive formats (e.g., `.zip`, `.tar`) in `SupportedExtensions`, the indexer now enforces a conservative size cap (50 MB per archive) and skips anything larger to mitigate decompression bombs. Only enable archive support when you absolutely need it and when the uploaded archives come from trusted sources.

> **Note on `EnableDebugLog`:** When set to `true`, creates a `program_debug.log` file in the configured temp directory with timestamped debug messages, including details for files that are skipped or fail conversion. The log is cleared at startup. Keep disabled (default) in production for best performance.

> **Note on LLM Parameters:** The new `MaxTokens`, `Temperature`, `TopP`, and `Timeout` settings give you fine-grained control over response quality and speed:
> - **`MaxTokens`**: Limits response length. Increase to 4000 for longer, more comprehensive answers; decrease to 1000 for quicker, more concise responses.
> - **`Temperature`**: Controls creativity/randomness. Use 0.3-0.5 for factual, deterministic answers; 0.7-0.9 for more creative or conversational responses.
> - **`TopP`**: Works with temperature to control diversity. Default 0.9 works well for most cases.
> - **`Timeout`**: Prevents requests from hanging indefinitely. Increase if using slow local models or experiencing timeouts.
> - **`ContextDocuments`**: More context = better answers but slower responses and higher API costs. Start with 5, adjust between 3-7 based on your needs.

> **Note on Model Selection:** When `ModelName` is left blank (recommended), the library auto-detects:
> - **OpenAI API** (`api.openai.com`) → defaults to `gpt-4o` (upgraded from `gpt-4o-mini` for better quality)
> - **Ollama** (`localhost:11434`) → defaults to `llama3.2`
> - **LM Studio** (`localhost:1234`) → defaults to `local-model`
> - **Other endpoints** → defaults to `gpt-4o`

> **Ollama note:** Use `http://localhost:11434/v1` as the `ApiPath` so requests hit the OpenAI-compatible endpoint.

Example `HelpChat` section in `appsettings.json`:

```json
"HelpChat": {
  "Name": "My Project Docs",
  "RootPath": "C:\\Docs\\HelpChat",
  "TempPath": "C:\\Temp\\help-chat",
  "EmbeddingsPath": "C:\\Temp\\help-chat\\embeddings.db",
  "ApiPath": "https://api.deepseek.com",
  "ApiKey": "deepseek-key",
  "ModelName": "",
  "ConversionTimeout": 5,
  "SupportedExtensions": ".pdf,.docx,.pptx,.xlsx,.md,.txt,.html,.htm,.xml,.json,.csv",
  "EnableDebugLog": false,
  "ContextDocuments": 5,
  "MaxTokens": 2000,
  "Temperature": 0.7,
  "TopP": 0.9,
  "Timeout": 60.0,
  "PythonPath": "C:\\Users\\me\\help-chat\\help-chat-python\\.venv\\Scripts\\python.exe"
}
```

### Complete Configuration Reference

Below is a comprehensive example showing **ALL** available configuration keys with inline comments. You can copy this into your .NET project's `appsettings.json` and customize as needed. Optional settings can be removed to use defaults.

```json
"HelpChat": {
  // REQUIRED: Friendly name for this configuration (displayed in console)
  "Name": "My Project Documentation",

  // REQUIRED: Root directory to scan for documents
  "RootPath": "C:\\Docs\\HelpChat",

  // REQUIRED: Temporary directory for file conversions and debug logs
  "TempPath": "C:\\Temp\\help-chat",

  // REQUIRED: Path to embeddings database file (created automatically if missing)
  "EmbeddingsPath": "C:\\Temp\\help-chat\\embeddings.db",

  // REQUIRED: API endpoint URL (OpenAI, DeepSeek, Ollama, LM Studio, etc.)
  "ApiPath": "https://api.openai.com/v1",

  // OPTIONAL: API key for authentication (default: "", can be empty for local models)
  "ApiKey": "sk-your-api-key-here",

  // OPTIONAL: LLM model name (default: "", auto-detected based on ApiPath)
  //   - Leave empty for auto-detection: gpt-4o (OpenAI), llama3.2 (Ollama), local-model (LM Studio)
  //   - Or specify explicitly: "gpt-4o", "gpt-4o-mini", "deepseek-chat", "llama3.2", etc.
  "ModelName": "",

  // OPTIONAL: File conversion timeout in seconds (default: 5)
  //   - Increase if processing large documents (e.g., 100+ page PDFs)
  "ConversionTimeout": 5,

  // REQUIRED: Comma-separated file extensions to index (must include at least one)
  //   - Recommended: ".pdf,.docx,.pptx,.xlsx,.md,.txt,.html,.htm,.xml,.json,.csv"
  //   - Images (.jpg, .jpeg, .png) supported via EXIF/OCR
  //   - Avoid: .zip, .doc (legacy), .wav, .mp3 (can cause performance issues)
  "SupportedExtensions": ".pdf,.docx,.pptx,.xlsx,.md,.txt,.html,.htm,.xml,.json,.csv",

  // OPTIONAL: Enable debug logging to program_debug.log (default: false)
  //   - Creates timestamped log in TempPath showing skipped files and conversion failures
  //   - Keep disabled in production for best performance
  "EnableDebugLog": false,

  // OPTIONAL: Number of document chunks to retrieve for RAG context (default: 5)
  //   - Range: 3-7 typical
  //   - More context = better answers but slower responses and higher API costs
  //   - Less context = faster responses but may miss relevant information
  "ContextDocuments": 5,

  // OPTIONAL: Maximum tokens in LLM response (default: 2000)
  //   - Increase to 4000 for longer, more comprehensive answers
  //   - Decrease to 1000 for quicker, more concise responses
  //   - Note: Higher values increase API costs and response time
  "MaxTokens": 2000,

  // OPTIONAL: Temperature for LLM generation, 0.0-1.0 (default: 0.7)
  //   - Lower (0.3-0.5): More factual, deterministic, focused answers
  //   - Higher (0.7-0.9): More creative, diverse, conversational answers
  "Temperature": 0.7,

  // OPTIONAL: Top-p sampling parameter, 0.0-1.0 (default: 0.9)
  //   - Controls response diversity alongside temperature
  //   - 0.9 works well for most cases; adjust only if needed
  "TopP": 0.9,

  // OPTIONAL: Request timeout in seconds (default: 60.0)
  //   - Prevents requests from hanging indefinitely
  //   - Increase if using slow local models or experiencing timeouts
  //   - Decrease for faster failure detection with fast cloud models
  "Timeout": 60.0,

  // REQUIRED (.NET only): Path to Python interpreter (use forward slashes or escaped backslashes)
  //   - Must point to Python 3.8+ with help-chat package installed
  //   - For virtual env: "C:\\path\\to\\help-chat-python\\.venv\\Scripts\\python.exe"
  //   - For system Python: "C:\\Python311\\python.exe" or "python" if in PATH
  "PythonPath": "C:\\Users\\me\\help-chat\\help-chat-python\\.venv\\Scripts\\python.exe"
}
```

> **Tip:** Start with the defaults above, then adjust `ContextDocuments`, `MaxTokens`, `Temperature`, and `Timeout` to tune the balance between response speed and quality for your specific use case.

Example JSON payload for the Python CLI or `KeyRing.build`:

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
  "supported_extensions": ".pdf,.docx,.pptx,.xlsx,.md,.txt,.html,.htm,.xml,.json,.csv",
  "enable_debug_log": false,
  "context_documents": 5,
  "max_tokens": 2000,
  "temperature": 0.7,
  "top_p": 0.9,
  "timeout": 60.0
}
```

---
## Updating an Existing Installation

If you already have Help Chat installed and want to update to the latest version:

### 1. Backup Your Data (Recommended)

Before updating, back up your important data:

```powershell
# Backup embeddings database (preserves your indexed documents)
Copy-Item "C:\Temp\help-chat\embeddings.db" "C:\Temp\help-chat\embeddings.db.backup"

# Backup saved conversations (if you've used /save command)
Copy-Item "C:\path\to\conversation_*.txt" "C:\backup\location\"
```

### 2. Update the Code

Pull the latest changes from the repository:

```powershell
git pull origin main
```

### 3. Update Dependencies

**Python package:**
```powershell
cd help-chat-python
.venv\Scripts\activate  # If using a venv
python -m pip install -e . --upgrade
deactivate
cd ..
```

**For .NET console users:**
```powershell
cd help-chat-dotnet\HelpChat.Console
dotnet restore
cd ..\..
```

### 4. Check Configuration

Review your `appsettings.json` or config files for any new settings. Compare with the [Configuration Settings](#configuration-settings-json-or-appsettings) table above. New optional settings can typically be left at their defaults.

### 5. When to Re-index

**You DON'T need to re-index if:**
- You're just updating the code (embeddings database is automatically preserved)
- Your documents haven't changed
- No new documents were added

**You SHOULD re-index if:**
- You've added new documents to your `RootPath`
- You've modified existing documents
- You want to pick up the latest indexing improvements

To re-index, either restart the console app (it runs an automatic reindex on startup) or type `/reindex` in the interactive session.

### 6. Verify the Update

Run the console application and verify:

```powershell
cd help-chat-dotnet\HelpChat.Console
dotnet run
```

Check that:
- Application starts without errors
- Database statistics show your expected file count
- You can query your documents successfully

### Implementation-Specific Update Instructions

- **Python package updates:** See [help-chat-python/README.md](help-chat-python/README.md#updating)
- **.NET library/console updates:** See [help-chat-dotnet/README.md](help-chat-dotnet/README.md#updating)

---
## When You Need More
- **Modify indexing or Python API usage?** Read `help-chat-python/README.md`.
- **Integrate with a .NET app?** See `help-chat-dotnet/README.md` for library + deployment notes.
- **Want a deeper requirements/architecture doc?** Check the `Requirements.md` file in each project folder.

---
## Example JSON Configurations
Use these snippets as starting points for `config.json` (Python CLI) or the `HelpChat` section in `appsettings.json` (console). Adjust paths, keys, and models to match your environment.

### OpenAI / Azure OpenAI
```json
{
  "name": "OpenAI Docs",
  "root_path": "C:/help-chat/docs",
  "temp_path": "C:/help-chat/temp",
  "embeddings_path": "C:/help-chat/store/embeddings.db",
  "api_path": "https://api.openai.com/v1",
  "api_key": "sk-your-openai-key",
  "model_name": "",
  "conversion_timeout": 5,
  "supported_extensions": ".pdf,.docx,.pptx,.xlsx,.md,.txt,.html,.htm,.xml,.json,.csv",
  "enable_debug_log": false,
  "context_documents": 5,
  "max_tokens": 2000,
  "temperature": 0.7,
  "top_p": 0.9,
  "timeout": 60.0
}
```

### DeepSeek Cloud
```json
{
  "name": "DeepSeek Docs",
  "root_path": "C:/help-chat/docs",
  "temp_path": "C:/help-chat/temp",
  "embeddings_path": "C:/help-chat/store/embeddings.db",
  "api_path": "https://api.deepseek.com",
  "api_key": "your-deepseek-key",
  "model_name": "deepseek-chat",
  "conversion_timeout": 5,
  "supported_extensions": ".pdf,.docx,.pptx,.xlsx,.md,.txt,.html,.htm,.xml,.json,.csv",
  "enable_debug_log": false,
  "context_documents": 5,
  "max_tokens": 2000,
  "temperature": 0.7,
  "top_p": 0.9,
  "timeout": 60.0
}
```

### Ollama (local)
```json
{
  "name": "Ollama Local",
  "root_path": "C:/help-chat/docs",
  "temp_path": "C:/help-chat/temp",
  "embeddings_path": "C:/help-chat/store/embeddings.db",
  "api_path": "http://localhost:11434/v1",
  "api_key": "",
  "model_name": "llama3.2",
  "conversion_timeout": 5,
  "supported_extensions": ".pdf,.docx,.pptx,.xlsx,.md,.txt,.html,.htm,.xml,.json,.csv",
  "enable_debug_log": false,
  "context_documents": 3,
  "max_tokens": 1500,
  "temperature": 0.8,
  "top_p": 0.9,
  "timeout": 120.0
}
```

### LM Studio (local)
```json
{
  "name": "LM Studio Local",
  "root_path": "C:/help-chat/docs",
  "temp_path": "C:/help-chat/temp",
  "embeddings_path": "C:/help-chat/store/embeddings.db",
  "api_path": "http://localhost:1234/v1",
  "api_key": "",
  "model_name": "",
  "conversion_timeout": 5,
  "supported_extensions": ".pdf,.docx,.pptx,.xlsx,.md,.txt,.html,.htm,.xml,.json,.csv",
  "enable_debug_log": false,
  "context_documents": 3,
  "max_tokens": 1500,
  "temperature": 0.8,
  "top_p": 0.9,
  "timeout": 120.0
}
```

---
## Troubleshooting in 10 seconds
| Issue | Fix |
| --- | --- |
| `ModuleNotFoundError: help_chat` | Install the package into the interpreter you’re using (venv, `HELPCHAT_PYTHON_PATH`, or global site Python). |
| Console can’t find Python | Point `HELPCHAT_PYTHON_PATH` or `HelpChat:PythonPath` at a valid interpreter, or ensure `python` on PATH has the package. |
| Need to refresh embeddings | In the console type `/reindex` (startup already does an initial run). |

### Tuning response speed and quality
- **For faster responses:** Reduce `max_tokens` to 1000-1500, lower `context_documents` to 2-3, or decrease `temperature` to 0.5.
- **For more detailed responses:** Increase `max_tokens` to 3000-4000, raise `context_documents` to 6-7, or use `temperature` 0.8-0.9.
- **For local models:** Increase `timeout` to 120+ seconds and reduce `context_documents` to avoid overwhelming slower models.
- Keep an eye on `<TempPath>\_markdown` to ensure MarkItDown is extracting the text you expect—those files are exactly what gets embedded.

That’s it. For full setup/deployment details jump into the project-specific READMEs when you’re ready.
