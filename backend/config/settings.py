import os
import logging
from typing import Optional

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
            # Production: Use AWS RDS PostgreSQL
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
        Production → redis://elasticache-endpoint:6379
        """
        if self.is_production:
            # Production: Use AWS ElastiCache
            elasticache_endpoint = os.getenv('AWS_ELASTICACHE_ENDPOINT')
            if elasticache_endpoint:
                return f"redis://{elasticache_endpoint}:6379"
        
        # Development: Use local Redis
        return os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    # S3 SETTINGS
    @property
    def documents_bucket(self) -> Optional[str]:
        """
        Get S3 bucket name for documents
        
        USAGE:
        Production → ai-legal-assistant-documents-bucket
        Development → None (use local files)
        """
        if self.is_production:
            return os.getenv('AWS_S3_BUCKET')
        return None
    
    # API KEYS (same for both environments)
    @property
    def openai_api_key(self) -> str:
        return os.getenv('OPENAI_API_KEY', '')
    
    @property
    def langsmith_api_key(self) -> str:
        return os.getenv('LANGSMITH_API_KEY', '')
    
    @property
    def jwt_secret_key(self) -> str:
        return os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
    
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