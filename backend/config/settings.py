import os
import logging
from typing import Optional

from config.secrets import secrets_manager

logger = logging.getLogger(__name__)

class Settings:
    """
    Smart settings that adapt to environment
    """
    
    def __init__(self):
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.is_production = self.environment == 'production'
        
        # Basic app settings
        self.app_name = "AI Legal Assistant"
        self.debug = not self.is_production
        
    # DATABASE SETTINGS
    @property
    def database_url(self) -> str:
        """
        Get database connection URL
        
        FLOW:
        Development → sqlite:///./ai_legal_assistant.db
        Production → postgresql://user:pass@aws-endpoint:5432/dbname
        """
        if self.is_production:
            # Try Secrets Manager first for DB credentials
            creds = secrets_manager.get_database_credentials()
            if creds and creds.get("host") and creds.get("password"):
                db_user = creds.get("username", "postgres")
                db_password = creds.get("password")
                db_host = creds.get("host")
                db_name = creds.get("database", "ai_legal_assistant")
                db_port = creds.get("port", "5432")
                return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

            # Fallback to environment variables if no secret present
            rds_endpoint = os.getenv('AWS_RDS_ENDPOINT')
            if rds_endpoint:
                db_user = os.getenv('AWS_RDS_USERNAME', 'postgres')
                db_password = os.getenv('AWS_RDS_PASSWORD')
                db_name = os.getenv('AWS_RDS_DATABASE', 'ai_legal_assistant')
                db_port = os.getenv('AWS_RDS_PORT', '5432')
                
                if not db_password:
                    raise ValueError("AWS_RDS_PASSWORD is required for production")
                
                return f"postgresql://{db_user}:{db_password}@{rds_endpoint}:{db_port}/{db_name}"
        
        # Development: Use local SQLite
        return "sqlite:///./ai_legal_assistant.db"
    
    # REDIS SETTINGS
    @property
    def redis_url(self) -> str:
        """
        Get Redis connection URL

        FLOW:
        Development → redis://localhost:6379
        Production → redis://elasticache-endpoint:6379 (prefers Secrets Manager, then env)
        """
        if self.is_production:
            elasticache_from_secret = secrets_manager.get_secret("elasticache_endpoint", "AWS_ELASTICACHE_ENDPOINT")
            if elasticache_from_secret:
                return f"redis://{elasticache_from_secret}:6379"

            # Fallback to environment variable (CloudFormation / CI should set this)
            elasticache_endpoint = os.getenv('AWS_ELASTICACHE_ENDPOINT')
            if elasticache_endpoint:
                return f"redis://{elasticache_endpoint}:6379"
                    

        # Development: Use local Redis
        return os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    @property
    def redis_host(self) -> str:
        elasticache_from_secret = secrets_manager.get_secret("elasticache_endpoint", "AWS_ELASTICACHE_ENDPOINT")
        if elasticache_from_secret:
            return f"redis://{elasticache_from_secret}"
        
        return os.getenv('REDIS_URL', 'redis://localhost:6379')
        
    @property
    def redis_port(self) -> str:
        return "6379"

    @property
    def aws_region(self) -> str:
        """AWS region to use for clients (default us-east-1)."""
        return os.getenv('AWS_REGION', 'us-east-1')

    @property
    def aws_s3_bucket(self) -> Optional[str]:
        """Primary S3 bucket name for legal documents (not secret by default)."""
        # allow storing bucket name in secrets if desired
        bucket_from_secret = secrets_manager.get_secret("aws_s3_bucket", None)
        if bucket_from_secret:
            return bucket_from_secret
        return os.getenv('AWS_S3_BUCKET') or None
    
    @property
    def aws_s3_prefix(self) -> str:
        """Optional prefix/folder inside the S3 bucket for documents."""
        return os.getenv('AWS_S3_PREFIX', '').lstrip('/')

    @property
    def chroma_persist_dir(self) -> str:
        """Directory used by Chroma to persist vector store (local path inside container)."""
        return os.getenv('CHROMA_PERSIST_DIR', './.chroma')

    @property
    def aws_access_key_id(self) -> Optional[str]:
        # prefer Secrets Manager; fallback to env
        return secrets_manager.get_secret("aws_access_key_id", "AWS_ACCESS_KEY_ID")

    @property
    def aws_secret_access_key(self) -> Optional[str]:
        return secrets_manager.get_secret("aws_secret_access_key", "AWS_SECRET_ACCESS_KEY")
    
    # S3 SETTINGS
    @property
    def documents_bucket(self) -> Optional[str]:
        """
        Legacy accessor - kept for compatibility.
        Returns the same as aws_s3_bucket.
        """
        return self.aws_s3_bucket
    
    @property
    def openai_api_key(self) -> str:
        key = secrets_manager.get_openai_api_key()
        if not key:
            raise ValueError("OpenAI API key not configured")
        return key

    @property
    def langsmith_api_key(self) -> Optional[str]:
        return secrets_manager.get_langsmith_api_key()

    @property
    def jwt_secret_key(self) -> str:
        val = secrets_manager.get_secret("jwt_secret_key", "JWT_SECRET_KEY")
        return val or os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
    
    # COST MONITORING
    @property
    def cost_monitoring_enabled(self) -> bool:
        return os.getenv('COST_MONITORING_ENABLED', 'true').lower() == 'true'

# Global settings instance
settings = Settings()

# Helper functions for easy access
def is_production() -> bool:
    return settings.is_production

def get_database_url() -> str:
    return settings.database_url

def get_redis_url() -> str:
    return settings.redis_url