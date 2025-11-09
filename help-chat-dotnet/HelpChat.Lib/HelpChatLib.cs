using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using HelpChat.Lib.Exceptions;
using Python.Runtime;

namespace HelpChat.Lib
{
    /// <summary>
    /// .NET wrapper for the help-chat-python package.
    /// Provides document indexing and LLM-based chat with RAG support.
    /// </summary>
    public class HelpChatLib : IDisposable
    {
        private bool _disposed;
        private readonly IPythonBackend _backend;
        private Dictionary<string, string>? _config;

        /// <summary>
        /// Initializes a new instance of the HelpChatLib class.
        /// Attempts to use pythonnet when the configured interpreter supports it,
        /// otherwise falls back to a CLI bridge that communicates with Python processes.
        /// </summary>
        /// <param name="pythonPath">
        /// Optional path to the Python executable. When omitted the system PATH is used.
        /// Accepts either an executable path or the directory containing python.exe.
        /// </param>
        /// <exception cref="PythonInitializationException">Thrown when Python cannot be located.</exception>
        public HelpChatLib(string? pythonPath = null)
        {
            PythonRuntimeInfo runtimeInfo = PythonRuntimeInfo.Detect(pythonPath);
            _backend = InitializeBackend(runtimeInfo);
        }

        /// <summary>
        /// Sets the configuration for the HelpChat library using a JSON string.
        /// </summary>
        /// <param name="configJson">JSON string containing configuration parameters.</param>
        /// <exception cref="ConfigurationException">Thrown when configuration is invalid.</exception>
        public void SetConfiguration(string configJson)
        {
            _config = _backend.SetConfiguration(configJson);
        }

        /// <summary>
        /// Sets the configuration for the HelpChat library using individual parameters.
        /// </summary>
        /// <param name="rootPath">Root directory path to scan for documents.</param>
        /// <param name="tempPath">Temporary directory path for processing.</param>
        /// <param name="apiPath">API endpoint URL for the LLM provider.</param>
        /// <param name="embeddingsPath">Path to the embeddings database file.</param>
        /// <param name="supportedExtensions">Comma-separated list of file extensions to index (e.g., ".pdf,.docx,.txt"). Required - must be explicitly specified.</param>
        /// <param name="apiKey">Optional API key for authentication.</param>
        /// <param name="modelName">Optional LLM model name (empty string for auto-detection).</param>
        /// <param name="conversionTimeout">Optional timeout in seconds for file conversion (default: 5).</param>
        /// <param name="embeddingModel">Optional SentenceTransformer model name for embeddings (default: "all-MiniLM-L6-v2").</param>
        /// <param name="enableDebugLog">Optional flag to enable debug logging to program_debug.log (default: false).</param>
        /// <param name="contextDocuments">Optional number of top documents to attach as context during responses (default: 5).</param>
        /// <param name="maxTokens">Optional maximum tokens for LLM response (default: 2000).</param>
        /// <param name="temperature">Optional temperature for LLM generation (default: 0.7).</param>
        /// <param name="topP">Optional top-p sampling parameter (default: 0.9).</param>
        /// <param name="timeout">Optional timeout in seconds for LLM requests (default: 60.0).</param>
        /// <exception cref="ConfigurationException">Thrown when configuration is invalid.</exception>
        public void SetConfiguration(
            string rootPath,
            string tempPath,
            string apiPath,
            string embeddingsPath,
            string supportedExtensions,
            string apiKey = "",
            string modelName = "",
            int conversionTimeout = 5,
            string embeddingModel = "",
            bool enableDebugLog = false,
            int contextDocuments = 5,
            int maxTokens = 2000,
            double temperature = 0.7,
            double topP = 0.9,
            double timeout = 60.0)
        {
            if (string.IsNullOrWhiteSpace(supportedExtensions))
            {
                throw new ConfigurationException("Supported file extensions must be specified.");
            }

            Dictionary<string, string> configDict = new()
            {
                { "root_path", rootPath },
                { "temp_path", tempPath },
                { "api_path", apiPath },
                { "embeddings_path", embeddingsPath },
                { "api_key", apiKey },
                { "model_name", modelName },
                { "conversion_timeout", conversionTimeout.ToString() },
                { "supported_extensions", supportedExtensions },
                { "embedding_model", embeddingModel },
                { "enable_debug_log", enableDebugLog.ToString().ToLower() },
                { "context_documents", contextDocuments.ToString() },
                { "max_tokens", maxTokens.ToString() },
                { "temperature", temperature.ToString() },
                { "top_p", topP.ToString() },
                { "timeout", timeout.ToString() }
            };

            _config = _backend.SetConfiguration(configDict);
        }

