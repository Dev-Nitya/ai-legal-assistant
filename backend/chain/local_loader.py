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
import re
from collections import defaultdict

from chain.utils import metadata_utils
from config.settings import settings
from config.secrets import secrets_manager

# Configuration
BACKEND_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_DIR = os.getenv("DOCUMENTS_DIR", str(BACKEND_ROOT / "documents"))
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(BACKEND_ROOT / "chroma_db"))
CACHE_FILE = os.path.join(CHROMA_PERSIST_DIR, "document_cache.json")

def resolve_openai_key():
        """Resolve OpenAI API key: env -> settings -> Secrets Manager.
        Secrets Manager value is expected to be a plain string (not JSON)."""
        # 1) Environment variable
        key = os.getenv("OPENAI_API_KEY")
        if key:
            return key

        # 2) settings attribute
        key = getattr(settings, "openai_api_key", None)
        if key:
            return key

        # 3) Secrets Manager (assume plain string)
        secret = secrets_manager.get_secret("openai_api_key", "OPENAI_API_KEY")
        if secret:
            return secret
        
        return None

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
                enhanced_metadata = metadata_utils.sanitize_extracted_metadata(enhanced_metadata)
                
                doc.metadata.update(enhanced_metadata)
            all_docs.extend(docs)
            print(f"Loaded {len(docs)} pages from {pdf_file}")
        except Exception as e:
            print(f"Error loading {pdf_file}: {e}")
            continue

    if not all_docs:
        print("Warning: No documents were loaded successfully.")
        return []
    
    # --- Ingestion aggregation: compute per-PDF union of sections/acts and attach to every page ---
    aggregate_sections = defaultdict(set)
    aggregate_acts = defaultdict(set)

    for d in all_docs:
        src = d.metadata.get("source_file") or d.metadata.get("source")
        
        raw_sections = d.metadata.get("extracted_sections_norm") or d.metadata.get("extracted_sections") or []
        if isinstance(raw_sections, str):
            section_parts = re.split(r'\s*(?:,|;|\||/|and)\s*', raw_sections)
        else:
            section_parts = raw_sections
        
        for s in section_parts:
            token = re.sub(r'[^0-9a-z]', '', str(s or "").lower())
            if token:
                aggregate_sections[src].add(token)
        
        raw_acts = d.metadata.get("extracted_acts_norm") or d.metadata.get("extracted_acts") or []
        if isinstance(raw_acts, str):
            act_parts = re.split(r'\s*(?:,|;|\||/|and)\s*', raw_acts)
        else:
            act_parts = raw_acts
        for a in act_parts:
            token = re.sub(r'[^0-9a-z_]', '', str(a or "").lower().replace(' ', '_'))
            if token:
                aggregate_acts[src].add(token)

    # Attach aggregated normalized lists to every page of the same PDF
    for d in all_docs:
        src = d.metadata.get("source_file") or d.metadata.get("source")
        d.metadata["aggregated_extracted_sections_norm"] = sorted(list(aggregate_sections.get(src, [])))
        d.metadata["aggregated_extracted_acts_norm"] = sorted(list(aggregate_acts.get(src, [])))
    # --- end aggregation ---

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
        json_to_save = {
            "doc_hash": metadata.get("doc_hash") or metadata.get("document_hash") or "",
            "document_count": metadata.get("document_count", 0),
            "created_at": metadata.get("created_at")
        }
        with open(CACHE_FILE, "w") as f:
           json.dump(json_to_save, f)
    except Exception as e:
        print(f"Error saving cache metadata: {e}")

def is_cache_valid() -> bool:    
    current_hash = get_document_hash()
    cache_metadata = load_cache_metadata()

    return cache_metadata.get("doc_hash") == current_hash

def create_vector_store(docs: List[Document]):
    """Create vector store from documents"""
    openai_key = resolve_openai_key()
    if not docs:
        # Create a minimal document to initialize the vector store
        dummy_doc = Document(
            page_content="This is a placeholder document. No legal documents were found.",
            metadata={"source_file": "placeholder", "document_type": "placeholder"}
        )

        if not openai_key:
            print("No OpenAI key available — returning placeholder document without embeddings/vector store")
            return None, [dummy_doc]
        
        print("Warning: No documents provided for vector store creation.")
        # Create an empty vector store that can be used
        embeddings = OpenAIEmbeddings(api_key=openai_key)

        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

        vector_store = Chroma.from_documents(
            documents=dummy_doc,
            embedding=embeddings,
            persist_directory=CHROMA_PERSIST_DIR
        )

        print("Created vector store with placeholder document")
        return vector_store, [dummy_doc]
    
    try:
        if not openai_key:
            raise RuntimeError(
                "OpenAI API key not found. Set OPENAI_API_KEY env var or ensure secret "
                "ai-legal-assistant-openai_api_key-<env> exists and is readable by the task role."
            )
        embeddings = OpenAIEmbeddings(api_key=openai_key)
        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

         # Chroma requires primitive metadata types. Create a separate list of Documents
        # with serialized metadata for storage, but keep original 'docs' intact for runtime.
        docs_for_store = []
        for d in docs:
            # Make a shallow copy of metadata then serialize
            meta_copy = dict(d.metadata or {})
            meta_serial = metadata_utils.serialize_metadata_for_storage(meta_copy)
            docs_for_store.append(Document(page_content=d.page_content, metadata=meta_serial))

        vector_store = Chroma.from_documents(
            documents=docs_for_store,
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
            print("Cache is valid, loading vector store from cache...")
            openai_key = resolve_openai_key()
            if not openai_key:
                raise RuntimeError(
                    "OpenAI API key not found. Set OPENAI_API_KEY env var or ensure secret "
                    "ai-legal-assistant-openai_api_key-<env> exists and is readable by the task role."
                )
            print("Loading vector store from cache...")
            embeddings = OpenAIEmbeddings(api_key=openai_key)
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