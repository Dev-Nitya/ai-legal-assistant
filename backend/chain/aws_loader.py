import os
import boto3
import hashlib
import json
from pathlib import Path
from typing import List, Optional
from langchain.schema import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv
import tempfile

from chain.utils import metadata_utils

load_dotenv()

class AWSDocumentsLoader:
    def __init__(self):
        self.s3_bucket = os.getenv("AWS_S3_BUCKET")
        self.s3_prefix = os.getenv("AWS_S3_PREFIX", "legal-documents/")
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.chroma_persist_dir = os.getenv("CHROMA_PERSIST_DIR", "/app/chroma_db")
        self.cache_file = os.path.join(self.chroma_persist_dir, "aws_document_cache.json")

        # Initialize AWS clients
        try:
            self.s3_client = boto3.client('s3', region_name=self.aws_region)
            self.s3_resource = boto3.resource('s3', region_name=self.aws_region)
            print(f"AWS S3 client initialized for bucket: {self.s3_bucket}")
        except NoCredentialsError:
            print("Error: AWS credentials not found. Please configure your AWS credentials.")
            raise
        except Exception as e:
            print(f"Error initializing AWS clients: {e}")
            raise

    def list_s3_documents(self) -> List[dict]:
        """List all PDF documents in the S3 bucket"""
        try:
            if not self.s3_bucket:
                print("Error: AWS_S3_BUCKET environment variable is not set.")
                return []
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix=self.s3_prefix,
            )

            pdf_objects = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    if obj['Key'].lower().endswith('.pdf'):
                        pdf_objects.append({
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'].isoformat(),
                            'etag': obj['Etag'].strip('"')
                        })
            
            print(f"Found {len(pdf_objects)} PDF documents in S3")
            return pdf_objects
        except ClientError as e:
            print(f"Error listing S3 objects: {e}")
            return []

    def download_s3_document(self, s3_key: str) -> Optional[str]:
        """Download a document from S3 to a temp file"""
        try:
            # Create a temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_path = temp_file.name
            temp_file.close()

            # Download from S3
            self.s3_client.download_file(self.s3_bucket, s3_key, temp_path)
            print(f"Downloaded {s3_key} to {temp_path}")
            return temp_path
        
        except ClientError as e:
            print(f"Error downloading ${s3_key}: {e}")
            return None
        
    def load_documents_from_s3(self) -> List[Document]:
        """Load and process documents from S3"""
        s3_objects = self.list_s3_documents()

        if not s3_objects:
            print("No documents found in S3")
            return []
        
        all_docs = []
        temp_files = []

        for s3_obj in s3_objects:
            try:
                s3_key = s3_obj['key']
                print(f"Processing {s3_key}...")

                # Download document
                temp_path = self.download_s3_document(s3_key)
                if not temp_path:
                    continue

                temp_files.append(temp_path)

                # Load PDF
                loader = PyPDFLoader(temp_path)
                docs = loader.load()

                # Add metadata
                for doc in docs:
                    enhanced_metadata = metadata_utils.extract_legal_metadata(
                        doc.page_content,
                        Path(s3_key).name
                    )
                    doc.metadata.update(enhanced_metadata)
                    doc.metadata.update({
                        "source_file": Path(s3_key).name,
                        "s3_key": s3_key,
                        "s3_bucket": self.s3_bucket,
                        "document_type": "legal_document",
                        "size": s3_obj['size'],
                        "last_modified": s3_obj['last_modified'],
                        "etag": s3_obj['etag']
                    })

                all_docs.extend(docs)
                print(f"  Loaded {len(docs)} pages from {Path(s3_key).name}")
                
            except Exception as e:
                print(f"Error processing {s3_obj['key']}: {e}")
                continue

        # Clean up temporary files
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except OSError:
                pass

        if not all_docs:
            print("Warning: No documents could be loaded successfully from S3")
            return []
        
        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )

        print(f"Splitting {len(all_docs)} documents into chunks...")
        chunks = text_splitter.split_documents(all_docs)

        print(f"Created {len(chunks)} chunks from {len(all_docs)} documents")
        return chunks
    
    def get_s3_documents_hash(self) -> str:
        """Generate hash of S3 documents for cache validation"""
        s3_objects = self.list_s3_documents()

        if not s3_objects:
            return "empty"
        
        # Create hash based on S3 object ETags and metadata
        hash_data = []
        for obj in sorted(s3_objects, key=lambda x: x['key']):
            hash_data.append(f"{obj['key']}:{obj['etag']}:{obj['last_modified']}")
        
        return hashlib.md5("\n".join(hash_data).encode()).hexdigest()

    def load_cache_metadata(self) -> dict:
        """Load cache metadata"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading cache metadata: {e}")
        return {}
    
    def save_cache_metadata(self, metadata: dict):
        """Save cache metadata"""
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(metadata, f)
        except Exception as e:
            print(f"Error saving cache metadata: {e}")

    def is_cache_valid(self) -> bool:
        """Check if the cached vector store is still valid"""
        if not os.path.exists(self.chroma_persist_dir):
            return False
        
        current_hash = self.get_s3_documents_hash()
        cache_metadata = self.load_cache_metadata()
        
        return cache_metadata.get("s3_documents_hash") == current_hash
    
    def create_vector_store(self, docs: List[Document]):
        """Create vector store from documents"""
        if not docs:
            print("Warning: No documents provided to create vector store")
            # Create a placeholder vector store
            embeddings = OpenAIEmbeddings()
            dummy_doc = Document(
                page_content="No legal documents found in S3. Please upload PDF documents to the configured S3 bucket.",
                metadata={"source_file": "placeholder", "document_type": "placeholder"}
            )
            
            os.makedirs(self.chroma_persist_dir, exist_ok=True)
            vector_store = Chroma.from_documents(
                documents=[dummy_doc],
                embedding=embeddings,
                persist_directory=self.chroma_persist_dir
            )
            
            print("Created vector store with placeholder document")
            return vector_store, [dummy_doc]
        
        try:
            embeddings = OpenAIEmbeddings()
            os.makedirs(self.chroma_persist_dir, exist_ok=True)
            
            vector_store = Chroma.from_documents(
                documents=docs,
                embedding=embeddings,
                persist_directory=self.chroma_persist_dir
            )
            
            # Save cache metadata
            cache_metadata = {
                "s3_documents_hash": self.get_s3_documents_hash(),
                "document_count": len(docs),
                "s3_bucket": self.s3_bucket,
                "s3_prefix": self.s3_prefix,
                "created_at": str(os.path.getctime(self.chroma_persist_dir))
            }
            self.save_cache_metadata(cache_metadata)
            
            print(f"Created and cached vector store with {len(docs)} documents from S3")
            return vector_store, docs
            
        except Exception as e:
            print(f"Error creating vector store: {e}")
            raise

    def get_or_create_vector_store(self):
        """Get existing vector store or create new one from S3"""
        
        # Check if we can load from cache
        if self.is_cache_valid():
            try:
                print("Loading vector store from cache...")
                embeddings = OpenAIEmbeddings()
                vector_store = Chroma(
                    persist_directory=self.chroma_persist_dir,
                    embedding_function=embeddings
                )
                
                cache_metadata = self.load_cache_metadata()
                print(f"Loaded cached vector store with {cache_metadata.get('document_count', 'unknown')} documents")

                # Reload docs for the retriever
                docs = self.load_documents_from_s3()
                return vector_store, docs
                
            except Exception as e:
                print(f"Error loading from cache: {e}")
                print("Creating new vector store from S3...")
        
        # Create new vector store from S3
        print("Loading documents from S3 and creating vector store...")
        docs = self.load_documents_from_s3()
        vector_store, docs = self.create_vector_store(docs)
        
        return vector_store, docs