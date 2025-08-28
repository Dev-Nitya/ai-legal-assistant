"""
Main loader module using Singleton pattern for vector store management.
This ensures vector store is loaded only once regardless of import frequency.
"""

from chain.vector_store_manager import get_vector_store

# Get the vector store through singleton manager
vectorstore, docs = get_vector_store()

print("📚 Vector Store loaded successfully")