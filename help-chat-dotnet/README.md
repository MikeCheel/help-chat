# Help Chat .NET

A .NET wrapper for the help-chat-python package, enabling C# applications to leverage document indexing, vector embeddings, and LLM-based question answering with Retrieval Augmented Generation (RAG).

## Projects

This solution contains three projects:

- **HelpChat.Lib** - Core .NET wrapper library
- **HelpChat.Lib.Tests** - Unit and integration tests (xUnit)
- **HelpChat.Console** - Interactive console application

## Features

- **Python.NET Integration**: Seamless C#/Python interoperability
- **Type-Safe API**: Strongly-typed .NET interface over Python functionality
- **Custom Exceptions**: .NET exception hierarchy for clear error handling
- **IDisposable Pattern**: Proper resource cleanup and memory management
- **Configuration Flexibility**: JSON or individual parameters, appsettings.json support
- **Interactive Console**: Full-featured CLI with conversation history
- **Multi-Provider Support**: OpenAI, DeepSeek, Ollama, LM Studio, and any OpenAI-compatible API

## Prerequisites

### To Run the Application

Minimum requirements to use HelpChat.Console or integrate HelpChat.Lib:

- **.NET 8.0 Runtime or higher**
  - Download: [dotnet.microsoft.com](https://dotnet.microsoft.com/download)
  - Verify: `dotnet --version`
  - Note: Only runtime needed if using pre-built binaries
- **Python 3.10 or higher**
  - Download: [python.org](https://www.python.org/downloads/)
  - Verify: `python --version`
  - Recommended: Python 3.10-3.12 for native pythonnet interop (best performance)
  - Python 3.13+ supported via CLI fallback (slightly slower but fully functional)
- **help-chat-python package installed**
  - Install: `pip install -e path/to/help-chat-python`
  - Verify: `python -c "import help_chat; print('OK')"`
- **LLM Provider Access** (choose one):
  - **Cloud**: API key for OpenAI, DeepSeek, or other OpenAI-compatible service
  - **Local**: Ollama or LM Studio with model downloaded and server running

### For Development

Additional requirements to build, test, or modify the .NET wrapper:

- **.NET 8.0 SDK** (not just runtime)
  - Includes build tools, MSBuild, and testing frameworks
- **Git** for version control
- **IDE/Editor** (optional but recommended):
  - Visual Studio 2022 or later
  - Visual Studio Code with C# extension
  - JetBrains Rider
- **xUnit** for testing (included with .NET SDK)

## Requirements

- .NET 8.0 SDK or higher
- Python 3.10 – 3.12 for native pythonnet interop (recommended)
- Python 3.13+ supported via the CLI fallback (requires a usable `python` executable on PATH)
- help-chat-python package installed in the selected Python environment
- Windows, Linux, or macOS

## Development Setup

1. **Install toolchains**
   - .NET 8 SDK
   - Python 3.10+ (ensure `python`/`py` is on PATH)
2. **Bootstrap the Python package (once)**
   ```powershell
   cd ..\help-chat-python
   python -m venv .venv
   .venv\Scripts\activate
   python -m pip install -e ".[dev]"
   pytest    # optional smoke test
   deactivate
   cd ..\help-chat-dotnet
   ```
3. **Restore and test the .NET solution**
   ```powershell
   dotnet restore
   # Point the tests at the interpreter that has help_chat installed
   $Env:HELPCHAT_PYTHON_PATH = (Resolve-Path ..\help-chat-python\.venv\Scripts\python.exe)
   dotnet test HelpChat.sln
   ```
   You can skip the environment variable if `python` on PATH already includes the package, or set `HelpChat:PythonPath` in `appsettings.json` instead.
4. **Runtime selection**
   - Set `HELPCHAT_PYTHON_PATH` or pass `pythonPath` to `HelpChatLib` if you need a specific interpreter.
- Otherwise, the library attempts (in order) the constructor argument, `HELPCHAT_PYTHON_PATH`, the Windows `py` launcher, `python`, `python3`, and specific `python3.x` executables on PATH. This makes Linux/macOS setups that only expose `python3` work out-of-the-box.

## Running Locally

Use these steps to demo the wrapper and console without publishing artifacts:

1. **Make sure the Python package is installed**
   - If you followed the root quick start, the `.venv` already contains it—no extra work.
   - Otherwise install it into whatever interpreter you plan to use (e.g. `python -m pip install -e ..\help-chat-python` inside your own venv or global Python).
   - Seeing a “global install” warning means the venv wasn’t active—reactivate and rerun `python -m pip ...` or use the full path `path\to\venv\python.exe -m pip install -e ..\help-chat-python`.
2. **Publish the console to a local folder**
   ```powershell
   dotnet publish HelpChat.Console/HelpChat.Console.csproj `
       -c Release `
       -r win-x64 `
       --self-contained false `
       -o .\publish\local
   ```
3. **Configure appsettings**
   - Copy `HelpChat.Console/appsettings.json` into `publish/local`.
   - Update `RootPath`, `TempPath`, `EmbeddingsPath`, and credentials.
   - Place your documents in the configured `RootPath` before launching so the first reindex picks them up.
4. **First run**
   ```powershell
   cd publish\local
   # Point at the interpreter that has help_chat installed (choose one):
   # $Env:HELPCHAT_PYTHON_PATH = (Resolve-Path ..\..\help-chat-python\.venv\Scripts\python.exe)
   # or edit appsettings.json -> HelpChat:PythonPath "C:\path\to\python.exe"
   # or rely on a global python.exe that already has the package
   .\HelpChat.Console.exe            # interactive session
   ```
   The console automatically performs an initial reindex on startup and streams requests through the CLI backend when pythonnet cannot initialize (e.g. Python 3.13+). You can still issue `/reindex` at any time to refresh embeddings.

## Updating

If you already have HelpChat.Lib or HelpChat.Console installed and want to update to the latest version:

### 1. Backup Your Data (Recommended)

Before updating, back up important data:

```powershell
# Backup embeddings database (preserves your indexed documents)
Copy-Item "C:\Temp\help-chat\embeddings.db" "C:\Temp\help-chat\embeddings.db.backup"

# Backup saved conversations (if using HelpChat.Console)
Copy-Item "C:\path\to\conversation_*.txt" "C:\backup\location\"

# Backup your appsettings.json if you've customized it
Copy-Item ".\publish\local\appsettings.json" ".\appsettings.json.backup"
```

### 2. Update the Code

Pull the latest changes from the repository:

```powershell
git pull origin main
```

### 3. Update Dependencies

**For developers working with the source:**

```powershell
cd help-chat-dotnet
dotnet restore
dotnet clean
dotnet build -c Release
```

**Update the Python package dependency:**

```powershell
cd ..\help-chat-python
.venv\Scripts\activate  # If using a venv
python -m pip install -e . --upgrade
deactivate
cd ..\help-chat-dotnet
```

**For applications using HelpChat.Lib from NuGet:**

```powershell
dotnet add package HelpChat.Lib --version <latest-version>
dotnet restore
```

### 4. Check Configuration

Review your `appsettings.json` for any new settings:

```powershell
# Compare your backup with the updated template
code .\appsettings.json.backup
code .\HelpChat.Console\appsettings.json
```

New optional settings can typically be left at their defaults. Check the [Configuration](#configuration) section above for the complete list of available settings.

**Breaking Changes**: Check the release notes for any breaking changes in configuration format or API signatures.

### 5. Rebuild and Republish (if applicable)

If you've published HelpChat.Console to a local folder:

```powershell
# Clean previous build
Remove-Item -Recurse -Force .\publish\local

# Republish
dotnet publish HelpChat.Console/HelpChat.Console.csproj `
    -c Release `
    -r win-x64 `
    --self-contained false `
    -o .\publish\local

# Restore your custom appsettings.json
Copy-Item ".\appsettings.json.backup" ".\publish\local\appsettings.json"
```

### 6. When to Re-index

**You DON'T need to re-index if:**
- You're just updating the .NET wrapper code
- Your documents haven't changed
- The Python package version hasn't changed

**You SHOULD re-index if:**
- The Python package (help-chat-python) was updated
- You've added new documents to your `RootPath`
- You've modified existing documents
- Release notes mention indexing improvements or embedding changes

**Your embeddings database is automatically preserved** during updates. The reindex process only processes new or changed files (based on SHA256 hash comparison).

To re-index:
- **Console app**: Restart (it automatically runs reindex on startup) or type `/reindex`
- **Library integration**: Call `helpChat.ReIndex()` in your code

### 7. Run Tests

Verify the update succeeded:

```powershell
# Set Python path for tests
$Env:HELPCHAT_PYTHON_PATH = (Resolve-Path ..\help-chat-python\.venv\Scripts\python.exe)

# Run all tests
dotnet test HelpChat.sln

# Expected: All 27 tests pass with 0 errors
```

### 8. Verify Your Application

**For HelpChat.Console users:**

```powershell
cd publish\local
.\HelpChat.Console.exe
```

Check that:
- Application starts without errors
- Configuration settings display correctly
- Database statistics show your expected file count
- You can query your documents successfully
- Type `/help` to verify all commands work

**For HelpChat.Lib integrators:**

Run your application and verify:
- `SetConfiguration()` succeeds
- `ReIndex()` completes (check progress callback if used)
- `MakeRequest()` returns expected results
- No new exceptions or warnings

### Rollback Procedure

If you encounter issues after updating:

```powershell
# Restore your embeddings database
Copy-Item "C:\Temp\help-chat\embeddings.db.backup" "C:\Temp\help-chat\embeddings.db"

# Restore your configuration
Copy-Item ".\appsettings.json.backup" ".\publish\local\appsettings.json"

# Revert to previous git commit
git log --oneline -10  # Find the commit hash you want
git checkout <previous-commit-hash>

# Rebuild
dotnet clean
dotnet build -c Release
```

### Migration Notes

**Python Version Changes:**
- If upgrading from Python 3.10-3.12 to Python 3.13+, the library will automatically switch from pythonnet to CLI backend
- Performance difference is minimal; both backends are fully functional
- No code changes required in your application

**Configuration Changes:**
- New `ModelName` setting added in recent versions (optional)
- Check release notes for any deprecated settings

## Deployment

### Publish HelpChat.Lib to NuGet

1. **Update version** in `HelpChat.Lib/HelpChat.Lib.csproj` (align with the Python package when releasing both).
2. **Pack the library**:
   ```powershell
   dotnet pack HelpChat.Lib/HelpChat.Lib.csproj -c Release -o ./artifacts
   ```
3. **Push to your feed**:
   ```powershell
   dotnet nuget push ./artifacts/HelpChat.Lib.<version>.nupkg --api-key <TOKEN> --source https://api.nuget.org/v3/index.json
   ```
4. **Tag the repository** once the package is live.

### Distribute HelpChat.Console

1. **Publish binaries**:
   ```powershell
   dotnet publish HelpChat.Console/HelpChat.Console.csproj -c Release -r win-x64 --self-contained false -o ./publish/win-x64
   ```
   For self-contained single-file output:
   ```powershell
   dotnet publish HelpChat.Console/HelpChat.Console.csproj -c Release -r win-x64 --self-contained true /p:PublishSingleFile=true /p:IncludeNativeLibrariesForSelfExtract=true -o ./publish/win-x64-selfcontained
   ```
2. **Bundle configuration**:
   - Include `appsettings.json`, README snippets, and any sample configs alongside the binary.
   - Provide instructions for setting `HELPCHAT_PYTHON_PATH` if a specific interpreter is required.

### Release Checklist

- `dotnet test HelpChat.sln`
- Ensure `help-chat-python` has been released if the wrapper relies on new Python features.
- Update READMEs and sample configurations with new version numbers.
- Create a Git tag matching the NuGet/PyPI release.

## Quick Start

### Using HelpChat.Lib

```csharp
using HelpChat.Lib;

// Initialize the library (optionally specify Python path)
using (HelpChatLib helpChat = new HelpChatLib())
{
    // Configure using individual parameters
    helpChat.SetConfiguration(
        rootPath: "C:\\docs",
        tempPath: "C:\\temp\\help-chat",
        apiPath: "https://api.openai.com/v1",
        embeddingsPath: "C:\\temp\\help-chat\\embeddings.db",
        supportedExtensions: ".pdf,.docx,.pptx,.xlsx,.md,.txt",  // Required: file types to index
        apiKey: "your-api-key",
        modelName: "gpt-4o",  // Optional: specify model, empty for auto-detect
        conversionTimeout: 5,  // Optional: timeout for file conversion (seconds)
        enableDebugLog: false  // Optional: enable debug logging to program_debug.log (in temp path)
    );

    // Index documents
    helpChat.ReIndex();

    // Ask questions
    string response = helpChat.MakeRequest("How do I configure the system?");
    Console.WriteLine(response);
}
```

### Using JSON Configuration

```csharp
using HelpChat.Lib;

using (HelpChatLib helpChat = new HelpChatLib())
{
    string configJson = @"{
        ""name"": ""My Project Docs"",
        ""root_path"": ""C:\\docs"",
        ""temp_path"": ""C:\\temp\\help-chat"",
        ""api_path"": ""https://api.openai.com/v1"",
        ""embeddings_path"": ""C:\\temp\\help-chat\\embeddings.db"",
        ""api_key"": ""your-api-key"",
        ""model_name"": ""gpt-4o"",
        ""conversion_timeout"": 5,
        ""supported_extensions"": "".pdf,.docx,.pptx,.xlsx,.md,.txt"",
        ""enable_debug_log"": false,
        ""context_documents"": 3
    }";

    helpChat.SetConfiguration(configJson);
    helpChat.ReIndex();

    string response = helpChat.MakeRequest("What are the system requirements?");
    Console.WriteLine(response);
}
```

## Python Runtime Detection

`HelpChatLib` automatically locates a Python interpreter in the following order:

1. `pythonPath` argument passed to the constructor.
2. `HELPCHAT_PYTHON_PATH` environment variable.
3. System defaults (`python` on `PATH`, or `py` launcher on Windows).

When the resolved interpreter targets Python 3.10–3.12, the library uses pythonnet for in-process interop. For newer Python releases, it transparently falls back to a CLI bridge that invokes `python -m help_chat.cli` to perform validation, indexing, and LLM requests.

> **Tip**: Set `HELPCHAT_PYTHON_PATH` (or pass `pythonPath`) to isolate the .NET integration to a specific virtual environment.

## HelpChat.Lib API Reference

### Constructor

```csharp
public HelpChatLib(string? pythonPath = null)
```

Initializes the library and Python runtime. If `pythonPath` is null, uses system PATH.

**Throws**: `PythonInitializationException` if Python cannot be initialized.

### SetConfiguration (JSON)

```csharp
public void SetConfiguration(string configJson)
```

Sets configuration using JSON string.

**Parameters**:
- `configJson`: JSON containing required and optional configuration fields

**Required Fields**: `root_path`, `temp_path`, `api_path`, `embeddings_path`, `supported_extensions`
**Optional Fields**: `name`, `api_key`, `model_name`, `conversion_timeout`, `enable_debug_log`, `context_documents`

> **Temp directory safety**
>
> Use a dedicated directory for `temp_path`. Help Chat creates a sentinel file named `.help_chat_temp` and will refuse to clean directories it does not manage to prevent accidental data loss.

> **Archive ingestion**
>
> If you allow archive formats (e.g., `.zip`) in `supported_extensions`, the indexing backend skips any archive larger than 50 MB. This is deliberate protection against decompression bombs—only enable archive processing for trusted inputs.

**Throws**: `ConfigurationException` if configuration is invalid.

### SetConfiguration (Parameters)

```csharp
public void SetConfiguration(
    string rootPath,
    string tempPath,
    string apiPath,
    string embeddingsPath,
    string supportedExtensions,
    string apiKey = "",
    string modelName = "",
    int conversionTimeout = 5,
    bool enableDebugLog = false
)
```

Sets configuration using individual parameters.

**Parameters**:
- `rootPath`: Directory containing documents to index
- `tempPath`: Temporary directory for processing
- `apiPath`: LLM API endpoint URL
- `embeddingsPath`: Path to SQLite embeddings database
- `supportedExtensions`: Comma-separated list of file extensions to index (required, e.g., ".pdf,.docx,.txt")
- `apiKey`: API key for authentication (optional, empty for local LLMs)
- `modelName`: LLM model name (optional, empty for auto-detection)
- `conversionTimeout`: Timeout in seconds for file conversion (optional, defaults to 5)
- `enableDebugLog`: Enable debug logging to program_debug.log inside the configured temp path (optional, defaults to false)

**Throws**: `ConfigurationException` if configuration is invalid.

### ReIndex

```csharp
public void ReIndex(Action<string>? progressCallback = null)
```

Reindexes all documents in the configured root path. Creates embeddings for new/changed files and removes deleted files from database.

**Parameters**:
- `progressCallback`: Optional callback invoked for each file being processed (receives file path as string). Only fires when files actually need processing (new or changed files).

**Notes**:
- Progress callback is only invoked when files need processing (embedding generation)
- Unchanged files are skipped silently (hash comparison is fast)
- If all files are up-to-date, callback never fires and reindex completes instantly

**Throws**:
- `InvalidOperationException` if configuration not set
- `IndexingException` if indexing fails

### MakeRequest

```csharp
public string MakeRequest(string prompt)
```

Makes a question/answer request using RAG (Retrieval Augmented Generation).

**Parameters**:
- `prompt`: User's question or request

**Returns**: LLM's response text

**Throws**:
- `InvalidOperationException` if configuration not set
- `LlmRequestException` if request fails

### Dispose

```csharp
public void Dispose()
```

Releases Python resources and shuts down Python runtime. Always call when done (use `using` statement).

## Exception Hierarchy

```
HelpChatException (base)
├── PythonInitializationException
├── ConfigurationException
├── IndexingException
└── LlmRequestException
```

All exceptions include descriptive messages and inner exceptions for debugging.

## HelpChat.Console Application

An interactive CLI for document-based question answering.

### Configuration

Edit `appsettings.json`:

```json
{
  "HelpChat": {
    "Name": "My Project Docs",
    "RootPath": "C:\\docs",
    "TempPath": "C:\\temp\\help-chat",
    "ApiPath": "https://api.openai.com/v1",
    "EmbeddingsPath": "C:\\temp\\help-chat\\embeddings.db",
    "ApiKey": "your-api-key",
    "ModelName": "gpt-4o",
    "ConversionTimeout": 5,
    "SupportedExtensions": ".pdf,.docx,.pptx,.xlsx,.md,.txt",
    "EnableDebugLog": false,
    "ContextDocuments": 3,
    "PythonPath": ""
  }
}
```
| Setting | Required | Description | Default |
| --- | --- | --- | --- |
| `Name` | Optional | Configuration name for user identification. | `""` |
| `RootPath` | Yes | Directory containing documents to index. | n/a |
| `TempPath` | Yes | Dedicated working directory for intermediate files and `_markdown` exports. | n/a |
| `EmbeddingsPath` | Yes | SQLite database file for embeddings; created automatically if missing. | n/a |
| `ApiPath` | Yes | Base URL for the LLM provider. | n/a |
| `ApiKey` | Optional | Provider API key. Leave empty for local providers such as Ollama. | `""` |
| `ModelName` | Optional | Explicit model identifier. Leave blank to auto-detect from `ApiPath`. | `""` |
| `ConversionTimeout` | Optional | Timeout in seconds for file conversion. Prevents hanging on problematic files. | `5` |
| `SupportedExtensions` | **Yes** | Comma-separated list of file extensions to index (e.g., ".pdf,.docx,.txt"). Must be explicitly configured. | n/a |
| `EnableDebugLog` | Optional | Enable debug logging to `program_debug.log` inside the temp path for troubleshooting. | `false` |
| `ContextDocuments` | Optional | Number of top documents attached as RAG context. | `3` |
| `PythonPath` | Optional | Absolute path to the Python interpreter for the console/wrapper. Omit if using `HELPCHAT_PYTHON_PATH` or a global Python. | unset |

> **Note on `ConversionTimeout`:** This prevents the indexer from hanging indefinitely on problematic files (e.g., corrupted documents, extremely large files). Files that exceed the timeout are skipped and logged. The default of 5 seconds works well for most documents.

> **Note on `SupportedExtensions`:** **REQUIRED**. You must explicitly specify which file types to index in appsettings.json. Extensions should be comma-separated with leading dots. Recommended value (known working): `".pdf,.docx,.pptx,.xlsx,.md,.txt"`. Exclude images (.jpg, .jpeg), archives (.zip), legacy binary formats (.doc), and audio files (.wav, .mp3) as these can cause performance issues or hanging. The application will fail if this setting is not configured.

> **Note on `EnableDebugLog`:** When set to `true`, creates a `program_debug.log` file in the configured temp path with timestamped debug messages, including per-file failures. The log is cleared at startup. Keep disabled (default) in production for better performance.

> **Ollama note:** Configure `ApiPath` as `http://localhost:11434/v1` to hit the OpenAI-compatible API surface.

### Running the Console App

```bash
cd HelpChat.Console
dotnet run
```

Or with command-line overrides:

```bash
dotnet run -- --HelpChat:ApiKey=your-key --HelpChat:ModelName=gpt-4o
```

### Available Commands

- `/help` - Show available commands
- `/history` - Display conversation history
- `/clear` - Clear conversation history
- `/save` - Save conversation to file (timestamped)
- `/list` - Show all indexed documents with file count
- `/reindex` - Rebuild document embeddings
- `/exit` - Exit application

Simply type your questions at the `>` prompt to get answers based on indexed documents.

**Visual Feedback**: The console provides animated spinners and timing information for all long-running operations:

- **Library Initialization**: Shows "Initializing HelpChat library" with an animated spinner (|, /, -, \) while detecting Python and loading configuration
- **Reindexing Operations**: Displays "Reindexing" or "Building embeddings database" with spinner before file processing begins. Then transitions to showing "Processing [/] filename" for each file being actively processed. If all files are up-to-date, displays "No files needed processing (all up to date)."
- **Question Responses**: Shows "Thinking" with spinner while waiting for the LLM response, then displays "Response (took X.XXs):" with the elapsed time in seconds
- **Database Statistics**: The `/list` command shows both database size and file count (e.g., "Database: 24.00 KB, Files: 5")

## Supported LLM Providers

The library supports any OpenAI-compatible API provider.

### OpenAI
```json
{
  "Name": "OpenAI Docs",
  "RootPath": "C:\\docs",
  "TempPath": "C:\\temp\\help-chat",
  "EmbeddingsPath": "C:\\temp\\help-chat\\embeddings.db",
  "ApiPath": "https://api.openai.com/v1",
  "ApiKey": "sk-your-openai-key",
  "ModelName": "gpt-4o",
  "ConversionTimeout": 5,
  "SupportedExtensions": ".pdf,.docx,.pptx,.xlsx,.md,.txt,.html,.htm,.xml,.json,.csv",
  "EnableDebugLog": false,
  "ContextDocuments": 3
}
```

### DeepSeek
```json
{
  "Name": "DeepSeek Docs",
  "RootPath": "C:\\docs",
  "TempPath": "C:\\temp\\help-chat",
  "EmbeddingsPath": "C:\\temp\\help-chat\\embeddings.db",
  "ApiPath": "https://api.deepseek.com",
  "ApiKey": "your-deepseek-key",
  "ModelName": "deepseek-chat",
  "ConversionTimeout": 5,
  "SupportedExtensions": ".pdf,.docx,.pptx,.xlsx,.md,.txt,.html,.htm,.xml,.json,.csv",
  "EnableDebugLog": false,
  "ContextDocuments": 3
}
```

### Ollama (Local)
```json
{
  "Name": "Ollama Local",
  "RootPath": "C:\\docs",
  "TempPath": "C:\\temp\\help-chat",
  "EmbeddingsPath": "C:\\temp\\help-chat\\embeddings.db",
  "ApiPath": "http://localhost:11434/v1",
  "ApiKey": "",
  "ModelName": "llama3.2",
  "ConversionTimeout": 5,
  "SupportedExtensions": ".pdf,.docx,.pptx,.xlsx,.md,.txt,.html,.htm,.xml,.json,.csv",
  "EnableDebugLog": false,
  "ContextDocuments": 2
}
```

### LM Studio (Local)
```json
{
  "Name": "LM Studio Local",
  "RootPath": "C:\\docs",
  "TempPath": "C:\\temp\\help-chat",
  "EmbeddingsPath": "C:\\temp\\help-chat\\embeddings.db",
  "ApiPath": "http://localhost:1234/v1",
  "ApiKey": "",
  "ModelName": "",
  "ConversionTimeout": 5,
  "SupportedExtensions": ".pdf,.docx,.pptx,.xlsx,.md,.txt,.html,.htm,.xml,.json,.csv",
  "EnableDebugLog": false,
  "ContextDocuments": 2
}
```

**Note**: If `ModelName` is empty, auto-detects based on `ApiPath`.

## Development

### Running Tests

```bash
dotnet test HelpChat.sln
```

**Test Coverage**:
- 27 tests exercise configuration validation, CLI fallback behavior, and exception pathways
- All tests run successfully against Python 3.13+ via the CLI backend (no native pythonnet dependency required)

### Build Release

```bash
dotnet build HelpChat.sln -c Release
```

### Code Quality

- Zero warnings, zero errors required
- No use of `var` keyword (explicit types)
- Sorted using statements
- String interpolation for formatting
- XML documentation on all public APIs

## Dependencies

All dependencies are free for commercial use:

- **Python.NET** (MIT) - C#/Python interoperability
- **xUnit** (Apache 2.0) - Testing framework
- **Moq** (BSD) - Mocking framework for tests
- **Microsoft.Extensions.Configuration** (MIT) - Configuration management

## Project Structure

```
help-chat-dotnet/
├── HelpChat.Lib/
│   ├── HelpChatLib.cs           # Main wrapper class
│   ├── Exceptions/
│   │   ├── HelpChatException.cs
│   │   ├── PythonInitializationException.cs
│   │   ├── ConfigurationException.cs
│   │   ├── IndexingException.cs
│   │   └── LlmRequestException.cs
│   └── HelpChat.Lib.csproj
├── HelpChat.Lib.Tests/
│   ├── HelpChatLibTests.cs      # Integration tests
│   ├── ExceptionTests.cs        # Exception unit tests
│   └── HelpChat.Lib.Tests.csproj
├── HelpChat.Console/
│   ├── Program.cs
│   ├── appsettings.json
│   └── HelpChat.Console.csproj
├── HelpChat.sln
└── README.md
```

## Error Handling Best Practices

```csharp
try
{
    using (HelpChatLib helpChat = new HelpChatLib())
    {
        helpChat.SetConfiguration(/* ... */);
        helpChat.ReIndex();
        string response = helpChat.MakeRequest("Your question");
    }
}
catch (PythonInitializationException ex)
{
    Console.WriteLine($"Python setup failed: {ex.Message}");
    // Check Python installation and help-chat-python package
}
catch (ConfigurationException ex)
{
    Console.WriteLine($"Configuration error: {ex.Message}");
    // Verify configuration parameters
}
catch (IndexingException ex)
{
    Console.WriteLine($"Indexing failed: {ex.Message}");
    // Check root_path exists and is accessible
}
catch (LlmRequestException ex)
{
    Console.WriteLine($"LLM request failed: {ex.Message}");
    // Check API key, network, and embeddings database
}
```

## Troubleshooting

### Python Not Found
**Error**: `PythonInitializationException: Failed to initialize Python`

**Solutions**:
- Install Python 3.10+
- Specify Python path: `new HelpChatLib("C:\\Python310\\python.exe")`
- Add Python to system PATH

### Package Not Found
**Error**: `PythonInitializationException: No module named 'help_chat'`

**Solutions**:
- Install help-chat-python package: `pip install -e ..\help-chat-python`
- Verify installation: `python -c "import help_chat"`

### Configuration Errors
**Error**: `ConfigurationException: Missing required fields`

**Solutions**:
- Ensure all required fields present: `root_path`, `temp_path`, `api_path`, `embeddings_path`
- Check JSON syntax is valid

### Indexing Errors
**Error**: `IndexingException: Root path does not exist`

**Solutions**:
- Verify `root_path` directory exists
- Check file permissions
- Ensure disk space available

## Performance Considerations

- **First Run**: Downloads sentence-transformers model (~80MB) and indexes all documents
- **Incremental Updates**: Only processes changed files based on SHA256 hashes
- **Memory Usage**: Proportional to document collection size
- **Python Runtime**: Shared across all instances (singleton pattern)

## License

MIT License - Free for commercial use

## See Also

- **Main Documentation**: See [repository root README](../../README.md) for full system documentation
- **Python Package**: See [help-chat-python](../help-chat-python/README.md) for Python package documentation
- **Requirements**: See [help-chat-dotnet.md](help-chat-dotnet.md) for detailed requirements