        /// <summary>
        /// Reindexes all documents in the configured root path.
        /// </summary>
        /// <param name="progressCallback">Optional callback invoked for each file being processed.</param>
        /// <exception cref="IndexingException">Thrown when indexing fails.</exception>
        /// <exception cref="InvalidOperationException">Thrown when configuration has not been set.</exception>
        public void ReIndex(Action<string>? progressCallback = null)
        {
            EnsureConfigured();
            _backend.ReIndex(_config!, progressCallback);
        }

        /// <summary>
        /// Makes a request to the LLM with the provided prompt.
        /// Uses RAG to augment the prompt with relevant document context.
        /// </summary>
        /// <param name="prompt">The user's question or prompt.</param>
        /// <returns>The LLM's response.</returns>
        /// <exception cref="LlmRequestException">Thrown when the LLM request fails.</exception>
        /// <exception cref="InvalidOperationException">Thrown when configuration has not been set.</exception>
        public string MakeRequest(string prompt)
        {
            EnsureConfigured();
            return _backend.MakeRequest(_config!, prompt);
        }

        /// <summary>
        /// Releases all resources used by the HelpChatLib.
        /// </summary>
        public void Dispose()
        {
            Dispose(true);
            GC.SuppressFinalize(this);
        }

        /// <summary>
        /// Releases unmanaged and optionally managed resources.
        /// </summary>
        /// <param name="disposing">True to release both managed and unmanaged resources; false to release only unmanaged resources.</param>
        protected virtual void Dispose(bool disposing)
        {
            if (!_disposed)
            {
                if (disposing)
                {
                    _backend.Dispose();
                }

                _disposed = true;
            }
        }

        /// <summary>
        /// Destructor for HelpChatLib.
        /// </summary>
        ~HelpChatLib()
        {
            Dispose(false);
        }

        private void EnsureConfigured()
        {
            if (_config == null)
            {
                throw new InvalidOperationException("Configuration must be set before invoking this operation. Call SetConfiguration first.");
            }
        }

        private static IPythonBackend InitializeBackend(PythonRuntimeInfo runtimeInfo)
        {
            if (runtimeInfo.SupportsPythonNet)
            {
                try
                {
                    return new PythonNetBackend(runtimeInfo);
                }
                catch (PythonInitializationException)
                {
                    // Fall through to CLI backend
                }
            }

            return new PythonCliBackend(runtimeInfo);
        }

        private interface IPythonBackend : IDisposable
        {
            Dictionary<string, string> SetConfiguration(string configJson);

            Dictionary<string, string> SetConfiguration(Dictionary<string, string> config);

            void ReIndex(Dictionary<string, string> config, Action<string>? progressCallback);

            string MakeRequest(Dictionary<string, string> config, string prompt);
        }

        private sealed class PythonRuntimeInfo
        {
            private const string DefaultExecutableName = "python";

            private PythonRuntimeInfo(string executable, string home, Version version, string? dllPath)
            {
                Executable = executable;
                Home = home;
                Version = version;
                DllPath = dllPath;
            }

            public string Executable { get; }

            public string Home { get; }

            public Version Version { get; }

            public string? DllPath { get; }

            public bool SupportsPythonNet => Version.Major == 3 && Version.Minor <= 12 && !string.IsNullOrWhiteSpace(DllPath);

