using HelpChat.Lib.Exceptions;

namespace HelpChat.Lib.Tests
{
    /// <summary>
    /// Unit tests for custom exception classes.
    /// </summary>
    public class ExceptionTests
    {
        [Fact]
        public void HelpChatException_DefaultConstructor_CreatesInstance()
        {
            // Act
            HelpChatException exception = new();

            // Assert
            Assert.NotNull(exception);
            Assert.IsType<HelpChatException>(exception);
        }

        [Fact]
        public void HelpChatException_WithMessage_StoresMessage()
        {
            // Arrange
            string message = "Test error message";

            // Act
            HelpChatException exception = new(message);

            // Assert
            Assert.Equal(message, exception.Message);
        }

        [Fact]
        public void HelpChatException_WithMessageAndInnerException_StoresBoth()
        {
            // Arrange
            string message = "Test error message";
            Exception innerException = new("Inner exception");

            // Act
            HelpChatException exception = new(message, innerException);

            // Assert
            Assert.Equal(message, exception.Message);
            Assert.Equal(innerException, exception.InnerException);
        }

        [Fact]
        public void PythonInitializationException_DefaultConstructor_CreatesInstance()
        {
            // Act
            PythonInitializationException exception = new();

            // Assert
            Assert.NotNull(exception);
            Assert.IsType<PythonInitializationException>(exception);
            Assert.IsAssignableFrom<HelpChatException>(exception);
        }

        [Fact]
        public void PythonInitializationException_WithMessage_StoresMessage()
        {
            // Arrange
            string message = "Python initialization failed";

            // Act
            PythonInitializationException exception = new(message);

            // Assert
            Assert.Equal(message, exception.Message);
        }

        [Fact]
        public void ConfigurationException_DefaultConstructor_CreatesInstance()
        {
            // Act
            ConfigurationException exception = new();

            // Assert
            Assert.NotNull(exception);
            Assert.IsType<ConfigurationException>(exception);
            Assert.IsAssignableFrom<HelpChatException>(exception);
        }

        [Fact]
        public void ConfigurationException_WithMessage_StoresMessage()
        {
            // Arrange
            string message = "Configuration is invalid";

            // Act
            ConfigurationException exception = new(message);

            // Assert
            Assert.Equal(message, exception.Message);
        }

        [Fact]
        public void IndexingException_DefaultConstructor_CreatesInstance()
        {
            // Act
            IndexingException exception = new();

            // Assert
            Assert.NotNull(exception);
            Assert.IsType<IndexingException>(exception);
            Assert.IsAssignableFrom<HelpChatException>(exception);
        }

        [Fact]
        public void IndexingException_WithMessage_StoresMessage()
        {
            // Arrange
            string message = "Indexing operation failed";

            // Act
            IndexingException exception = new(message);

            // Assert
            Assert.Equal(message, exception.Message);
        }

        [Fact]
        public void LlmRequestException_DefaultConstructor_CreatesInstance()
        {
            // Act
            LlmRequestException exception = new();

            // Assert
            Assert.NotNull(exception);
            Assert.IsType<LlmRequestException>(exception);
            Assert.IsAssignableFrom<HelpChatException>(exception);
        }

        [Fact]
        public void LlmRequestException_WithMessage_StoresMessage()
        {
            // Arrange
            string message = "LLM request failed";

            // Act
            LlmRequestException exception = new(message);

            // Assert
            Assert.Equal(message, exception.Message);
        }
    }
}
