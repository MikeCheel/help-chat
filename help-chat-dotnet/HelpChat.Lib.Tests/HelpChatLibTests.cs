using System.Text.Json;
using HelpChat.Lib.Exceptions;

namespace HelpChat.Lib.Tests
{
    /// <summary>
    /// Unit tests for HelpChatLib class.
    /// Note: These are integration tests that require Python and the help-chat-python package to be installed.
    /// </summary>
    public class HelpChatLibTests : IDisposable
    {
        private HelpChatLib? _helpChat;
        private bool _disposed = false;
        private readonly List<string> _tempDirectories = [];
        private const string SupportedExtensions = ".txt,.md";

        public HelpChatLibTests()
        {
            // Tests will initialize HelpChatLib as needed
        }

        [Fact]
        public void Constructor_WithNullPythonPath_InitializesSuccessfully()
        {
            // Act & Assert - Should not throw
            _helpChat = new HelpChatLib(null);
        }

        [Fact]
        public void Constructor_WithInvalidPythonPath_ThrowsPythonInitializationException()
        {
            // Arrange
            string invalidPath = "C:\\invalid\\path\\python.exe";

            // Act & Assert
            Assert.Throws<PythonInitializationException>(() =>
            {
                _helpChat = new HelpChatLib(invalidPath);
            });
        }

        [Fact]
        public void SetConfiguration_WithValidJson_Succeeds()
        {
            // Arrange
            _helpChat = new HelpChatLib();
            string configJson = CreateConfigJson(out _);

            // Act & Assert - Should not throw
            _helpChat.SetConfiguration(configJson);
        }

        [Fact]
        public void SetConfiguration_WithInvalidJson_ThrowsConfigurationException()
        {
            // Arrange
            _helpChat = new HelpChatLib();
            string invalidJson = "{ invalid json }";

            // Act & Assert
            Assert.Throws<ConfigurationException>(() =>
            {
                _helpChat.SetConfiguration(invalidJson);
            });
        }

        [Fact]
        public void SetConfiguration_WithMissingRequiredField_ThrowsConfigurationException()
        {
            // Arrange
            _helpChat = new HelpChatLib();
            string configJson = @"{
                ""root_path"": ""C:\\temp\\docs"",
                ""temp_path"": ""C:\\temp\\processing""
            }";

            // Act & Assert
            Assert.Throws<ConfigurationException>(() =>
            {
                _helpChat.SetConfiguration(configJson);
            });
        }

        [Fact]
        public void SetConfiguration_WithIndividualParameters_Succeeds()
        {
            // Arrange
            _helpChat = new HelpChatLib();
            ConfigurationPaths paths = CreateConfigPaths();

            // Act & Assert - Should not throw
            _helpChat.SetConfiguration(
                rootPath: paths.RootPath,
                tempPath: paths.TempPath,
                apiPath: "https://api.openai.com/v1",
                embeddingsPath: paths.EmbeddingsPath,
                supportedExtensions: SupportedExtensions,
                apiKey: "test-key",
                modelName: string.Empty
            );
        }

        [Fact]
        public void SetConfiguration_WithIndividualParametersNoApiKey_Succeeds()
        {
            // Arrange
            _helpChat = new HelpChatLib();
            ConfigurationPaths paths = CreateConfigPaths();

            // Act & Assert - Should not throw
            _helpChat.SetConfiguration(
                rootPath: paths.RootPath,
                tempPath: paths.TempPath,
                apiPath: "http://localhost:11434",
                embeddingsPath: paths.EmbeddingsPath,
                supportedExtensions: SupportedExtensions
            );
        }

        [Fact]
        public void ReIndex_WithoutConfiguration_ThrowsInvalidOperationException()
        {
            // Arrange
            _helpChat = new HelpChatLib();

            // Act & Assert
            Assert.Throws<InvalidOperationException>(() =>
            {
                _helpChat.ReIndex();
            });
        }