            public static PythonRuntimeInfo Detect(string? providedPath)
            {
                string? explicitCandidate = null;
                bool hasExplicitPath = !string.IsNullOrWhiteSpace(providedPath);
                if (hasExplicitPath)
                {
                    explicitCandidate = NormalizeCandidatePath(providedPath);
                    if (explicitCandidate == null)
                    {
                        Console.WriteLine($"Warning: Configured PythonPath '{providedPath}' not found or invalid. Falling back to HELPCHAT_PYTHON_PATH or system PATH.");
                    }
                }

                string? envPath = Environment.GetEnvironmentVariable("HELPCHAT_PYTHON_PATH");
                string? envCandidate = NormalizeCandidatePath(envPath);
                if (envCandidate == null && !string.IsNullOrWhiteSpace(envPath))
                {
                    Console.WriteLine($"Warning: HELPCHAT_PYTHON_PATH '{envPath}' not found or invalid. Falling back to system PATH.");
                }

                string? candidate = explicitCandidate ?? envCandidate;

                string pythonExecutable = LocatePythonExecutable(candidate);
                PythonRuntimeProbeResult probeResult = ProbeRuntime(pythonExecutable) ?? throw new PythonInitializationException("Unable to probe Python runtime details.");
                Version version = ParseVersion(probeResult.Version)
                    ?? throw new PythonInitializationException($"Unsupported Python version format: {probeResult.Version}");

                string? dllPath = ResolvePythonDll(pythonExecutable, probeResult.HomeDirectory, version);

                return new PythonRuntimeInfo(pythonExecutable, probeResult.HomeDirectory, version, dllPath);
            }

            private static string? NormalizeCandidatePath(string? path)
            {
                if (string.IsNullOrWhiteSpace(path))
                {
                    return null;
                }

                string trimmedPath = path.Trim();
                string expanded;

                try
                {
                    expanded = Environment.ExpandEnvironmentVariables(trimmedPath);
                }
                catch (ArgumentException ex)
                {
                    Console.WriteLine($"Warning: Path '{trimmedPath}' contains invalid environment variable syntax: {ex.Message}");
                    return null;
                }
                catch (FormatException ex)
                {
                    Console.WriteLine($"Warning: Path '{trimmedPath}' has invalid format: {ex.Message}");
                    return null;
                }

                if (File.Exists(expanded))
                {
                    return expanded;
                }

                if (Directory.Exists(expanded))
                {
                    string exePath = Path.Combine(expanded, OperatingSystem.IsWindows() ? "python.exe" : "python");
                    return File.Exists(exePath) ? exePath : null;
                }

                return null;
            }

            private static string LocatePythonExecutable(string? candidate)
            {
                if (!string.IsNullOrWhiteSpace(candidate) && File.Exists(candidate))
                {
                    return candidate;
                }

                string? fromEnv = Environment.GetEnvironmentVariable("PYTHONEXECUTABLE");
                if (!string.IsNullOrWhiteSpace(fromEnv) && File.Exists(fromEnv))
                {
                    return fromEnv;
                }

                if (OperatingSystem.IsWindows())
                {
                    string? fromLauncher = TryResolveViaPyLauncher();
                    if (!string.IsNullOrWhiteSpace(fromLauncher))
                    {
                        return fromLauncher;
                    }
                }

                foreach (string executableName in EnumerateCandidateExecutables())
                {
                    string? fromPath = FindExecutableInPath(executableName);
                    if (fromPath != null)
                    {
                        return fromPath;
                    }
                }

                throw new PythonInitializationException("Python executable could not be located. Set HELPCHAT_PYTHON_PATH or ensure python is on the PATH.");
            }

            private static IEnumerable<string> EnumerateCandidateExecutables()
            {
                if (OperatingSystem.IsWindows())
                {
                    yield return $"{DefaultExecutableName}.exe";
                    yield return "python3.exe";
                    for (int minor = 13; minor >= 7; minor--)
                    {
                        yield return $"python3.{minor}.exe";
                    }
                }
                else
                {
                    yield return DefaultExecutableName;
                    yield return "python3";
                    for (int minor = 13; minor >= 7; minor--)
                    {
                        yield return $"python3.{minor}";
                    }
                }
            }

