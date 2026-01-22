from sqlalchemy import create_engine, Column, String, Integer, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
import os
import sys
from pathlib import Path
import logging

# Add project root to path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from apps.shared.config_loader import ConfigLoader

logger = logging.getLogger(__name__)

Base = declarative_base()

class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id = Column(String, primary_key=True, server_default=func.gen_random_uuid()) # PostgreSQL specific
    kb_id = Column(String, unique=True, nullable=False) # kb_<uuid>
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    embedding_model = Column(String, default='zhipu')
    chunk_count = Column(Integer, default=0)
    doc_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String, default='active') # active/deleted

    documents = relationship("Document", back_populates="knowledge_base", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    kb_id = Column(String, ForeignKey("knowledge_bases.kb_id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    size = Column(Integer, default=0)  # Size in bytes
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="uploaded")  # uploaded/processing/indexed/error
    chunks = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    knowledge_base = relationship("KnowledgeBase", back_populates="documents")

# Global engine and session factory
engine = None
SessionLocal = None

def init_db(config_path: str = None):
    global engine, SessionLocal
    
    if config_path is None:
        config_path = os.path.join(project_root, "config")
    
    try:
        config_loader = ConfigLoader(config_path)
        db_config = config_loader.load_config("database")
        
        # Fallback to default if database.yaml is empty or missing (during migration)
        if not db_config:
             logger.warning("Database config not found, using defaults")
             # Assuming we want to fail or use sqlite? 
             # For this task we want PostgreSQL.
             # Let's assume the config write was successful.
             pass

        pg_config = db_config.get("postgresql", {})
        user = pg_config.get("user", "postgres")
        password = pg_config.get("password", "your_password")
        host = pg_config.get("host", "localhost")
        port = pg_config.get("port", 5432)
        db_name = pg_config.get("database", "rshanygen")
        pool_size = pg_config.get("pool_size", 10)

        # Construct connection string
        # url = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
        # For psycopg2
        url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"

        engine = create_engine(
            url, 
            pool_size=pool_size, 
            max_overflow=20,
            pool_pre_ping=True
        )
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info(f"Database initialized: {host}:{port}/{db_name}")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # Fallback to SQLite for dev/testing if PG fails? 
        # Or just raise to alert user.
        # Let's stick to PG as requested.
        raise e

def get_db():
    if SessionLocal is None:
        # Try to init with default path if not initialized
        init_db()
        
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
