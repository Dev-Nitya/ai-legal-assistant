import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import logging

from models.user import Base
from config.settings import Settings

logger = logging.getLogger(__name__)

class DatabaseManager:

    def __init__(self):
        self.settings = Settings()
        self.engine = None
        self.SessionLocal = None
        self.setup_database()
    
    def setup_database(self):
        database_url = self.settings.database_url
        
        if database_url.startswith("sqlite"):
            # SQLite setup (development)
            self.engine = create_engine(
                database_url,
                connect_args={"check_same_thread": False},  # SQLite specific
                poolclass=StaticPool
            )
            logger.info("🗄️  Using SQLite database for development")
        else:
            # PostgreSQL setup (production)
            self.engine = create_engine(
                database_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True
            )
            logger.info("🗄️  Using PostgreSQL database for production")
        
        # Create session factory
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create all tables
        self.create_tables()
    
    def create_tables(self):
        """Create all user tables if they don't exist."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("✅ User database tables created/verified")
        except Exception as e:
            logger.error(f"❌ Failed to create database tables: {e}")
            raise
    
    def get_session(self):
        """
        Get a database session for operations.
        """
        return self.SessionLocal()
    
    def close(self):
        """Close database connections."""
        if self.engine:
            self.engine.dispose()
            logger.info("🔒 Database connections closed")

# Global database manager instance
db_manager = DatabaseManager()

# Dependency for FastAPI routes
def get_db():
    """
    FastAPI dependency to get database session.
    
    SIMPLE EXPLANATION:
    This function provides a database connection to our API endpoints.
    FastAPI will automatically call this when endpoints need database access.
    """
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()