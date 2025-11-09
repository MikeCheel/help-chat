# Help Chat .NET - Requirements Document

## Overview

The Help Chat .NET solution provides a C# wrapper around the help-chat-python package, enabling .NET applications to leverage document indexing, vector embeddings, and LLM-based question answering with Retrieval Augmented Generation (RAG) support.

## Project Structure

The solution consists of two projects located in the `help-chat-dotnet` directory:

1. **HelpChat.Lib** - Core wrapper library with unit tests
2. **HelpChat.Console** - Interactive console application

---

## Project 1: HelpChat.Lib

### Purpose

A C# class library that wraps the help-chat-python package using Python.NET, providing a native .NET API for document-based chat functionality.

### Technical Requirements

- **Framework**: .NET 8.0 (Latest LTS)
- **Interop Library**: Python.NET 3.0+ (latest stable from NuGet)
- **Testing Framework**: xUnit
- **Mocking Framework**: Moq (for unit tests)
- **Dependencies**:
  - Python 3.10+ runtime
  - help-chat-python package installed and accessible

### Architecture

The library provides a managed wrapper around three Python modules from the help-chat-python package:
- `help_chat.keyring` (KeyRing module)
- `help_chat.doc_indexer` (DocIndexer module)
- `help_chat.llm` (LLM module)

### Core Class: HelpChatLib

#### Constructor

```csharp
public HelpChatLib(string? pythonPath = null)
```

**Purpose**: Initialize the Python runtime and import required Python modules.

**Parameters**:
- `pythonPath` (optional): Path to Python executable. If null, uses system PATH.

**Behavior**:
- Initialize Python.NET runtime
- Set Python paths appropriately
- Import the three help-chat-python modules (keyring, doc_indexer, llm)
- Throw `PythonInitializationException` if Python cannot be initialized or modules cannot be loaded

**Error Handling**:
- Validate Python path exists (if provided)
- Verify help-chat-python package is installed
- Provide clear error messages for common setup issues

---

#### Method 1: SetConfiguration

**Signature 1** (JSON Configuration):
```csharp
public void SetConfiguration(string configJson)
```

**Purpose**: Configure the system using a JSON string that matches the help-chat-python KeyRing.build() expected format.

**Parameters**:
- `configJson`: JSON string containing configuration properties

**JSON Format**:
```json
{
  "root_path": "C:\\path\\to\\documents",
  "temp_path": "C:\\path\\to\\temp",
  "api_path": "https://api.openai.com/v1",
  "embeddings_path": "C:\\path\\to\\embeddings.db",
  "api_key": "optional-api-key"
}
```

**Required Fields**:
- `root_path`: Directory containing documents to index
- `temp_path`: Temporary directory for processing
- `api_path`: LLM API endpoint URL
- `embeddings_path`: Path to SQLite embeddings database

**Optional Fields**:
- `api_key`: API key for LLM provider (empty string for local providers like Ollama)

**Behavior**:
- Parse and validate JSON structure
- Call Python KeyRing.build() method to create configuration dictionary
- Store configuration for use by ReIndex() and MakeRequest() methods
- Throw `ConfigurationException` for invalid JSON or missing required fields

---

**Signature 2** (Individual Parameters):
```csharp
public void SetConfiguration(
    string rootPath,
    string tempPath,
    string apiPath,
    string embeddingsPath,
    string apiKey = ""
)
```

**Purpose**: Configure the system using individual parameters (overload for convenience).

**Parameters**:
- `rootPath`: Directory containing documents to index
- `tempPath`: Temporary directory for processing
- `apiPath`: LLM API endpoint URL
- `embeddingsPath`: Path to SQLite embeddings database
- `apiKey` (optional): API key for LLM provider (defaults to empty string)

**Behavior**:
- Build JSON string from parameters
- Call the JSON overload of SetConfiguration()
- Throw `ConfigurationException` for invalid parameters

**Implementation Note**: This overload should internally construct a JSON string and call the primary SetConfiguration(string) method to avoid code duplication.

---

#### Method 2: ReIndex

