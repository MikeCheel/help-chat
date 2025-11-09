using Microsoft.Data.Sqlite;
using HelpChat.Lib;
using HelpChat.Lib.Exceptions;
using Microsoft.Extensions.Configuration;

namespace HelpChat.Console
{
    internal class Program
    {
        private static readonly List<string> _conversationHistory = [];
        private static IConfiguration? _configuration;
        private static HelpChatLib? _helpChatLib;
        private static readonly char[] SpinnerChars = ['|', '/', '-', '\\'];
        private static readonly char[] FileProgressSpinnerChars = ['/', '-', '\\', '|'];

        static void Main(string[] args)
        {
            System.Console.WriteLine("=================================");
            System.Console.WriteLine("  HelpChat - Interactive Console");
            System.Console.WriteLine("=================================");
            System.Console.WriteLine();

            try
            {
                // Load configuration from appsettings.json and command line
                LoadConfiguration(args);

                // Display configuration
                DisplayConfiguration();

                // Initialize HelpChat library
                InitializeHelpChat();

                // Display statistics
                DisplayStatistics();

                // Run interactive loop
                InteractiveLoop();
            }
            catch (Exception ex)
            {
                System.Console.ForegroundColor = ConsoleColor.Red;
                System.Console.WriteLine($"Fatal error: {ex.Message}");
                System.Console.WriteLine($"Exception type: {ex.GetType().Name}");
                System.Console.WriteLine($"Stack trace:");
                System.Console.WriteLine(ex.StackTrace);
                if (ex.InnerException != null)
                {
                    System.Console.WriteLine($"Inner exception: {ex.InnerException.Message}");
                    System.Console.WriteLine(ex.InnerException.StackTrace);
                }
                System.Console.ResetColor();
                Environment.Exit(1);
            }
            finally
            {
                _helpChatLib?.Dispose();
            }
        }

        private static void LoadConfiguration(string[] args)
        {
            ConfigurationBuilder builder = new();
            builder.SetBasePath(Directory.GetCurrentDirectory());
            builder.AddJsonFile("appsettings.json", optional: false, reloadOnChange: false);
            builder.AddCommandLine(args);

            _configuration = builder.Build();
        }

        private static void DisplayConfiguration()
        {
            if (_configuration == null)
            {
                return;
            }

            System.Console.WriteLine("Configuration:");
            System.Console.WriteLine($"  Root Path: {_configuration["HelpChat:RootPath"]}");
            System.Console.WriteLine($"  Temp Path: {_configuration["HelpChat:TempPath"]}");
            System.Console.WriteLine($"  API Path: {_configuration["HelpChat:ApiPath"]}");
            System.Console.WriteLine($"  Embeddings Path: {_configuration["HelpChat:EmbeddingsPath"]}");
            System.Console.WriteLine($"  Model Name: {(_configuration["HelpChat:ModelName"] ?? "(auto-detect)")}");
            System.Console.WriteLine($"  Python Path: {(_configuration["HelpChat:PythonPath"] ?? "(system PATH)")}");
            System.Console.WriteLine($"  Conversion Timeout: {(_configuration["HelpChat:ConversionTimeout"] ?? "5")} seconds");
            System.Console.WriteLine($"  Supported Extensions: {(_configuration["HelpChat:SupportedExtensions"] ?? "(defaults)")}");
            System.Console.WriteLine($"  Context Documents: {(_configuration["HelpChat:ContextDocuments"] ?? "5")}");
            System.Console.WriteLine($"  Max Tokens: {(_configuration["HelpChat:MaxTokens"] ?? "2000")}");
            System.Console.WriteLine($"  Temperature: {(_configuration["HelpChat:Temperature"] ?? "0.7")}");
            System.Console.WriteLine($"  Top-P: {(_configuration["HelpChat:TopP"] ?? "0.9")}");
            System.Console.WriteLine($"  LLM Timeout: {(_configuration["HelpChat:Timeout"] ?? "60.0")} seconds");
            System.Console.WriteLine();
        }

