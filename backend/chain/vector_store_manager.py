import threading
from typing import Tuple, List, Optional
from langchain.schema import Document
from langchain_chroma import Chroma

class VectorStoreManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._vectorstore = None
        self._docs = None
        self._initialized = True
    
    def get_vector_store(self) -> Tuple[Chroma, List[Document]]:
        if self._vectorstore is None:
            with self._lock:
                if self._vectorstore is None:
                    self._load_vector_store()
        return self._vectorstore, self._docs
    
    def _load_vector_store(self):
        import os
        from config.settings import settings

        use_aws = False
        if settings and settings.is_production and settings.documents_bucket:
            use_aws = True
        else:
            use_aws = os.getenv("USE_AWS_S3", "false").lower() == "true"
        
        if use_aws:
            from chain.aws_loader import AWSDocumentsLoader
            loader = AWSDocumentsLoader()
            self._vectorstore, self._docs = loader.get_or_create_vector_store()
            print("✅ AWS S3 document loading successful")
        else:
            from chain.local_loader import get_or_create_vector_store
            self._vectorstore, self._docs = get_or_create_vector_store()
            print("✅ Local document loading successful")

# Global functions
def get_vector_store() -> Tuple[Chroma, List[Document]]:
    return VectorStoreManager().get_vector_store()