**Signature**:
```csharp
public void ReIndex()
```

**Purpose**: Wrapper around the DocIndexer.reindex() method from help-chat-python. Scans the root path for documents, converts them to markdown, generates vector embeddings, and stores them in the SQLite database.

**Prerequisites**:
- SetConfiguration() must be called first
- Configuration must include valid root_path, temp_path, and embeddings_path

**Behavior**:
1. Verify configuration has been set
2. Call Python DocIndexer.reindex() with stored configuration
3. DocIndexer will:
   - Validate root_path exists (throw exception if not)
   - Create temp_path if it doesn't exist and ensure it's empty
   - Create embeddings database if it doesn't exist
   - Recursively scan root_path for supported file types
   - Convert files to markdown using Markitdown library
   - Generate vector embeddings using sentence-transformers
   - Store/update embeddings in SQLite database with SHA256 file hashes
   - Delete database records for files that no longer exist
   - Update records for files that have changed (hash comparison)

**Error Handling**:
- Throw `InvalidOperationException` if configuration not set
- Throw `IndexingException` if Python reindex operation fails
- Wrap Python exceptions with meaningful .NET exception messages

**Performance Considerations**:
- This operation can be time-consuming for large document sets
- Consider exposing progress callbacks in future versions

---

#### Method 3: MakeRequest

**Signature**:
```csharp
public string MakeRequest(string prompt)
```

**Purpose**: Wrapper around the HelpChat.make_request() method from help-chat-python. Uses Retrieval Augmented Generation (RAG) to answer questions based on indexed documents.

**Parameters**:
- `prompt`: User's question or request

**Prerequisites**:
- SetConfiguration() must be called first
- Configuration must include valid api_path, api_key, and embeddings_path
- Documents must be indexed (ReIndex() called at least once)

**Behavior**:
1. Verify configuration has been set
2. Call Python HelpChat.make_request() with the prompt
3. HelpChat will:
   - Generate vector embedding for the prompt
   - Query embeddings database for relevant document chunks
   - Construct augmented prompt with relevant context
   - Send request to LLM API (OpenAI/Ollama/LM Studio)
   - Return LLM response as string

**Return Value**:
- String containing the LLM's response

**Error Handling**:
- Throw `InvalidOperationException` if configuration not set
- Throw `LlmRequestException` if API request fails
- Wrap Python exceptions with meaningful .NET exception messages
- Handle network timeouts and API errors gracefully

**Supported LLM Providers**:
- OpenAI API (api_path: "https://api.openai.com/v1")
- Ollama local runtime (api_path: "http://localhost:11434")
- LM Studio local server (api_path: "http://localhost:1234/v1")

---

#### IDisposable Implementation

**Signature**:
```csharp
public void Dispose()
```

**Purpose**: Properly clean up Python runtime resources and prevent memory leaks.

**Behavior**:
- Implement full IDisposable pattern
- Release Python module references
- Shutdown Python runtime if initialized
- Support multiple calls to Dispose() (idempotent)
- Suppress finalizer after disposal

**Implementation**:
```csharp
protected virtual void Dispose(bool disposing)
{
    if (!_disposed)
    {
        if (disposing)
        {
            // Release Python resources
            // Shutdown Python.NET runtime
        }
        _disposed = true;
    }
}

public void Dispose()
{
    Dispose(true);
    GC.SuppressFinalize(this);
}
```

---

### Exception Hierarchy

Create custom exception classes for clear error handling:

#### Base Exception
```csharp
public class HelpChatException : Exception
{
    public HelpChatException() { }
    public HelpChatException(string message) : base(message) { }
    public HelpChatException(string message, Exception inner) : base(message, inner) { }
}
```

#### Derived Exceptions

1. **PythonInitializationException**
   - Thrown when Python runtime fails to initialize
   - Thrown when Python path is invalid
   - Thrown when help-chat-python package cannot be imported

2. **ConfigurationException**
   - Thrown when JSON configuration is invalid
   - Thrown when required configuration fields are missing
   - Thrown when configuration validation fails