        private static void InitializeHelpChat()
        {
            if (_configuration == null)
            {
                throw new InvalidOperationException("Configuration not loaded.");
            }

            System.Console.ForegroundColor = ConsoleColor.Cyan;
            System.Console.Write("Initializing HelpChat library");
            System.Console.ResetColor();

            // Start spinner animation
            var spinnerCts = new CancellationTokenSource();
            var spinnerTask = Task.Run(() => ShowSpinner(spinnerCts.Token));

            try
            {
                string pythonPath = _configuration["HelpChat:PythonPath"] ?? string.Empty;
                _helpChatLib = new HelpChatLib(string.IsNullOrEmpty(pythonPath) ? null : pythonPath);

                string rootPath = _configuration["HelpChat:RootPath"] ?? string.Empty;
                string tempPath = _configuration["HelpChat:TempPath"] ?? string.Empty;
                string apiPath = _configuration["HelpChat:ApiPath"] ?? string.Empty;
                string embeddingsPath = _configuration["HelpChat:EmbeddingsPath"] ?? string.Empty;
                string apiKey = _configuration["HelpChat:ApiKey"] ?? string.Empty;
                string modelName = _configuration["HelpChat:ModelName"] ?? string.Empty;
                int conversionTimeout = int.TryParse(_configuration["HelpChat:ConversionTimeout"], out int timeout) ? timeout : 5;
                string supportedExtensions = _configuration["HelpChat:SupportedExtensions"] ?? string.Empty;
                bool enableDebugLog = bool.TryParse(_configuration["HelpChat:EnableDebugLog"], out bool debugLog) && debugLog;
                int contextDocuments = int.TryParse(_configuration["HelpChat:ContextDocuments"], out int ctxDocs) ? ctxDocs : 5;
                int maxTokens = int.TryParse(_configuration["HelpChat:MaxTokens"], out int maxTok) ? maxTok : 2000;
                double temperature = double.TryParse(_configuration["HelpChat:Temperature"], out double temp) ? temp : 0.7;
                double topP = double.TryParse(_configuration["HelpChat:TopP"], out double tp) ? tp : 0.9;
                double llmTimeout = double.TryParse(_configuration["HelpChat:Timeout"], out double to) ? to : 60.0;

                _helpChatLib.SetConfiguration(
                    rootPath,
                    tempPath,
                    apiPath,
                    embeddingsPath,
                    supportedExtensions,
                    apiKey,
                    modelName,
                    conversionTimeout,
                    embeddingModel: "",
                    enableDebugLog,
                    contextDocuments,
                    maxTokens,
                    temperature,
                    topP,
                    llmTimeout
                );

                // Stop spinner
                spinnerCts.Cancel();
                spinnerTask.Wait(500);
                System.Console.Write("\r" + new string(' ', 50) + "\r");

                System.Console.ForegroundColor = ConsoleColor.Green;
                System.Console.WriteLine("HelpChat initialized successfully.");
                System.Console.ResetColor();
                System.Console.WriteLine();

                PerformInitialReindex(embeddingsPath);
            }
            catch (PythonInitializationException ex)
            {
                // Stop spinner on error
                spinnerCts.Cancel();
                spinnerTask.Wait(500);
                System.Console.Write("\r" + new string(' ', 50) + "\r");

                System.Console.ForegroundColor = ConsoleColor.Red;
                System.Console.WriteLine($"Failed to initialize Python: {ex.Message}");
                System.Console.ResetColor();
                throw;
            }
            catch (ConfigurationException ex)
            {
                // Stop spinner on error
                spinnerCts.Cancel();
                spinnerTask.Wait(500);
                System.Console.Write("\r" + new string(' ', 50) + "\r");

                System.Console.ForegroundColor = ConsoleColor.Red;
                System.Console.WriteLine($"Configuration error: {ex.Message}");
                System.Console.ResetColor();
                throw;
            }
            finally
            {
                spinnerCts.Dispose();
            }
        }

        private static void PerformInitialReindex(string embeddingsPath)
        {
            if (_helpChatLib == null)
            {
                return;
            }

            bool embeddingsExist = File.Exists(embeddingsPath);
            string message = embeddingsExist
                ? "Refreshing embeddings (existing database detected)"
                : "Building embeddings database";

            PerformReindex(message, isInitial: true);

            System.Console.WriteLine();
        }

        private static void DisplayStatistics()
        {
            if (_configuration == null)
            {
                return;
            }

            string embeddingsPath = _configuration["HelpChat:EmbeddingsPath"] ?? string.Empty;

            System.Console.WriteLine("Database Statistics:");
            if (File.Exists(embeddingsPath))
            {
                FileInfo fileInfo = new(embeddingsPath);
                double sizeKB = fileInfo.Length / 1024.0;

                // Get file count from database
                int fileCount = 0;
                try
                {
                    using SqliteConnection connection = CreateSqliteConnection(embeddingsPath);
                    connection.Open();
                    using SqliteCommand command = connection.CreateCommand();
                    command.CommandText = "SELECT COUNT(*) FROM embeddings";
                    object? result = command.ExecuteScalar();
                    if (result != null)
                    {
                        fileCount = Convert.ToInt32(result);
                    }
                }
                catch (Exception)
                {
                    // If we can't read the count, just show 0
                    fileCount = 0;
                }

                System.Console.WriteLine($"  Database: {sizeKB:F2} KB, Files: {fileCount}");
                System.Console.WriteLine($"  Last Modified (UTC): {fileInfo.LastWriteTimeUtc:u}");
            }
            else
            {
                System.Console.WriteLine("  Database does not exist. Run reindex to create it.");
            }

            System.Console.WriteLine();
        }

