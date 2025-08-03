import traceback
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import uuid
import os
import aiofiles
from .database import engine, SessionLocal, Base
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from .file_processing import file_to_text as image_to_text
from .groq_client import (
    generate_ui_code,
    generate_db_schema,
    generate_backend_code,
    generate_db_queries,
    generate_technical_docs,
    generate_er_diagram,
    generate_core_language_code,
    detect_stack_with_langchain,
    analyze_request,
    determine_generation_types,
    CodeAnalysis,
    # Legacy functions for backward compatibility
    detect_stack,
)
from .models import GenerationRecord
from typing import Optional
from sqlalchemy.exc import OperationalError
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="app.log",
)
logger = logging.getLogger(__name__)

app = FastAPI()

try:
    with engine.connect() as connection:
        logger.info("Database connection successful")
        existing_tables = connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='table';")
        ).fetchall()
        logger.info(
            f"Existing tables before create_all: {[row[0] for row in existing_tables]}"
        )

    Base.metadata.create_all(bind=engine, checkfirst=True)
    logger.info("Ran Base.metadata.create_all to create tables")

    with engine.connect() as connection:
        result = connection.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='generation_records';"
            )
        ).fetchone()
        if result:
            logger.info("Verified generation_records table exists")
        else:
            logger.warning(
                "generation_records table not found, attempting manual creation"
            )
            connection.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS generation_records (
                    id INTEGER PRIMARY KEY,
                    image_path VARCHAR,
                    prompt TEXT,
                    description TEXT,
                    ui_code TEXT,
                    db_schema TEXT,
                    backend_code TEXT,
                    db_queries TEXT,
                    tech_docs TEXT,
                    er_diagram TEXT,
                    backend_language VARCHAR,
                    framework VARCHAR,
                    frontend_framework VARCHAR,
                    created_at DATETIME
                )
            """
                )
            )
            connection.commit()
            logger.info("Manually created generation_records table with new columns")
            result = connection.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='generation_records';"
                )
            ).fetchone()
            if not result:
                logger.error(
                    "Failed to create generation_records table even after manual attempt"
                )
                raise Exception("Failed to create generation_records table")
except OperationalError as e:
    logger.error(
        f"Failed to connect to database or create tables: {str(e)}\n{traceback.format_exc()}"
    )
    raise Exception(
        f"Failed to connect to database or create tables: {str(e)}\n{traceback.format_exc()}"
    )
except Exception as e:
    logger.error(
        f"Unexpected error during database initialization: {str(e)}\n{traceback.format_exc()}"
    )
    raise Exception(
        f"Unexpected error during database initialization: {str(e)}\n{traceback.format_exc()}"
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8501"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database error: {str(e)}\n{traceback.format_exc()}")
        raise
    finally:
        db.close()


def sse_event(event_type: str, data: any):
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


async def generation_stream(
    file_path: Optional[str],
    prompt: str,
    generate_types: dict,
    db: Session,
):
    try:
        try:
            db.execute(text("SELECT 1 FROM generation_records LIMIT 1"))
            logger.info("Verified generation_records table exists")
        except OperationalError as e:
            yield sse_event(
                "error",
                {
                    "message": f"Database table 'generation_records' does not exist: {str(e)}",
                    "traceback": traceback.format_exc(),
                },
            )
            logger.error(f"Table check failed: {str(e)}\n{traceback.format_exc()}")
            return

        record = GenerationRecord(
            image_path=file_path,
            prompt=prompt,
        )
        db.add(record)
        try:
            db.commit()
            db.refresh(record)
            logger.info(f"Created generation record with ID {record.id}")
        except OperationalError as e:
            yield sse_event(
                "error",
                {
                    "message": f"Failed to save record to database: {str(e)}",
                    "traceback": traceback.format_exc(),
                },
            )
            logger.error(f"Failed to save record: {str(e)}\n{traceback.format_exc()}")
            return

        description = ""
        if file_path:
            try:
                description = await asyncio.to_thread(image_to_text, file_path)
                logger.info(f"Extracted description from image: {description[:100]}...")
            except Exception as e:
                yield sse_event(
                    "error",
                    {
                        "message": f"Image processing failed: {str(e)}",
                        "traceback": traceback.format_exc(),
                    },
                )
                logger.error(
                    f"Image processing failed: {str(e)}\n{traceback.format_exc()}"
                )
                return

        full_description = f"{description}\n\nUser Requirements: {prompt}"
        record.description = full_description
        try:
            db.commit()
            logger.info("Updated record with description")
        except OperationalError as e:
            yield sse_event(
                "error",
                {
                    "message": f"Failed to update record description: {str(e)}",
                    "traceback": traceback.format_exc(),
                },
            )
            logger.error(
                f"Failed to update description: {str(e)}\n{traceback.format_exc()}"
            )
            return

        # Use LangChain enhanced analysis
        try:
            # Analyze the request using LangChain
            analysis = await analyze_request(full_description)
            logger.info(f"LangChain analysis: {analysis.dict()}")

            # Use LangChain stack detection (now returns 4 values including frontend_framework)
            backend_language, framework, use_framework, frontend_framework = (
                await detect_stack_with_langchain(full_description)
            )
            logger.info(
                f"Detected stack: {backend_language}/{framework}, frontend: {frontend_framework}, use_framework: {use_framework}"
            )

        except Exception as e:
            logger.warning(f"LangChain analysis failed, using fallback: {str(e)}")
            # Fallback to original detection if LangChain fails
            backend_language, framework = await asyncio.to_thread(
                detect_stack, full_description
            )
            frontend_framework = None

            # Create a simple analysis object for fallback with all required fields
            analysis = CodeAnalysis(
                language=backend_language,
                requires_framework="api" in full_description.lower()
                or "server" in full_description.lower(),
                framework=framework,
                frontend_framework=frontend_framework,
                code_type=(
                    "simple_function"
                    if not (
                        "api" in full_description.lower()
                        or "server" in full_description.lower()
                    )
                    else "web_api"
                ),
                components_needed=["backend_code"],
                ui_type=frontend_framework,
            )
            use_framework = analysis.requires_framework

        record.backend_language = backend_language
        record.framework = framework if use_framework else "core"
        record.frontend_framework = frontend_framework
        db.commit()

        yield sse_event(
            "config",
            {
                "backend_language": backend_language,
                "framework": framework,
                "frontend_framework": frontend_framework,
                "use_framework": use_framework,
                "analysis": (
                    analysis.dict() if hasattr(analysis, "dict") else str(analysis)
                ),
            },
        )

        # Update generate_types if not provided or use analysis
        if not any(generate_types.values()):
            generate_types = determine_generation_types(analysis)
            logger.info(f"Updated generate_types from analysis: {generate_types}")

        if generate_types.get("ui_code"):
            yield sse_event("progress", {"step": "UI", "status": "started"})
            try:
                # Pass frontend framework to UI generation
                ui_code = await generate_ui_code(
                    full_description, analysis.frontend_framework
                )
                record.ui_code = ui_code
                db.commit()
                yield sse_event(
                    "ui_code",
                    {
                        "code": ui_code,
                        "framework": analysis.frontend_framework or "html",
                    },
                )
                yield sse_event("progress", {"step": "UI", "status": "completed"})
                logger.info(
                    f"Generated and saved UI code using {analysis.frontend_framework or 'HTML'}"
                )
            except Exception as e:
                yield sse_event(
                    "error",
                    {
                        "message": f"UI code generation failed: {str(e)}",
                        "traceback": traceback.format_exc(),
                    },
                )
                logger.error(
                    f"UI code generation failed: {str(e)}\n{traceback.format_exc()}"
                )
                return

        if generate_types.get("db_schema"):
            yield sse_event("progress", {"step": "DB Schema", "status": "started"})
            try:
                db_schema = await generate_db_schema(full_description)
                record.db_schema = db_schema
                db.commit()
                yield sse_event("db_schema", {"schema": db_schema})
                yield sse_event(
                    "progress", {"step": "DB Schema", "status": "completed"}
                )
                logger.info("Generated and saved DB schema")
            except Exception as e:
                yield sse_event(
                    "error",
                    {
                        "message": f"DB schema generation failed: {str(e)}",
                        "traceback": traceback.format_exc(),
                    },
                )
                logger.error(
                    f"DB schema generation failed: {str(e)}\n{traceback.format_exc()}"
                )
                return

        if generate_types.get("er_diagram"):
            yield sse_event("progress", {"step": "E-R Diagram", "status": "started"})
            try:
                er_diagram = await generate_er_diagram(full_description)
                record.er_diagram = er_diagram
                db.commit()
                yield sse_event("er_diagram", {"diagram": er_diagram})
                yield sse_event(
                    "progress", {"step": "E-R Diagram", "status": "completed"}
                )
                logger.info("Generated and saved E-R diagram")
            except Exception as e:
                yield sse_event(
                    "error",
                    {
                        "message": f"E-R diagram generation failed: {str(e)}",
                        "traceback": traceback.format_exc(),
                    },
                )
                logger.error(
                    f"E-R diagram generation failed: {str(e)}\n{traceback.format_exc()}"
                )
                return

        if generate_types.get("backend_code"):
            yield sse_event("progress", {"step": "Backend", "status": "started"})
            try:
                # Use the new LangChain-enhanced backend code generation
                backend_code = await generate_backend_code(
                    full_description, backend_language, framework, analysis
                )

                record.backend_code = backend_code
                db.commit()
                yield sse_event(
                    "backend_code",
                    {
                        "code": backend_code,
                        "language": backend_language,
                        "framework": framework if use_framework else "core",
                    },
                )
                yield sse_event("progress", {"step": "Backend", "status": "completed"})
                logger.info(
                    f"Generated and saved backend code using {backend_language}/{framework}"
                )
            except Exception as e:
                yield sse_event(
                    "error",
                    {
                        "message": f"Backend code generation failed: {str(e)}",
                        "traceback": traceback.format_exc(),
                    },
                )
                logger.error(
                    f"Backend code generation failed: {str(e)}\n{traceback.format_exc()}"
                )
                return

        if generate_types.get("db_queries"):
            yield sse_event("progress", {"step": "DB Queries", "status": "started"})
            try:
                db_queries = await generate_db_queries(full_description)
                record.db_queries = db_queries
                db.commit()
                yield sse_event("db_queries", {"queries": db_queries})
                yield sse_event(
                    "progress", {"step": "DB Queries", "status": "completed"}
                )
                logger.info("Generated and saved DB queries")
            except Exception as e:
                yield sse_event(
                    "error",
                    {
                        "message": f"DB queries generation failed: {str(e)}",
                        "traceback": traceback.format_exc(),
                    },
                )
                logger.error(
                    f"DB queries generation failed: {str(e)}\n{traceback.format_exc()}"
                )
                return

        if generate_types.get("tech_docs"):
            yield sse_event("progress", {"step": "Documentation", "status": "started"})
            try:
                tech_docs = await generate_technical_docs(full_description)
                record.tech_docs = tech_docs
                db.commit()
                yield sse_event("tech_docs", {"documentation": tech_docs})
                yield sse_event(
                    "progress", {"step": "Documentation", "status": "completed"}
                )
                logger.info("Generated and saved technical documentation")
            except Exception as e:
                yield sse_event(
                    "error",
                    {
                        "message": f"Documentation generation failed: {str(e)}",
                        "traceback": traceback.format_exc(),
                    },
                )
                logger.error(
                    f"Documentation generation failed: {str(e)}\n{traceback.format_exc()}"
                )
                return

        yield sse_event("complete", {"id": record.id})
        logger.info(f"Generation completed with ID {record.id}")

        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Deleted uploaded file: {file_path}")
            except Exception as e:
                yield sse_event(
                    "warning",
                    {
                        "message": f"Failed to delete uploaded file: {str(e)}",
                        "traceback": traceback.format_exc(),
                    },
                )
                logger.warning(
                    f"Failed to delete file {file_path}: {str(e)}\n{traceback.format_exc()}"
                )

    except Exception as e:
        yield sse_event(
            "error",
            {
                "message": f"Unexpected error: {str(e)}",
                "traceback": traceback.format_exc(),
            },
        )
        logger.error(
            f"Unexpected error in generation_stream: {str(e)}\n{traceback.format_exc()}"
        )


@app.post("/generate-code")
async def generate_code(
    file: UploadFile = File(None),
    prompt: str = Form(""),
    generate_types: str = Form("{}"),
    db: Session = Depends(get_db),
):
    file_path = None
    if file:
        logger.info(f"Received file: {file.filename}, type: {file.content_type}")
    else:
        logger.info("No file uploaded")
    if file and file.filename:
        file_ext = file.filename.split(".")[-1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Allowed: png, jpg, jpeg, pdf",
            )

        await file.seek(0)
        content = await file.read()
        file_size = len(content)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large. Max size: 5MB")
        await file.seek(0)

        file_path = f"{UPLOAD_DIR}/{uuid.uuid4()}.{file_ext}"
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        logger.info(f"Saved uploaded file: {file_path}")

    try:
        generate_types_dict = json.loads(generate_types)
    except json.JSONDecodeError:
        logger.error(f"Invalid generate_types JSON: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail="Invalid generate_types JSON")

    logger.info(
        f"Starting code generation for prompt: {prompt}, generate_types: {generate_types}"
    )
    return StreamingResponse(
        generation_stream(file_path, prompt, generate_types_dict, db),
        media_type="text/event-stream",
    )


@app.get("/generations")
def get_generations(db: Session = Depends(get_db)):
    try:
        records = (
            db.query(GenerationRecord)
            .order_by(GenerationRecord.created_at.desc())
            .all()
        )
        return [
            {
                "id": record.id,
                "prompt": record.prompt or "Image-based request",
                "backend_language": record.backend_language,
                "framework": record.framework,
                "frontend_framework": getattr(record, "frontend_framework", None),
                "created_at": record.created_at.isoformat(),
            }
            for record in records
        ]
    except Exception as e:
        logger.error(f"Failed to fetch generations: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch generations: {str(e)}",
        )


@app.get("/generations/{generation_id}")
def get_generation(generation_id: int, db: Session = Depends(get_db)):
    try:
        record = (
            db.query(GenerationRecord)
            .filter(GenerationRecord.id == generation_id)
            .first()
        )
        if record:
            logger.info(f"Retrieved generation record with ID {generation_id}")
            return {
                "id": record.id,
                "image_path": record.image_path,
                "prompt": record.prompt,
                "description": record.description,
                "ui_code": record.ui_code,
                "db_schema": record.db_schema,
                "backend_code": record.backend_code,
                "db_queries": record.db_queries,
                "tech_docs": record.tech_docs,
                "er_diagram": getattr(record, "er_diagram", None),
                "backend_language": record.backend_language,
                "framework": record.framework,
                "frontend_framework": getattr(record, "frontend_framework", None),
                "created_at": record.created_at.isoformat(),
            }
        raise HTTPException(status_code=404, detail="Record not found")
    except Exception as e:
        logger.error(
            f"Failed to retrieve generation {generation_id}: {str(e)}\n{traceback.format_exc()}"
        )
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Failed to retrieve generation: {str(e)}",
                "traceback": traceback.format_exc(),
            },
        )


# New endpoints for enhanced functionality
@app.get("/supported-frameworks")
def get_supported_frameworks():
    """Get list of supported frontend and backend frameworks"""
    return {
        "frontend": {
            "html": "Plain HTML/CSS/JavaScript",
            "react": "React with Hooks",
            "vue": "Vue 3 with Composition API",
            "angular": "Angular with TypeScript",
        },
        "backend": {
            "python": {
                "core": "Pure Python",
                "fastapi": "FastAPI Framework",
                "flask": "Flask Framework",
                "django": "Django Framework",
            },
            "javascript": {"core": "Node.js Core", "express": "Express.js Framework"},
            "java": {"core": "Core Java", "spring": "Spring Boot Framework"},
        },
    }


@app.post("/generate-fullstack")
async def generate_fullstack(
    file: UploadFile = File(None),
    prompt: str = Form(""),
    backend_language: str = Form("python"),
    frontend_framework: str = Form("react"),
    db: Session = Depends(get_db),
):
    """Generate a complete fullstack application"""
    # Set generate_types for fullstack
    generate_types_dict = {
        "ui_code": True,
        "db_schema": True,
        "backend_code": True,
        "db_queries": True,
        "tech_docs": True,
        "er_diagram": True,
    }

    file_path = None
    if file and file.filename:
        file_ext = file.filename.split(".")[-1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Allowed: png, jpg, jpeg, pdf",
            )

        await file.seek(0)
        content = await file.read()
        file_size = len(content)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large. Max size: 5MB")
        await file.seek(0)

        file_path = f"{UPLOAD_DIR}/{uuid.uuid4()}.{file_ext}"
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        logger.info(f"Saved uploaded file for fullstack generation: {file_path}")

    logger.info(
        f"Starting fullstack generation: {backend_language} + {frontend_framework}"
    )
    return StreamingResponse(
        generation_stream(file_path, prompt, generate_types_dict, db),
        media_type="text/event-stream",
    )