            private static string? TryResolveViaPyLauncher()
            {
                try
                {
                    ProcessStartInfo psi = new()
                    {
                        FileName = "py",
                        Arguments = "-0p",
                        RedirectStandardOutput = true,
                        RedirectStandardError = true,
                        UseShellExecute = false,
                        CreateNoWindow = true
                    };

                    using Process process = Process.Start(psi) ?? throw new InvalidOperationException("Unable to start py launcher.");
                    string output = process.StandardOutput.ReadToEnd();
                    process.WaitForExit();

                    if (process.ExitCode != 0)
                    {
                        return null;
                    }

                    string? firstPath = output
                        .Split(['\r', '\n'], StringSplitOptions.RemoveEmptyEntries)
                        .Select(line => line.Split(' ', StringSplitOptions.RemoveEmptyEntries).LastOrDefault())
                        .FirstOrDefault(path => !string.IsNullOrWhiteSpace(path) && File.Exists(path));

                    return firstPath;
                }
                catch
                {
                    return null;
                }
            }

            private static string? FindExecutableInPath(string executable)
            {
                string? pathEnv = Environment.GetEnvironmentVariable("PATH");
                if (string.IsNullOrWhiteSpace(pathEnv))
                {
                    return null;
                }

                foreach (string path in pathEnv.Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries))
                {
                    string candidate = Path.Combine(path, executable);
                    if (File.Exists(candidate))
                    {
                        return candidate;
                    }
                }

                return null;
            }

            private static PythonRuntimeProbeResult ProbeRuntime(string pythonExecutable)
            {
                string probeScript = @"
import json
import os
import platform
import sys

result = {
    'version': platform.python_version(),
    'prefix': sys.prefix,
    'exe_dir': os.path.dirname(sys.executable),
    'home': sys.prefix,
}

print(json.dumps(result))
";

                ProcessStartInfo psi = new()
                {
                    FileName = pythonExecutable,
                    Arguments = $"-c \"{probeScript.Replace(Environment.NewLine, "\n")}\"",
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true
                };

                using Process process = Process.Start(psi) ?? throw new InvalidOperationException("Failed to probe Python runtime.");
                string stdout = process.StandardOutput.ReadToEnd();
                string stderr = process.StandardError.ReadToEnd();
                process.WaitForExit();

                if (process.ExitCode != 0)
                {
                    throw new PythonInitializationException($"Failed to probe Python runtime. Details: {stderr}");
                }

                try
                {
                    PythonRuntimeProbeResult? result = JsonSerializer.Deserialize<PythonRuntimeProbeResult>(stdout);
                    if (result == null || string.IsNullOrWhiteSpace(result.Version) || string.IsNullOrWhiteSpace(result.HomeDirectory))
                    {
                        throw new PythonInitializationException("Python runtime probe returned incomplete data.");
                    }

                    return result;
                }
                catch (JsonException ex)
                {
                    throw new PythonInitializationException($"Unable to parse Python runtime probe output: {ex.Message}", ex);
                }
            }

            private static Version? ParseVersion(string version)
            {
                if (Version.TryParse(version, out Version? parsed))
                {
                    return parsed;
                }

                return null;
            }

            private static string? ResolvePythonDll(string pythonExecutable, string homeDirectory, Version version)
            {
                if (!OperatingSystem.IsWindows())
                {
                    return null;
                }

                string dllFileName = $"python{version.Major}{version.Minor}.dll";
                string exeDirectory = Path.GetDirectoryName(pythonExecutable) ?? string.Empty;

                string[] candidates =
                [
                    Path.Combine(exeDirectory, dllFileName),
                    Path.Combine(homeDirectory, dllFileName),
                    Path.Combine(homeDirectory, "DLLs", dllFileName),
                    Path.Combine(homeDirectory, "libs", dllFileName)
                ];

                return candidates.FirstOrDefault(File.Exists);
            }

            private sealed class PythonRuntimeProbeResult
            {
                [JsonPropertyName("version")]
                public string Version { get; set; } = string.Empty;

                [JsonPropertyName("home")]
                public string HomeDirectory { get; set; } = string.Empty;
            }
        }