        private static void InteractiveLoop()
        {
            System.Console.WriteLine("Commands:");
            System.Console.WriteLine("  /help      - Show available commands");
            System.Console.WriteLine("  /history   - Show conversation history");
            System.Console.WriteLine("  /clear     - Clear conversation history");
            System.Console.WriteLine("  /save      - Save conversation to file");
            System.Console.WriteLine("  /list      - Show indexed documents");
            System.Console.WriteLine("  /reindex   - Reindex documents");
            System.Console.WriteLine("  /exit      - Exit application");
            System.Console.WriteLine();
            System.Console.WriteLine("Enter your question or command:");
            System.Console.WriteLine();

            while (true)
            {
                System.Console.Write("> ");
                string? input = System.Console.ReadLine();

                if (string.IsNullOrWhiteSpace(input))
                {
                    continue;
                }

                if (input.StartsWith('/'))
                {
                    HandleCommand(input.ToLower());
                }
                else
                {
                    HandleQuestion(input);
                }
            }
        }

        private static void HandleCommand(string command)
        {
            switch (command)
            {
                case "/help":
                    ShowHelp();
                    break;

                case "/history":
                    ShowHistory();
                    break;

                case "/clear":
                    ClearHistory();
                    break;

                case "/save":
                    SaveHistory();
                    break;

                case "/list":
                    ListIndexedFiles();
                    break;

                case "/reindex":
                    ReindexDocuments();
                    break;

                case "/exit":
                    System.Console.WriteLine("Goodbye!");
                    Environment.Exit(0);
                    break;

                default:
                    System.Console.WriteLine($"Unknown command: {command}. Type /help for available commands.");
                    break;
            }

            System.Console.WriteLine();
        }

        private static void ShowHelp()
        {
            System.Console.WriteLine("Available commands:");
            System.Console.WriteLine("  /help      - Show this help message");
            System.Console.WriteLine("  /history   - Display all conversation messages");
            System.Console.WriteLine("  /clear     - Clear all conversation history");
            System.Console.WriteLine("  /save      - Save conversation to a text file");
            System.Console.WriteLine("  /list      - Show indexed documents");
            System.Console.WriteLine("  /reindex   - Rebuild the document embeddings database");
            System.Console.WriteLine("  /exit      - Exit the application");
        }

        private static void ShowHistory()
        {
            if (_conversationHistory.Count == 0)
            {
                System.Console.WriteLine("No conversation history.");
                return;
            }

            System.Console.WriteLine("Conversation History:");
            System.Console.WriteLine("--------------------");
            foreach (string message in _conversationHistory)
            {
                System.Console.WriteLine(message);
                System.Console.WriteLine();
            }
        }

        private static void ClearHistory()
        {
            _conversationHistory.Clear();
            System.Console.ForegroundColor = ConsoleColor.Green;
            System.Console.WriteLine("Conversation history cleared.");
            System.Console.ResetColor();
        }

        private static void SaveHistory()
        {
            if (_conversationHistory.Count == 0)
            {
                System.Console.WriteLine("No conversation history to save.");
                return;
            }

            string timestamp = DateTime.UtcNow.ToString("yyyyMMdd_HHmmss");
            string filename = $"conversation_{timestamp}.txt";

            try
            {
                File.WriteAllLines(filename, _conversationHistory);
                System.Console.ForegroundColor = ConsoleColor.Green;
                System.Console.WriteLine($"Conversation saved to: {filename}");
                System.Console.ResetColor();
            }
            catch (Exception ex)
            {
                System.Console.ForegroundColor = ConsoleColor.Red;
                System.Console.WriteLine($"Failed to save conversation: {ex.Message}");
                System.Console.ResetColor();
            }
        }

