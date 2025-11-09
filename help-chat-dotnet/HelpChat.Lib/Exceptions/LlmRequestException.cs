namespace HelpChat.Lib.Exceptions
{
    /// <summary>
    /// Exception thrown when an LLM request fails.
    /// </summary>
    public class LlmRequestException : HelpChatException
    {
        public LlmRequestException()
        {
        }

        public LlmRequestException(string message) : base(message)
        {
        }

        public LlmRequestException(string message, Exception innerException) : base(message, innerException)
        {
        }
    }
}
