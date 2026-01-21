from sqlalchemy import create_engine, Column, String, Integer, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    size = Column(Integer, default=0)  # Size in bytes
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="processing")  # processing, indexed, error
    chunks = Column(Integer, default=0)
    error_message = Column(String, nullable=True)

# Create engine
# Use a local sqlite file in the service directory or a data directory
DB_PATH = os.path.join(os.path.dirname(__file__), "rag.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