        private static void ListIndexedFiles()
        {
            if (_configuration == null)
            {
                System.Console.WriteLine("Configuration not loaded.");
                return;
            }

            string embeddingsPath = _configuration["HelpChat:EmbeddingsPath"] ?? string.Empty;
            if (string.IsNullOrEmpty(embeddingsPath))
            {
                System.Console.WriteLine("EmbeddingsPath is not configured.");
                return;
            }

            if (!File.Exists(embeddingsPath))
            {
                System.Console.WriteLine("Embeddings database not found. Run /reindex first.");
                return;
            }

            try
            {
                using SqliteConnection connection = CreateSqliteConnection(embeddingsPath, readOnly: true);
                connection.Open();

                using SqliteCommand command = connection.CreateCommand();
                command.CommandText = "SELECT file_path, last_updated FROM embeddings ORDER BY file_path COLLATE NOCASE";

                using SqliteDataReader reader = command.ExecuteReader();

                int count = 0;
                System.Console.WriteLine("Indexed documents:");
                System.Console.WriteLine("------------------");

                while (reader.Read())
                {
                    string filePath = reader.GetString(0);
                    string lastUpdatedRaw = reader.GetString(1);
                    string displayTime = lastUpdatedRaw;
                    if (DateTime.TryParse(lastUpdatedRaw, out DateTime parsed))
                    {
                        displayTime = parsed.ToString("u");
                    }

                    System.Console.WriteLine($"- {filePath} (last updated {displayTime})");
                    count++;
                }

                if (count == 0)
                {
                    System.Console.WriteLine("No documents are currently indexed. Run /reindex to populate the database.");
                }
            }
            catch (Exception ex)
            {
                System.Console.ForegroundColor = ConsoleColor.Red;
                System.Console.WriteLine($"Failed to list indexed documents: {ex.Message}");
                System.Console.ResetColor();
            }
        }

        private static void ReindexDocuments()
        {
            if (_helpChatLib == null)
            {
                System.Console.WriteLine("HelpChat not initialized.");
                return;
            }

            PerformReindex("Reindexing", isInitial: false);
            DisplayStatistics();
        }

        private static SqliteConnection CreateSqliteConnection(string embeddingsPath, bool readOnly = false)
        {
            if (string.IsNullOrWhiteSpace(embeddingsPath))
            {
                throw new InvalidOperationException("EmbeddingsPath is not configured.");
            }

            SqliteConnectionStringBuilder builder = new()
            {
                DataSource = embeddingsPath
            };

            if (readOnly)
            {
                builder.Mode = SqliteOpenMode.ReadOnly;
            }

            return new SqliteConnection(builder.ToString());
        }

        private static void HandleQuestion(string question)
        {
            if (_helpChatLib == null)
            {
                System.Console.WriteLine("HelpChat not initialized.");
                return;
            }

            _conversationHistory.Add($"[{DateTime.UtcNow:yyyy-MM-dd HH:mm:ss} UTC] User: {question}");

            System.Console.WriteLine();
            System.Console.ForegroundColor = ConsoleColor.Cyan;
            System.Console.Write("Thinking");
            System.Console.ResetColor();

            // Start spinner animation in background
            var spinnerCts = new CancellationTokenSource();
            var spinnerTask = Task.Run(() => ShowSpinner(spinnerCts.Token));

            var stopwatch = System.Diagnostics.Stopwatch.StartNew();
            try
            {
                string response = _helpChatLib.MakeRequest(question);
                stopwatch.Stop();

                // Stop spinner
                spinnerCts.Cancel();
                spinnerTask.Wait(500); // Wait briefly for spinner to stop

                // Clear the spinner line
                System.Console.Write("\r" + new string(' ', 50) + "\r");

                _conversationHistory.Add($"[{DateTime.UtcNow:yyyy-MM-dd HH:mm:ss} UTC] Assistant: {response}");

                System.Console.ForegroundColor = ConsoleColor.Green;
                System.Console.WriteLine($"Response (took {stopwatch.ElapsedMilliseconds / 1000.0:F2}s):");
                System.Console.ResetColor();
                System.Console.WriteLine(response);
                System.Console.WriteLine();
            }
            catch (LlmRequestException ex)
            {
                // Stop spinner on error
                spinnerCts.Cancel();
                spinnerTask.Wait(500);
                System.Console.Write("\r" + new string(' ', 50) + "\r");

                System.Console.ForegroundColor = ConsoleColor.Red;
                System.Console.WriteLine($"Request failed: {ex.Message}");
                System.Console.ResetColor();
                System.Console.WriteLine();
            }
            finally
            {
                spinnerCts.Dispose();
            }
        }

        private static void ShowSpinner(CancellationToken cancellationToken)
        {
            int index = 0;

            try
            {
                while (!cancellationToken.IsCancellationRequested)
                {
                    System.Console.ForegroundColor = ConsoleColor.Cyan;
                    System.Console.Write($" {SpinnerChars[index]}");
                    System.Console.ResetColor();
                    index = (index + 1) % SpinnerChars.Length;
                    Thread.Sleep(100);
                    System.Console.Write("\b\b"); // Backspace to overwrite spinner char
                }
            }
            catch (OperationCanceledException)
            {
                // Expected when cancelled
            }
        }

