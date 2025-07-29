from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import traceback
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="app.log",
)
logger = logging.getLogger(__name__)

# Use an absolute path for the database
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'example.db')}"

try:
    # Ensure the directory is writable
    if not os.access(BASE_DIR, os.W_OK):
        logger.error(f"Directory {BASE_DIR} is not writable")
        raise Exception(f"Directory {BASE_DIR} is not writable")

    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    logger.info(f"Database initialized with URL: {DATABASE_URL}")
except Exception as e:
    logger.error(f"Database initialization failed: {str(e)}\n{traceback.format_exc()}")
    raise Exception(
        f"Database initialization failed: {str(e)}\n{traceback.format_exc()}"
    )
