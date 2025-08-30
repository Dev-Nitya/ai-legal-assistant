import boto3
import json
import os
from typing import Dict, Optional
from botocore.exceptions import ClientError, NoCredentialsError
import logging

logger = logging.getLogger(__name__)

class SecretsManager:
    def __init__(self):
        """Initialize AWS Secrets Manager client"""
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.environment = os.getenv("ENVIRONMENT", "production")
        self.secrets_client = None

        try:
            self.secrets_client = boto3.client('secretsmanager',region_name=self.region)
            logger.info(f"✅ AWS Secrets Manager initialized for {self.region}")
        except (NoCredentialsError, Exception) as e:
            logger.warning(f"⚠️ AWS Secrets Manager unavailable, using environment variables: {e}")

    def get_secret(self, secret_name: str, fallback_env_var: Optional[str] = None) -> Optional[str]:
        """Get secret from AWS Secrets Manager with environment variable fallback
        secret_name: short key (e.g. "openai_api_key") — full secret name = ai-legal-assistant-{secret_name}-{environment}
        fallback_env_var: environment variable to use if secret not found (e.g. "OPENAI_API_KEY")
        """

        # Try Secrets Manager first
        if self.secrets_client:
            try:
                full_secret_name = f"ai-legal-assistant-{secret_name}-{self.environment}"
                logger.info(f"🔑 Retrieving secret: {full_secret_name}")
                logger.warning(f"🔑 Retrieving secret: {full_secret_name}")

                # Avoid logging secret contents; only log that we attempted to retrieve
                response = self.secrets_client.get_secret_value(SecretId=full_secret_name)
                logger.warning(f"Retrieved secret for {full_secret_name} (response keys: {list(response.keys())})")

                # Handle SecretString (JSON or plain text)
                if 'SecretString' in response:
                    secret_str = response.get('SecretString') or ""
                    try:
                        secret_data = json.loads(secret_str)
                    except json.JSONDecodeError:
                        # Plain string (e.g. bucket name) — return as-is
                        logger.info(f"🔑 Retrieved plain secret for {full_secret_name} (len={len(secret_str)})")
                        return secret_str
                    
                    # If JSON, prefer common keys (api_key) or requested key
                    if isinstance(secret_data, dict):
                        return secret_data.get('api_key') or secret_data.get(secret_name) or json.dumps(secret_data)
                    return secret_data

                # Handle SecretBinary
                if 'SecretBinary' in response:
                    try:
                        import base64
                        decoded = base64.b64decode(response['SecretBinary'])
                        try:
                            return json.loads(decoded)
                        except json.JSONDecodeError:
                            return decoded.decode('utf-8', errors='replace')
                    except Exception as e:
                        logger.error(f"❌ Error decoding SecretBinary for {full_secret_name}: {e}")

            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code')
                if error_code == 'ResourceNotFoundException':
                    logger.warning(f"🔍 Secret {secret_name} not found in AWS Secrets Manager")
                else:
                    logger.error(f"❌ Error retrieving secret {secret_name}: {e}")
            except Exception as e:
                logger.error(f"❌ Unexpected error retrieving secret {secret_name}: {e}")

        # Fallback to environment variable if provided
        if fallback_env_var:
            env_value = os.getenv(fallback_env_var)
            if env_value:
                logger.info(f"📝 Using environment variable for {secret_name}")
                return env_value

        logger.error(f"❌ No secret found for {secret_name}")
        return None

    def get_openai_api_key(self) -> str:
        """Get OpenAI API key with fallback"""
        api_key = self.get_secret("openai_api_key", "OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not found in Secrets Manager or environment variables")
        return api_key

    def get_langsmith_api_key(self) -> Optional[str]:
        """Get LangSmith API key (optional)"""
        return self.get_secret("langsmith_api_key", "LANGSMITH_API_KEY")
    
    def get_database_credentials(self) -> Optional[Dict[str, str]]:
        """Get database credentials if using RDS"""
        try:
            if self.secrets_client:
                secret_name = f"ai-legal-assistant-db-credentials-{self.environment}"
                response = self.secrets_client.get_secret_value(SecretId=secret_name)
                
                if 'SecretString' in response:
                    data = json.loads(response['SecretString'])
                    # Expect keys: username, password, host, port, database
                    if isinstance(data, dict):
                        return {
                            "username": data.get("username"),
                            "password": data.get("password"),
                            "host": data.get("host"),
                            "port": data.get("port"),
                            "database": data.get("database")
                        }
        except Exception as e:
            logger.warning(f"Database credentials not found: {e}")
        
        # Fallback to env vars if present
        username = os.getenv("AWS_RDS_USERNAME")
        password = os.getenv("AWS_RDS_PASSWORD")
        host = os.getenv("AWS_RDS_ENDPOINT")
        port = os.getenv("AWS_RDS_PORT")
        database = os.getenv("AWS_RDS_DATABASE")
        if username and password and host:
            return {"username": username, "password": password, "host": host, "port": port, "database": database}
        return None
    
    def create_secret(self, secret_name: str, secret_value: str, description: str = "") -> bool:
        """Create a new secret (useful for initial setup)"""
        if not self.secrets_client:
            logger.error("Cannot create secret: AWS Secrets Manager not available")
            return False
            
        try:
            full_secret_name = f"ai-legal-assistant-{secret_name}-{self.environment}"
            
            self.secrets_client.create_secret(
                Name=full_secret_name,
                Description=description,
                SecretString=json.dumps({"api_key": secret_value})
            )
            logger.info(f"✅ Created secret: {full_secret_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create secret {secret_name}: {e}")
            return False
        
# Global secrets manager instance
secrets_manager = SecretsManager()