        private static void PerformReindex(string messagePrefix, bool isInitial)
        {
            System.Console.ForegroundColor = ConsoleColor.Cyan;
            System.Console.Write(messagePrefix);
            System.Console.ResetColor();

            // Start spinner animation
            var spinnerCts = new CancellationTokenSource();
            var spinnerTask = Task.Run(() => ShowSpinner(spinnerCts.Token));

            try
            {
                int fileSpinnerIndex = 0;
                int cursorTop = 0;
                bool canUseCursor = false;
                try
                {
                    cursorTop = System.Console.CursorTop;
                    canUseCursor = true;
                }
                catch (IOException)
                {
                    // Console not available (redirected or non-interactive)
                    canUseCursor = false;
                }
                int filesProcessed = 0;

                _helpChatLib!.ReIndex(filePath =>
                {
                    // Stop the initial spinner on first file
                    if (filesProcessed == 0)
                    {
                        spinnerCts.Cancel();
                        spinnerTask.Wait(500);
                        System.Console.Write("\r" + new string(' ', 50) + "\r");
                    }

                    // Display spinner and current file
                    filesProcessed++;
                    fileSpinnerIndex = (fileSpinnerIndex + 1) % FileProgressSpinnerChars.Length;

                    if (canUseCursor)
                    {
                        try
                        {
                            System.Console.SetCursorPosition(0, cursorTop);
                            string progressText = $"Processing [{FileProgressSpinnerChars[fileSpinnerIndex]}] {filePath}";
                            int clearLength = Math.Max(System.Console.WindowWidth - 1, progressText.Length + 10);
                            System.Console.Write(new string(' ', clearLength));
                            System.Console.SetCursorPosition(0, cursorTop);
                            System.Console.Write(progressText);
                        }
                        catch (IOException)
                        {
                            // Cursor positioning failed unexpectedly
                            canUseCursor = false;
                            System.Console.WriteLine($"Processing [{FileProgressSpinnerChars[fileSpinnerIndex]}] {filePath}");
                        }
                        catch (ArgumentOutOfRangeException)
                        {
                            canUseCursor = false;
                            System.Console.WriteLine($"Processing [{FileProgressSpinnerChars[fileSpinnerIndex]}] {Path.GetFileName(filePath)}");
                        }
                    }
                    else
                    {
                        // Non-interactive mode - just output the line
                        System.Console.WriteLine($"Processing [{FileProgressSpinnerChars[fileSpinnerIndex]}] {filePath}");
                    }
                });

                // Stop spinner if no files were processed
                if (filesProcessed == 0)
                {
                    spinnerCts.Cancel();
                    spinnerTask.Wait(500);
                    System.Console.Write("\r" + new string(' ', 50) + "\r");
                }

                if (canUseCursor)
                {
                    try
                    {
                        System.Console.SetCursorPosition(0, cursorTop);
                        System.Console.Write(new string(' ', System.Console.WindowWidth - 1));
                        System.Console.SetCursorPosition(0, cursorTop);
                    }
                    catch (IOException)
                    {
                        // Console no longer supports cursor operations; ignore.
                    }
                    catch (ArgumentOutOfRangeException)
                    {
                        // Window dimensions changed; ignore cleanup.
                    }
                }

                System.Console.ForegroundColor = ConsoleColor.Green;
                if (filesProcessed > 0)
                {
                    string completionMessage = isInitial
                        ? $"Initial reindex completed. Processed {filesProcessed} file(s)."
                        : $"Reindexing completed successfully. Processed {filesProcessed} file(s).";
                    System.Console.WriteLine(completionMessage);
                }
                else
                {
                    string completionMessage = isInitial
                        ? "Initial reindex completed. No files needed processing (all up to date)."
                        : "Reindexing completed successfully. No files needed processing (all up to date).";
                    System.Console.WriteLine(completionMessage);
                }
                System.Console.ResetColor();
            }
            catch (Exception ex)
            {
                spinnerCts.Cancel();
                spinnerTask.Wait(500);
                System.Console.Write("\r" + new string(' ', 50) + "\r");

                System.Console.ForegroundColor = ConsoleColor.Red;
                string errorMessage = isInitial
                    ? $"Initial reindex failed: {ex.Message}"
                    : $"Reindex failed: {ex.Message}";
                System.Console.WriteLine(errorMessage);
                System.Console.ResetColor();

                if (isInitial)
                {
                    throw;
                }
            }
            finally
            {
                spinnerCts.Dispose();
            }
        }
    }
}
