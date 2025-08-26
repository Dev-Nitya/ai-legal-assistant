import os
from langchain.schema import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

# Determine if we should use AWS or local loading
USE_AWS = os.getenv("USE_AWS_S3", "false").lower() == "true"

if USE_AWS:
    print("Using AWS S3 for document storage")

    from chain.aws_loader import AWSDocumentsLoader

    try:
        aws_loadr = AWSDocumentsLoader()
        vectorstore, docs = aws_loadr.get_or_create_vector_store()
        print("AWS S3 document loading successful")
    except Exception as e:
        print(f"Error with AWS loading: {e}")
        print("Falling back to empty vector store")
        
        # Fallback to empty vector store
        embeddings = OpenAIEmbeddings()
        dummy_doc = Document(
            page_content="AWS S3 document loading failed. Please check your AWS configuration.",
            metadata={"source_file": "error", "document_type": "error"}
        )
        vectorstore = Chroma.from_documents(
            documents=[dummy_doc],
            embedding=embeddings,
            persist_directory="/app/chroma_db"
        )
        docs = [dummy_doc]
else:
    print("Using local document storage")
    # Import local loader
    from chain.local_loader import get_or_create_vector_store as local_get_or_create

    try:
        vectorstore, docs = local_get_or_create()
        print("Local document loading successful")
    except Exception as e:
        print(f"Error with local loading: {e}")
        
        # Fallback to empty vector store
        embeddings = OpenAIEmbeddings()
        dummy_doc = Document(
            page_content="Local document loading failed. Please check your documents directory.",
            metadata={"source_file": "error", "document_type": "error"}
        )
        vectorstore = Chroma.from_documents(
            documents=[dummy_doc],
            embedding=embeddings,
            persist_directory="/app/chroma_db"
        )
        docs = [dummy_doc]