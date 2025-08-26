import os
import logging

from config.secrets import secrets_manager

logger = logging.getLogger(__name__)

class Settings:
    def __init__(self):
        """Initialize application settings"""
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")

         # Load secrets
        try:
            self.openai_api_key = secrets_manager.get_openai_api_key()
            self.langsmith_api_key = secrets_manager.get_langsmith_api_key()
            logger.info("✅ Secrets loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load secrets: {e}")
            raise

        # AWS Configuration
        self.use_aws_s3 = os.getenv("USE_AWS_S3", "false").lower() == "true"
        self.aws_s3_bucket = os.getenv("AWS_S3_BUCKET")
        self.aws_s3_prefix = os.getenv("AWS_S3_PREFIX", "legal-documents/")
        
        # Cache Configuration
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.cache_ttl_seconds = int(os.getenv("CACHE_TTL_SECONDS", "1800"))  # 30 minutes

        # Application Configuration
        self.chroma_persist_dir = os.getenv("CHROMA_PERSIST_DIR", "/app/chroma_db")
        self.max_query_length = int(os.getenv("MAX_QUERY_LENGTH", "1000"))
        self.default_complexity_level = os.getenv("DEFAULT_COMPLEXITY_LEVEL", "simple")
        
        # OpenSearch Configuration (for future use)
        self.use_opensearch = os.getenv("USE_OPENSEARCH", "false").lower() == "true"
        self.opensearch_endpoint = os.getenv("OPENSEARCH_ENDPOINT")
        
        # Rate Limiting
        self.rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
        self.rate_limit_per_hour = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))

    def is_production(self) -> bool:
        return self.environment == "production"

    def is_development(self) -> bool:
        return self.environment == "development"

# Global settings instance
settings = Settings()