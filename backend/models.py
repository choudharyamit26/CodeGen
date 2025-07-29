from sqlalchemy import Column, Integer, String, Text, DateTime
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import Base  # Import Base from database.py
from datetime import datetime


class GenerationRecord(Base):
    __tablename__ = "generation_records"
    id = Column(Integer, primary_key=True, index=True)
    image_path = Column(String, nullable=True)
    prompt = Column(Text)
    description = Column(Text, nullable=True)
    ui_code = Column(Text, nullable=True)
    db_schema = Column(Text, nullable=True)
    backend_code = Column(Text, nullable=True)
    db_queries = Column(Text, nullable=True)
    tech_docs = Column(Text, nullable=True)
    backend_language = Column(String)
    framework = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