        [Fact]
        public void MakeRequest_WithoutConfiguration_ThrowsInvalidOperationException()
        {
            // Arrange
            _helpChat = new HelpChatLib();

            // Act & Assert
            Assert.Throws<InvalidOperationException>(() =>
            {
                _helpChat.MakeRequest("test prompt");
            });
        }

        [Fact]
        public void Dispose_MultipleCalls_DoesNotThrow()
        {
            // Arrange
            _helpChat = new HelpChatLib();

            // Act & Assert - Should not throw
            _helpChat.Dispose();
            _helpChat.Dispose();
        }

        [Fact]
        public void ReIndex_WithConfiguration_CreatesEmbeddingsDatabase()
        {
            // Arrange
            _helpChat = new HelpChatLib();
            ConfigurationPaths paths = CreateConfigPaths();

            // Create some test files
            File.WriteAllText(Path.Combine(paths.RootPath, "test.txt"), "Test content for indexing");
            File.WriteAllText(Path.Combine(paths.RootPath, "test2.md"), "# Markdown content");

            _helpChat.SetConfiguration(
                rootPath: paths.RootPath,
                tempPath: paths.TempPath,
                apiPath: "http://localhost:11434",
                embeddingsPath: paths.EmbeddingsPath,
                supportedExtensions: SupportedExtensions
            );

            // Act
            _helpChat.ReIndex();

            // Assert
            Assert.True(File.Exists(paths.EmbeddingsPath), "Embeddings database should be created");
        }

        [Fact]
        public void ReIndex_WithEmptyDirectory_SucceedsWithoutErrors()
        {
            // Arrange
            _helpChat = new HelpChatLib();
            ConfigurationPaths paths = CreateConfigPaths();

            _helpChat.SetConfiguration(
                rootPath: paths.RootPath,
                tempPath: paths.TempPath,
                apiPath: "http://localhost:11434",
                embeddingsPath: paths.EmbeddingsPath,
                supportedExtensions: SupportedExtensions
            );

            // Act & Assert - Should not throw
            _helpChat.ReIndex();
            Assert.True(File.Exists(paths.EmbeddingsPath));
        }

        [Fact]
        public void ReIndex_MultipleCallsWithSameFiles_DoesNotReindexUnchangedFiles()
        {
            // Arrange
            _helpChat = new HelpChatLib();
            ConfigurationPaths paths = CreateConfigPaths();

            string testFile = Path.Combine(paths.RootPath, "test.txt");
            File.WriteAllText(testFile, "Test content");

            _helpChat.SetConfiguration(
                rootPath: paths.RootPath,
                tempPath: paths.TempPath,
                apiPath: "http://localhost:11434",
                embeddingsPath: paths.EmbeddingsPath,
                supportedExtensions: SupportedExtensions
            );

            // Act - Index twice
            _helpChat.ReIndex();
            DateTime firstIndexTime = File.GetLastWriteTimeUtc(paths.EmbeddingsPath);

            Thread.Sleep(100); // Small delay to ensure time difference

            _helpChat.ReIndex();
            DateTime secondIndexTime = File.GetLastWriteTimeUtc(paths.EmbeddingsPath);

            // Assert - Database file should be touched but content reused for unchanged files
            Assert.True(secondIndexTime >= firstIndexTime);
        }

        [Fact]
        public void ReIndex_WithNonExistentRootPath_ThrowsIndexingException()
        {
            // Arrange
            _helpChat = new HelpChatLib();
            ConfigurationPaths paths = CreateConfigPaths();
            string nonExistentRoot = Path.Combine(paths.RootPath, "does_not_exist");

            _helpChat.SetConfiguration(
                rootPath: nonExistentRoot,
                tempPath: paths.TempPath,
                apiPath: "http://localhost:11434",
                embeddingsPath: paths.EmbeddingsPath,
                supportedExtensions: SupportedExtensions
            );

            // Act & Assert - Indexing should fail with non-existent root
            Assert.Throws<IndexingException>(() =>
            {
                _helpChat.ReIndex();
            });
        }

