namespace HelpChat.Lib.Exceptions
{
    /// <summary>
    /// Exception thrown when document indexing fails.
    /// </summary>
    public class IndexingException : HelpChatException
    {
        public IndexingException()
        {
        }

        public IndexingException(string message) : base(message)
        {
        }

        public IndexingException(string message, Exception innerException) : base(message, innerException)
        {
        }
    }
}