        private sealed class PythonNetBackend : IPythonBackend
        {
            private readonly PythonRuntimeInfo _runtimeInfo;
            private bool _disposed;
            private dynamic? _keyringModule;
            private dynamic? _docIndexerModule;
            private dynamic? _llmModule;
            private dynamic? _docIndexerInstance;
            private dynamic? _helpChatInstance;

            public PythonNetBackend(PythonRuntimeInfo runtimeInfo)
            {
                _runtimeInfo = runtimeInfo;
                InitializePythonRuntime();
            }

            public Dictionary<string, string> SetConfiguration(string configJson)
            {
                EnsureNotDisposed();

                if (_keyringModule == null || _docIndexerModule == null || _llmModule == null)
                {
                    throw new InvalidOperationException("Python modules are not loaded.");
                }

                try
                {
                    using (Py.GIL())
                    {
                        dynamic result = _keyringModule!.KeyRing.build(configJson);

                        _docIndexerInstance = _docIndexerModule!.DocIndexer();
                        _helpChatInstance = _llmModule!.HelpChat(config: result);

                        return ConvertPythonDictToManaged(result);
                    }
                }
                catch (PythonException ex)
                {
                    throw new ConfigurationException($"Failed to set configuration: {ex.Message}", ex);
                }
                catch (Exception ex)
                {
                    throw new ConfigurationException($"Unexpected error setting configuration: {ex.Message}", ex);
                }
            }

            public Dictionary<string, string> SetConfiguration(Dictionary<string, string> config)
            {
                string configJson = JsonSerializer.Serialize(config);
                return SetConfiguration(configJson);
            }

            public void ReIndex(Dictionary<string, string> config, Action<string>? progressCallback)
            {
                EnsureNotDisposed();

                if (_docIndexerInstance == null)
                {
                    throw new InvalidOperationException("Configuration must be set before calling ReIndex.");
                }

                try
                {
                    using (Py.GIL())
                    {
                        using PyDict pyDict = new();
                        foreach (KeyValuePair<string, string> kvp in config)
                        {
                            pyDict[kvp.Key] = kvp.Value.ToPython();
                        }

                        // Note: Progress callback not supported with pythonnet backend
                        // The CLI backend provides progress support
                        _docIndexerInstance!.reindex(config: pyDict);
                    }
                }
                catch (PythonException ex)
                {
                    throw new IndexingException($"Failed to reindex documents: {ex.Message}", ex);
                }
                catch (Exception ex)
                {
                    throw new IndexingException($"Unexpected error during reindexing: {ex.Message}", ex);
                }
            }

            public string MakeRequest(Dictionary<string, string> config, string prompt)
            {
                EnsureNotDisposed();

                if (_helpChatInstance == null)
                {
                    throw new InvalidOperationException("Configuration must be set before calling MakeRequest.");
                }

                try
                {
                    using (Py.GIL())
                    {
                        dynamic response = _helpChatInstance!.make_request(prompt);
                        return response.ToString();
                    }
                }
                catch (PythonException ex)
                {
                    throw new LlmRequestException($"Failed to make LLM request: {ex.Message}", ex);
                }
                catch (Exception ex)
                {
                    throw new LlmRequestException($"Unexpected error during LLM request: {ex.Message}", ex);
                }
            }

            public void Dispose()
            {
                if (_disposed)
                {
                    return;
                }

                try
                {
                    using (Py.GIL())
                    {
                        _keyringModule?.Dispose();
                        _docIndexerModule?.Dispose();
                        _llmModule?.Dispose();
                        _docIndexerInstance?.Dispose();
                        _helpChatInstance?.Dispose();
                    }
                }
                catch
                {
                    // Ignore cleanup failures.
                }

                _disposed = true;
            }

            private void EnsureNotDisposed()
            {
                ObjectDisposedException.ThrowIf(_disposed, nameof(PythonNetBackend));
            }

