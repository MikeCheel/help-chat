namespace HelpChat.Lib.Exceptions
{
    /// <summary>
    /// Base exception class for all HelpChat library exceptions.
    /// </summary>
    public class HelpChatException : Exception
    {
        public HelpChatException()
        {
        }

        public HelpChatException(string message) : base(message)
        {
        }

        public HelpChatException(string message, Exception innerException) : base(message, innerException)
        {
        }
    }
}
