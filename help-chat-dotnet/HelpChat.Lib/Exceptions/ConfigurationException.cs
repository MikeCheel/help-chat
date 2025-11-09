namespace HelpChat.Lib.Exceptions
{
    /// <summary>
    /// Exception thrown when configuration is invalid or missing required fields.
    /// </summary>
    public class ConfigurationException : HelpChatException
    {
        public ConfigurationException()
        {
        }

        public ConfigurationException(string message) : base(message)
        {
        }

        public ConfigurationException(string message, Exception innerException) : base(message, innerException)
        {
        }
    }
}
