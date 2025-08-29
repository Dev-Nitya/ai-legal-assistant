import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

from config.settings import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

class DatabaseManager:

    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._setup_database()
    
    def _setup_database(self):
        """Set up database connection based on environment"""
        
        database_url = settings.database_url
        
        if settings.is_production:
            # PRODUCTION: PostgreSQL configuration
            logger.info("🌐 Connecting to AWS RDS PostgreSQL")
            
            # PostgreSQL-specific settings for production
            self.engine = create_engine(
                database_url,
                pool_pre_ping=True,          # Test connections before use
                pool_recycle=3600,           # Refresh connections every hour
                pool_size=5,                 # Keep 5 connections ready
                max_overflow=10,             # Allow up to 15 total connections
                echo=False                   # Don't log SQL queries
            )
        else:
            # DEVELOPMENT: SQLite configuration
            logger.info("💻 Connecting to local SQLite database")
            
            # SQLite-specific settings for development
            self.engine = create_engine(
                database_url,
                connect_args={"check_same_thread": False},  # Allow multiple threads
                echo=False
            )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        logger.info(f"✅ Database connection established")
    
    def create_tables(self):
        """Create all database tables"""
        try:
            # Import models so SQLAlchemy knows about them
            from models.user import User, UserSession, UserBudget
            
            # Create all tables
            Base.metadata.create_all(bind=self.engine)
            logger.info("✅ Database tables created/verified")
            
        except Exception as e:
            logger.error(f"❌ Error creating database tables: {e}")
            raise
    
    @contextmanager
    def get_session_context(self):
        """
        Database session with automatic cleanup
        
        USAGE IN OUR APP:
        with db_manager.get_session_context() as db:
            user = db.query(User).filter(User.email == "test@example.com").first()
        # Session automatically closed
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def get_session(self):
        """Get a single database session"""
        return self.SessionLocal()

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

# Initialize tables when module is imported
try:
    db_manager.create_tables()
except Exception as e:
    logger.warning(f"Could not create tables on import: {e}")