            private void InitializePythonRuntime()
            {
                if (string.IsNullOrWhiteSpace(_runtimeInfo.DllPath))
                {
                    throw new PythonInitializationException("Python DLL path could not be resolved for pythonnet.");
                }

                try
                {
                    Runtime.PythonDLL = _runtimeInfo.DllPath;
                    PythonEngine.PythonHome = _runtimeInfo.Home;

                    if (!PythonEngine.IsInitialized)
                    {
                        PythonEngine.Initialize();
                    }

                    using (Py.GIL())
                    {
                        AppendDeveloperPythonPath();
                        _keyringModule = Py.Import("help_chat.keyring");
                        _docIndexerModule = Py.Import("help_chat.doc_indexer");
                        _llmModule = Py.Import("help_chat.llm");
                    }
                }
                catch (PythonException ex)
                {
                    throw new PythonInitializationException($"Failed to initialize pythonnet: {ex.Message}", ex);
                }
                catch (Exception ex)
                {
                    throw new PythonInitializationException($"Unexpected error initializing pythonnet: {ex.Message}", ex);
                }
            }

            private static Dictionary<string, string> ConvertPythonDictToManaged(dynamic pyDict)
            {
                Dictionary<string, string> result = [];

                foreach (dynamic key in pyDict.keys())
                {
                    string keyStr = key.ToString();
                    string valueStr = pyDict[key].ToString();
                    result[keyStr] = valueStr;
                }

                return result;
            }

            private static void AppendDeveloperPythonPath()
            {
                string assemblyDirectory = AppContext.BaseDirectory;
                string? repoRoot = TryLocateRepositoryRoot(assemblyDirectory);

                if (repoRoot == null)
                {
                    return;
                }

                string pythonSrc = Path.Combine(repoRoot, "help-chat-python", "src");
                if (!Directory.Exists(pythonSrc))
                {
                    return;
                }

                using (Py.GIL())
                {
                    dynamic sys = Py.Import("sys");
                    sys.path.append(pythonSrc);
                }
            }

        }

        private sealed class PythonCliBackend(PythonRuntimeInfo runtimeInfo) : IPythonBackend
        {
            private readonly PythonRuntimeInfo _runtimeInfo = runtimeInfo;
            private static readonly JsonSerializerOptions _jsonOptions = new()
            {
                PropertyNameCaseInsensitive = true
            };

            public Dictionary<string, string> SetConfiguration(string configJson)
            {
                try
                {
                    Dictionary<string, string> config = JsonSerializer.Deserialize<Dictionary<string, string>>(configJson)
                        ?? throw new ConfigurationException("Configuration JSON could not be parsed.");

                    return SetConfiguration(config);
                }
                catch (JsonException ex)
                {
                    throw new ConfigurationException($"Configuration JSON could not be parsed: {ex.Message}", ex);
                }
            }

            public Dictionary<string, string> SetConfiguration(Dictionary<string, string> config)
            {
                CliCommandResult result = InvokeCli("validate", config, null, null);

                Dictionary<string, string> normalized = result.ReadDictionaryData()
                    ?? throw new ConfigurationException("Python CLI did not return a configuration payload.");

                return normalized;
            }

            public void ReIndex(Dictionary<string, string> config, Action<string>? progressCallback)
            {
                InvokeCli("reindex", config, null, progressCallback);
            }

            public string MakeRequest(Dictionary<string, string> config, string prompt)
            {
                CliCommandResult result = InvokeCli("make-request", config, prompt, null);
                string? response = result.ReadStringData();

                if (string.IsNullOrWhiteSpace(response))
                {
                    throw new LlmRequestException("Python CLI returned an empty response.");
                }

                return response;
            }

            public void Dispose()
            {
                // No unmanaged resources to dispose.
            }

