namespace HelpChat.Lib.Exceptions
{
    /// <summary>
    /// Exception thrown when Python environment initialization fails.
    /// </summary>
    public class PythonInitializationException : HelpChatException
    {
        public PythonInitializationException()
        {
        }

        public PythonInitializationException(string message) : base(message)
        {
        }

        public PythonInitializationException(string message, Exception innerException) : base(message, innerException)
        {
        }
    }
}