3. **IndexingException**
   - Thrown when document indexing fails
   - Thrown when root_path doesn't exist
   - Wraps errors from DocIndexer.reindex()

4. **LlmRequestException**
   - Thrown when LLM API requests fail
   - Thrown when embeddings database is inaccessible
   - Wraps errors from HelpChat.make_request()

All exceptions should:
- Inherit from `HelpChatException`
- Include constructors for: default, message, message + inner exception
- Provide meaningful error messages with actionable guidance

---

### Unit Testing Requirements

**Test Project**: HelpChat.Lib.Tests (xUnit)

#### Test Categories

1. **Exception Tests** (13 tests)
   - Test all exception constructors
   - Verify inheritance hierarchy
   - Test exception message storage
   - No external dependencies required

2. **Integration Tests** (11 tests)
   - Constructor with null Python path
   - Constructor with invalid Python path
   - SetConfiguration with valid JSON
   - SetConfiguration with invalid JSON
   - SetConfiguration with missing fields
   - SetConfiguration with individual parameters
   - ReIndex without configuration
   - MakeRequest without configuration
   - Dispose multiple calls
   - Full workflow integration tests (require Python environment)

#### Testing Guidelines

- Use Moq for mocking where appropriate
- Exception tests should be pure unit tests (no Python required)
- Integration tests require Python environment with help-chat-python installed
- Tests should follow AAA pattern (Arrange, Act, Assert)
- Test method names should clearly describe what is being tested
- Achieve minimum 70% code coverage (target 90%+)

#### Test Execution

- All exception tests must pass in any environment
- Integration tests may be skipped in CI without Python
- No warnings or errors in test output
- Tests should run quickly (< 1 minute for unit tests)

---

### Code Quality Requirements

1. **C# Coding Standards**
   - Target .NET 8.0
   - Enable nullable reference types
   - Avoid `var` keyword unless necessary
   - Use string interpolation ($"") instead of string.Format()
   - Sort and remove unused using statements
   - Follow standard C# naming conventions (PascalCase for public members)

2. **Build Requirements**
   - Zero warnings in Debug and Release configurations
   - Zero errors
   - All NuGet packages free for commercial use
   - No code analysis suppressions without justification

3. **Security**
   - Validate all input parameters
   - Properly handle API keys (never log or expose)
   - Use parameterized queries for database operations
   - Follow OWASP security best practices

4. **Documentation**
   - XML comments on all public types and members
   - Clear exception documentation
   - Usage examples in comments
   - README with installation and usage instructions

---

## Project 2: HelpChat.Console

### Purpose

An interactive console application that provides a user-friendly interface for document-based question answering using the HelpChat.Lib library.

### Technical Requirements

- **Framework**: .NET 8.0
- **Configuration**: Microsoft.Extensions.Configuration
- **Dependencies**: HelpChat.Lib (project reference)
- **Testing**: No unit tests required (simple interactive application)

### Features

#### 1. Configuration Management

**Configuration File**: `appsettings.json`

```json
{
  "HelpChat": {
    "RootPath": "C:\\docs",
    "TempPath": "C:\\temp\\help-chat",
    "ApiPath": "https://api.openai.com/v1",
    "EmbeddingsPath": "C:\\temp\\help-chat\\embeddings.db",
    "ApiKey": "",
    "PythonPath": ""
  }
}
```

**Configuration Sources** (in priority order):
1. Command-line arguments (override appsettings.json)
2. appsettings.json file

**Configuration Loading**:
```csharp
var builder = new ConfigurationBuilder()
    .SetBasePath(Directory.GetCurrentDirectory())
    .AddJsonFile("appsettings.json", optional: false, reloadOnChange: false)
    .AddCommandLine(args);

var configuration = builder.Build();
```

**Command-Line Override Example**:
```
HelpChat.Console.exe --HelpChat:ApiKey=sk-your-key --HelpChat:RootPath=C:\other\docs
```

---

#### 2. Startup Display

When the application starts, display:

1. **Application Banner**
```
=================================
  HelpChat - Interactive Console
=================================
```

