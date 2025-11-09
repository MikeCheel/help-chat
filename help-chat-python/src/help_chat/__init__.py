"""
Help Chat Python Package

A package for document indexing, vector embeddings, and LLM-based help chat with RAG support.
"""

from help_chat.keyring import KeyRing
from help_chat.doc_indexer import DocIndexer
from help_chat.llm import HelpChat

__version__ = "0.1.0"
__all__ = ["KeyRing", "DocIndexer", "HelpChat"]