            private CliCommandResult InvokeCli(string command, Dictionary<string, string>? config, string? prompt, Action<string>? progressCallback)
            {
                string? configFile = null;
                string? promptFile = null;

                try
                {
                    ProcessStartInfo psi = new()
                    {
                        FileName = _runtimeInfo.Executable,
                        RedirectStandardOutput = true,
                        RedirectStandardError = true,
                        UseShellExecute = false,
                        CreateNoWindow = true
                    };

                    AppendDevelopmentPythonPath(psi);

                    // Run Python in unbuffered mode so progress messages appear in real-time
                    psi.ArgumentList.Add("-u");
                    psi.ArgumentList.Add("-m");
                    psi.ArgumentList.Add("help_chat.cli");
                    psi.ArgumentList.Add("--command");
                    psi.ArgumentList.Add(command);

                    if (config != null)
                    {
                        configFile = WriteTempJson(config);
                        psi.ArgumentList.Add("--config-file");
                        psi.ArgumentList.Add(configFile);
                    }

                    if (!string.IsNullOrEmpty(prompt))
                    {
                        promptFile = WriteTempText(prompt);
                        psi.ArgumentList.Add("--prompt-file");
                        psi.ArgumentList.Add(promptFile);
                    }

                    using Process process = Process.Start(psi) ?? throw new InvalidOperationException("Failed to start Python process.");

                    StringBuilder stdoutBuilder = new();
                    CliCommandResult? result = null;

                    // Read output line by line to handle progress messages
                    string? line;
                    while ((line = process.StandardOutput.ReadLine()) != null)
                    {
                        // Try to parse as JSON to check if it's a progress message BEFORE adding to builder
                        bool isProgressMessage = false;
                        if (progressCallback != null && line.TrimStart().StartsWith('{'))
                        {
                            try
                            {
                                using JsonDocument doc = JsonDocument.Parse(line);
                                if (doc.RootElement.TryGetProperty("status", out JsonElement statusElement))
                                {
                                    string? status = statusElement.GetString();
                                    if (status == "progress" && doc.RootElement.TryGetProperty("file", out JsonElement fileElement))
                                    {
                                            string? filePath = fileElement.GetString();
                                            if (!string.IsNullOrEmpty(filePath))
                                            {
                                                progressCallback(filePath);
                                                isProgressMessage = true;
                                            }
                                        }
                                }
                            }
                            catch (JsonException ex)
                            {
                                // Not valid JSON or not a progress message, continue
                                System.Diagnostics.Debug.WriteLine($"Failed to parse progress JSON: {ex.Message}");
                            }
                        }

                        // Only add non-progress messages to the output builder
                        if (!isProgressMessage)
                        {
                            stdoutBuilder.AppendLine(line);
                        }
                    }

                    string stderr = process.StandardError.ReadToEnd();
                    process.WaitForExit();

                    string stdout = stdoutBuilder.ToString();
                    string lastLine = stdout.Split('\n', StringSplitOptions.RemoveEmptyEntries).LastOrDefault() ?? string.Empty;

                    if (!string.IsNullOrWhiteSpace(lastLine))
                    {
                        result = JsonSerializer.Deserialize<CliCommandResult>(lastLine, _jsonOptions);
                    }

                    if (process.ExitCode != 0)
                    {
                        throw CreateExceptionFromCli(command, stdout, stderr, result);
                    }

                    if (result == null)
                    {
                        throw CreateExceptionFromCli(command, stdout, stderr, null);
                    }

                    if (!result.IsSuccess)
                    {
                        throw CreateExceptionFromCli(command, stdout, stderr, result);
                    }

                    return result;
                }
                catch (JsonException ex)
                {
                    throw new PythonInitializationException($"Failed to parse CLI output: {ex.Message}", ex);
                }
                catch (Win32Exception ex)
                {
                    throw new PythonInitializationException($"Failed to start Python process: {ex.Message}", ex);
                }
                finally
                {
                    SafeDelete(configFile);
                    SafeDelete(promptFile);
                }
            }

            private static void AppendDevelopmentPythonPath(ProcessStartInfo psi)
            {
                string? repoRoot = TryLocateRepositoryRoot(AppContext.BaseDirectory);
                if (repoRoot == null)
                {
                    return;
                }

                string pythonSrc = Path.Combine(repoRoot, "help-chat-python", "src");
                if (!Directory.Exists(pythonSrc))
                {
                    return;
                }

                string newPythonPath = pythonSrc;
                if (psi.Environment.TryGetValue("PYTHONPATH", out string? existing) && !string.IsNullOrWhiteSpace(existing))
                {
                    newPythonPath = $"{pythonSrc}{Path.PathSeparator}{existing}";
                }

                psi.Environment["PYTHONPATH"] = newPythonPath;

                if (psi.EnvironmentVariables.ContainsKey("PYTHONPATH"))
                {
                    psi.EnvironmentVariables["PYTHONPATH"] = newPythonPath;
                }
                else
                {
                    psi.EnvironmentVariables.Add("PYTHONPATH", newPythonPath);
                }
            }