2. **Current Configuration**
```
Configuration:
  Root Path: C:\docs
  Temp Path: C:\temp\help-chat
  API Path: https://api.openai.com/v1
  Embeddings Path: C:\temp\help-chat\embeddings.db
  Python Path: (system PATH)
```

3. **Database Statistics** (if embeddings database exists)
```
Database Statistics:
  Database Size: 1024.50 KB
  Last Modified: 2025-11-01 10:30:15
```

Or if database doesn't exist:
```
Database Statistics:
  Database does not exist. Run /reindex to create it.
```

4. **Initialization Status**
```
Initializing HelpChat library...
HelpChat initialized successfully.
```

---

#### 3. Interactive Command Loop

**Available Commands**:

```
Commands:
  /help      - Show available commands
  /history   - Show conversation history
  /clear     - Clear conversation history
  /save      - Save conversation to file
  /reindex   - Reindex documents
  /exit      - Exit application

Enter your question or command:
```

**Command Descriptions**:

1. **/help**
   - Display all available commands with descriptions
   - No parameters required

2. **/history**
   - Display all conversation messages with timestamps
   - Format: `[YYYY-MM-DD HH:mm:ss] User: {question}`
   - Format: `[YYYY-MM-DD HH:mm:ss] Assistant: {response}`
   - Display "No conversation history" if empty

3. **/clear**
   - Clear all conversation history from memory
   - Display confirmation message in green
   - Does not affect saved files

4. **/save**
   - Save conversation history to text file
   - Filename format: `conversation_YYYYMMDD_HHmmss.txt`
   - Display success message with filename in green
   - Display error message in red if save fails
   - Display "No conversation history to save" if empty

5. **/reindex**
   - Call HelpChatLib.ReIndex() to rebuild embeddings database
   - Display "Reindexing documents..." message
   - Display success message in green when complete
   - Display updated database statistics
   - Display error message in red if reindexing fails
   - Wrap IndexingException appropriately

6. **/exit**
   - Display "Goodbye!" message
   - Exit application cleanly
   - Ensure Dispose() is called on HelpChatLib

---

#### 4. Question Handling

**Prompt**: `> `

**User Input Processing**:
- Commands start with `/` (handled by command processor)
- All other input treated as questions

**Question Workflow**:
1. Add question to conversation history with timestamp
2. Display "Thinking..." message in cyan
3. Call HelpChatLib.MakeRequest(question)
4. Add response to conversation history with timestamp
5. Display "Response:" label in green
6. Display response text in default color
7. Handle LlmRequestException with red error message

**Example Interaction**:
```
> How do I configure the API key?

Thinking...
Response:
The API key can be configured in appsettings.json under HelpChat:ApiKey,
or via command-line argument --HelpChat:ApiKey=your-key...

> /save
Conversation saved to: conversation_20251101_103045.txt

> /exit
Goodbye!
```

---

#### 5. Error Handling

**Error Types and Display**:

1. **Configuration Errors** (ConfigurationException)
   - Display in red: `Configuration error: {message}`
   - Exit application with code 1

2. **Python Initialization Errors** (PythonInitializationException)
   - Display in red: `Failed to initialize Python: {message}`
   - Exit application with code 1

