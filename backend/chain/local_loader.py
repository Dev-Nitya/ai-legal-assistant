from datetime import datetime
import os
import hashlib
import json
from pathlib import Path
from typing import List
from langchain.schema import Document
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from chain.utils import metadata_utils
from config.settings import settings

# Configuration
DOCUMENTS_DIR = os.getenv("DOCUMENTS_DIR", "/app/documents")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "/app/chroma_db")
CACHE_FILE = os.path.join(CHROMA_PERSIST_DIR, "document_cache.json")

def discover_documents() -> List[str]:
    """Discover PDF documents in the documents directory and subdirectories"""
    documents_path = Path(DOCUMENTS_DIR)

    if not documents_path.exists():
        print(f"Warning: Documents directory {DOCUMENTS_DIR} does not exist")
        return []
    
    # Find all PDF files recursively
    pdf_files = list(documents_path.rglob("*.pdf"))
    if not pdf_files:
        print(f"Warning: No PDF files found in {DOCUMENTS_DIR}")
        return []
    
    print(f"Discovered {len(pdf_files)} PDF files.")
    for pdf_file in pdf_files:
        print(f" - {pdf_file}")

    return [str(pdf_file) for pdf_file in pdf_files]

def load_documents() -> List[Document]:
    """Load and process documents from the documents directory"""
    pdf_files = discover_documents()
    if not pdf_files:
        print("No documents found. Creating empty document list.")
        return []
    
    all_docs = []
    
    for pdf_file in pdf_files:
        try:
            print(f"Loading document: {pdf_file}")
            loader = PyPDFLoader(pdf_file)
            docs = loader.load()

            # Add metadata
            for doc in docs:
                enhanced_metadata = metadata_utils.extract_legal_metadata(
                    doc.page_content,
                    Path(pdf_file).name
                )
                doc.metadata.update(enhanced_metadata)
            all_docs.extend(docs)
            print(f"Loaded {len(docs)} pages from {pdf_file}")
        except Exception as e:
            print(f"Error loading {pdf_file}: {e}")
            continue

    if not all_docs:
        print("Warning: No documents were loaded successfully.")
        return []
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )

    print(f"Splitting {len(all_docs)} documents into chunks...")
    chunks = text_splitter.split_documents(all_docs)

    print(f"Created {len(chunks)} chunks from documents.")
    return chunks

def get_document_hash() -> str:
    """Generate a hash of all documents for cache validaton"""
    pdf_files = discover_documents()

    if not pdf_files:
        return "empty"
    
    # Create a hash based on file paths and modification times
    hash_data = []
    for pdf_file in pdf_files:
        try:
            stat = os.stat(pdf_file)
            hash_data.append(f"{pdf_file}:{stat.st_mtime}:{stat.st_size}")
        except OSError:
            continue

    return hashlib.md5("\n".join(hash_data).encode()).hexdigest()

def load_cache_metadata() -> dict:
    """Load cache metadata"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading cache metadata: {e}")
    return {}

def save_cache_metadata(metadata: dict):
    """Save cache metadata"""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(metadata, f)
    except Exception as e:
        print(f"Error saving cache metadata: {e}")

def is_cache_valid() -> bool:
    """Check if the cached vector store is still valid"""
    if not os.path.exists(CHROMA_PERSIST_DIR):
        return False
    
    current_hash = get_document_hash()
    cache_metadata = load_cache_metadata()

    return cache_metadata.get("doc_hash") == current_hash

def create_vector_store(docs: List[Document]):
    """Create vector store from documents"""
    if not docs:
        print("Warning: No documents provided for vector store creation.")
        # Create an empty vector store that can be used
        embeddings = OpenAIEmbeddings(api_key=settings.openai_api_key)

        # Create a minimal document to initialize the vector store
        dummy_doc = Document(
            page_content="This is a placeholder document. No legal documents were found.",
            metadata={"source_file": "placeholder", "document_type": "placeholder"}
        )

        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
        vector_store = Chroma.from_documents(
            documents=[dummy_doc],
            embedding=embeddings,
            persist_directory=CHROMA_PERSIST_DIR
        )

        print("Created vector store with placeholder document")
        return vector_store, [dummy_doc]
    
    try:
        embeddings = OpenAIEmbeddings(api_key=settings.openai_api_key)
        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

        vector_store = Chroma.from_documents(
            documents=docs,
            embedding=embeddings,
            persist_directory=CHROMA_PERSIST_DIR
        )

        cache_metadata = {
            "document_hash": get_document_hash(),
            "document_count": len(docs),
            "created_at": datetime.utcnow().isoformat()
        }
        save_cache_metadata(cache_metadata)

        print(f"Created and cached vector store with {len(docs)} documents.")
        return vector_store, docs
    
    except Exception as e:
        print(f"Error creating vector store in local loader: {e}")
        raise

def get_or_create_vector_store():
    """Get existing vector store or create new one"""

    # Check if we can load from cache
    if is_cache_valid():
        try:
            print("Loading vector store from cache...")
            embeddings = OpenAIEmbeddings(api_key=settings.openai_api_key)
            vector_store = Chroma(
                embedding_function=embeddings,
                persist_directory=CHROMA_PERSIST_DIR
            )

            # Load document list from cache
            cache_metadata = load_cache_metadata()
            print(f"Loaded cached vector store with {cache_metadata.get('document_count', 'unknown')} documents")
            
            # We need to reload docs for the retriever
            docs = load_documents()
            return vector_store, docs
        except Exception as e:
            print(f"Error loading from cache: {e}")
            print("Creating new vector store...")

    # Create new vector store
    print("Creating new vector store...")
    docs = load_documents()
    vector_store, docs = create_vector_store(docs)

    return vector_store, docs