            private static string WriteTempJson(Dictionary<string, string> payload)
            {
                string path = Path.Combine(Path.GetTempPath(), $"helpchat-config-{Guid.NewGuid():N}.json");
                File.WriteAllText(path, JsonSerializer.Serialize(payload));
                return path;
            }

            private static string WriteTempText(string content)
            {
                string path = Path.Combine(Path.GetTempPath(), $"helpchat-prompt-{Guid.NewGuid():N}.txt");
                File.WriteAllText(path, content, Encoding.UTF8);
                return path;
            }

            private static void SafeDelete(string? path)
            {
                if (string.IsNullOrWhiteSpace(path))
                {
                    return;
                }

                try
                {
                    if (File.Exists(path))
                    {
                        File.Delete(path);
                    }
                }
                catch
                {
                    // Ignore cleanup failures.
                }
            }

            private static Exception CreateExceptionFromCli(string command, string stdout, string stderr, CliCommandResult? result)
            {
                string message = result?.Message ??
                                 (!string.IsNullOrWhiteSpace(stderr) ? stderr.Trim() :
                                     !string.IsNullOrWhiteSpace(stdout) ? stdout.Trim() :
                                     "Unknown Python CLI error.");

                return command switch
                {
                    "validate" => new ConfigurationException(message),
                    "reindex" => new IndexingException(message),
                    "make-request" => new LlmRequestException(message),
                    _ => new PythonInitializationException(message)
                };
            }
        }

        private sealed class CliCommandResult
        {
            [JsonPropertyName("status")]
            public string Status { get; set; } = string.Empty;

            [JsonPropertyName("message")]
            public string? Message { get; set; }

            [JsonPropertyName("data")]
            public JsonElement? Data { get; set; }

            public bool IsSuccess => string.Equals(Status, "ok", StringComparison.OrdinalIgnoreCase);

            public Dictionary<string, string>? ReadDictionaryData()
            {
                if (Data == null || Data.Value.ValueKind != JsonValueKind.Object)
                {
                    return null;
                }

                Dictionary<string, string> result = [];
                foreach (JsonProperty property in Data.Value.EnumerateObject())
                {
                    // Handle different JSON value types properly
                    string value = property.Value.ValueKind switch
                    {
                        JsonValueKind.String => property.Value.GetString() ?? string.Empty,
                        JsonValueKind.Number => property.Value.TryGetInt32(out int intValue)
                            ? intValue.ToString()
                            : property.Value.GetDouble().ToString(),
                        JsonValueKind.True => "true",
                        JsonValueKind.False => "false",
                        JsonValueKind.Null => string.Empty,
                        _ => property.Value.ToString()
                    };
                    result[property.Name] = value;
                }

                return result;
            }

            public string? ReadStringData()
            {
                if (Data == null)
                {
                    return null;
                }

                JsonElement element = Data.Value;
                return element.ValueKind switch
                {
                    JsonValueKind.String => element.GetString(),
                    JsonValueKind.Object when element.TryGetProperty("value", out JsonElement nested) && nested.ValueKind == JsonValueKind.String => nested.GetString(),
                    _ => null
                };
            }
        }

        private static string? TryLocateRepositoryRoot(string startDirectory)
        {
            DirectoryInfo? current = new(startDirectory);

            while (current != null)
            {
                string sentinelPath = Path.Combine(current.FullName, "README.md");
                string pythonDir = Path.Combine(current.FullName, "help-chat-python");
                if (File.Exists(sentinelPath) && Directory.Exists(pythonDir))
                {
                    return current.FullName;
                }

                current = current.Parent;
            }

            return null;
        }
    }
}
