import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from config import Config
from auth_models import Base, User, Building, Drawing, ChatMessage

logger = logging.getLogger(__name__)

class AuthDatabase:
    def __init__(self):
        self.config = Config()
        # Use SQLite for local development, PostgreSQL for production
        if self.config.POSTGRES_HOST == "localhost" and not hasattr(self, '_postgres_available'):
            # Check if PostgreSQL is available, fall back to SQLite
            try:
                test_engine = create_engine(self.config.postgres_url)
                test_engine.connect().close()
                self.database_url = self.config.postgres_url
                logger.info("Using PostgreSQL database")
            except Exception:
                # Fall back to SQLite for local development
                self.database_url = "sqlite:///./auth.db"
                logger.info("PostgreSQL not available, using SQLite for development")
        else:
            self.database_url = self.config.postgres_url
            logger.info("Using PostgreSQL database")
        
        self.engine = create_engine(
            self.database_url,
            pool_pre_ping=True,
            echo=False  # Set to True for SQL debugging
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """Create all tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session"""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            with self.engine.connect() as conn:
                conn.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

# Global database instance
auth_db = AuthDatabase()