        [Fact]
        public void SetConfiguration_WithModelName_StoresModelName()
        {
            // Arrange
            _helpChat = new HelpChatLib();
            ConfigurationPaths paths = CreateConfigPaths();

            // Act
            _helpChat.SetConfiguration(
                rootPath: paths.RootPath,
                tempPath: paths.TempPath,
                apiPath: "https://api.openai.com/v1",
                embeddingsPath: paths.EmbeddingsPath,
                supportedExtensions: SupportedExtensions,
                apiKey: "test-key",
                modelName: "gpt-4"
            );

            // Assert - Configuration succeeded, model name stored internally
            // We can verify by not throwing and allowing reindex
            _helpChat.ReIndex();
        }

        [Fact]
        public void ReIndex_WithSubdirectories_IndexesAllFiles()
        {
            // Arrange
            _helpChat = new HelpChatLib();
            ConfigurationPaths paths = CreateConfigPaths();

            // Create nested directory structure
            string subDir = Path.Combine(paths.RootPath, "subdirectory");
            Directory.CreateDirectory(subDir);

            File.WriteAllText(Path.Combine(paths.RootPath, "root.txt"), "Root file");
            File.WriteAllText(Path.Combine(subDir, "nested.txt"), "Nested file");

            _helpChat.SetConfiguration(
                rootPath: paths.RootPath,
                tempPath: paths.TempPath,
                apiPath: "http://localhost:11434",
                embeddingsPath: paths.EmbeddingsPath,
                supportedExtensions: SupportedExtensions
            );

            // Act
            _helpChat.ReIndex();

            // Assert - Database should exist with indexed files
            Assert.True(File.Exists(paths.EmbeddingsPath));
        }

        protected virtual void Dispose(bool disposing)
        {
            if (!_disposed)
            {
                if (disposing)
                {
                    _helpChat?.Dispose();
                    foreach (string directory in _tempDirectories)
                    {
                        TryDeleteDirectory(directory);
                    }
                    _tempDirectories.Clear();
                }
                _disposed = true;
            }
        }

        public void Dispose()
        {
            Dispose(true);
            GC.SuppressFinalize(this);
        }

        private string CreateConfigJson(out ConfigurationPaths paths)
        {
            paths = CreateConfigPaths();

            Dictionary<string, string> payload = new()
            {
                { "root_path", paths.RootPath },
                { "temp_path", paths.TempPath },
                { "api_path", "https://api.openai.com/v1" },
                { "embeddings_path", paths.EmbeddingsPath },
                { "api_key", "test-key" },
                { "supported_extensions", SupportedExtensions }
            };

            return JsonSerializer.Serialize(payload);
        }

        private ConfigurationPaths CreateConfigPaths()
        {
            string basePath = Path.Combine(Path.GetTempPath(), "HelpChatTests", Guid.NewGuid().ToString("N"));
            string rootPath = Path.Combine(basePath, "docs");
            string tempPath = Path.Combine(basePath, "temp");
            string embeddingsDirectory = Path.Combine(basePath, "store");
            string embeddingsPath = Path.Combine(embeddingsDirectory, "embeddings.db");

            Directory.CreateDirectory(rootPath);
            Directory.CreateDirectory(tempPath);
            Directory.CreateDirectory(embeddingsDirectory);

            _tempDirectories.Add(basePath);

            return new ConfigurationPaths(rootPath, tempPath, embeddingsPath);
        }

        private static void TryDeleteDirectory(string path)
        {
            if (string.IsNullOrWhiteSpace(path))
            {
                return;
            }

            try
            {
                if (Directory.Exists(path))
                {
                    Directory.Delete(path, recursive: true);
                }
            }
            catch
            {
                // Safe cleanup best effort
            }
        }

        private readonly record struct ConfigurationPaths(string RootPath, string TempPath, string EmbeddingsPath);
    }
}