3. **Indexing Errors** (IndexingException)
   - Display in red: `Reindexing failed: {message}`
   - Continue running (don't exit)

4. **LLM Request Errors** (LlmRequestException)
   - Display in red: `Request failed: {message}`
   - Continue running (don't exit)

5. **Unhandled Errors**
   - Display in red: `Fatal error: {message}`
   - Exit application with code 1

---

#### 6. Console Formatting

**Color Scheme**:
- **Cyan**: "Thinking..." status messages
- **Green**: Success messages, "Response:" label, confirmation messages
- **Red**: Error messages
- **Default**: Normal text, user input, response content

**Output Guidelines**:
- Use `Console.ForegroundColor` for colored text
- Always call `Console.ResetColor()` after colored output
- Keep formatting simple and readable
- Ensure accessibility (don't rely solely on color for information)

---

#### 7. Resource Management

**Cleanup**:
```csharp
try
{
    // Application logic
}
catch (Exception ex)
{
    // Error handling
}
finally
{
    _helpChatLib?.Dispose();
}
```

**Requirements**:
- Dispose HelpChatLib in finally block
- Ensure cleanup on all exit paths
- Handle Ctrl+C gracefully if possible

---

### User Experience Requirements

1. **Simplicity**
   - Keep implementation straightforward
   - Don't over-engineer features
   - Focus on core functionality
   - Provide clear, concise messages

2. **Feedback**
   - Show status during long operations (reindexing, LLM requests)
   - Provide clear success/error messages
   - Display timestamps for conversation tracking
   - Show configuration on startup for verification

3. **Flexibility**
   - Support both configuration file and CLI arguments
   - Allow optional API key for local LLMs
   - Optional Python path configuration
   - Conversation save feature for reference

4. **Reliability**
   - Graceful error handling
   - Don't crash on single request failures
   - Clear error messages with context
   - Proper resource cleanup

---

## Implementation Priorities

### Phase 1: Core Library
1. Create solution and project structure
2. Add Python.NET NuGet package
3. Implement HelpChatLib class with all methods
4. Create custom exception hierarchy
5. Implement IDisposable pattern

### Phase 2: Testing
1. Create test project with xUnit
2. Implement exception unit tests (13 tests)
3. Implement integration tests (11 tests)
4. Verify code coverage (target 70%+ minimum)

### Phase 3: Console Application
1. Create console project
2. Add Microsoft.Extensions.Configuration packages
3. Implement configuration loading
4. Implement startup display
5. Implement interactive command loop
6. Implement all commands
7. Add colored console output
8. Test end-to-end workflow

### Phase 4: Quality Assurance
1. Verify zero build warnings/errors
2. Run all tests (24 total)
3. Test with real Python environment
4. Test with different LLM providers
5. Validate exception handling
6. Security review
7. Documentation review

---

## Success Criteria

### HelpChat.Lib
- ✅ Builds with 0 warnings, 0 errors
- ✅ All 24 tests implemented
- ✅ 13/13 exception tests pass (no Python required)
- ✅ 11 integration tests pass (with Python environment)
- ✅ Code coverage ≥ 70%
- ✅ All methods properly wrap Python functionality
- ✅ IDisposable pattern correctly implemented
- ✅ Custom exceptions properly structured

### HelpChat.Console
- ✅ Builds with 0 warnings, 0 errors
- ✅ Loads configuration from appsettings.json
- ✅ Supports command-line overrides
- ✅ All 6 commands implemented and functional
- ✅ Colored console output working
- ✅ Error handling for all exception types
- ✅ Conversation history tracking
- ✅ File save functionality
- ✅ Proper resource cleanup

### Overall Solution
- ✅ Follows GitHub repository best practices
- ✅ All dependencies free for commercial use
- ✅ Security best practices followed
- ✅ Documentation complete and accurate
- ✅ End-to-end workflow tested
- ✅ Ready for production use

---

## Future Enhancements (Out of Scope)

- Progress callbacks for long-running operations
- Async/await support for MakeRequest
- Conversation context management (multi-turn conversations)
- Streaming responses from LLM
- Batch processing support
- Web API wrapper
- GUI application
- Docker containerization
- Cross-platform Python distribution

---

## Dependencies

### Required
- .NET 8.0 SDK
- Python 3.10+
- help-chat-python package
- Python.NET 3.0+

### NuGet Packages
- **HelpChat.Lib**:
  - Python.NET (latest 3.x stable)

- **HelpChat.Lib.Tests**:
  - xUnit
  - xUnit.runner.visualstudio
  - Moq
  - Microsoft.NET.Test.Sdk

- **HelpChat.Console**:
  - Microsoft.Extensions.Configuration
  - Microsoft.Extensions.Configuration.Json
  - Microsoft.Extensions.Configuration.CommandLine

All packages must be free for commercial use (verified).

---

## License

MIT License - Free for commercial use
