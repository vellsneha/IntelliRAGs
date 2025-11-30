# src/api/main.py

"""
FastAPI REST API for Enterprise RAG System

Complete API providing:
- JWT-based authentication
- Document upload and ingestion
- Question answering with RAG
- Analytics and monitoring
- User feedback collection

Security Features:
- JWT token authentication
- Input validation with Pydantic
- Safety guardrails (prompt injection, PII detection)
- CORS configuration
- Rate limiting ready
"""

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import shutil
import warnings
import logging
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.document_processor import DocumentProcessor
from retrieval.retriever import Retriever
from guardrails.safety import SafetyGuardrails
from analytics.tracker import AnalyticsTracker

# ═══════════════════════════════════════════════════════════
# Initialize FastAPI App
# ═══════════════════════════════════════════════════════════

app = FastAPI(
    title="Enterprise RAG System",
    version="1.0.0",
    description="Production-ready RAG system with security and analytics"
)

# ═══════════════════════════════════════════════════════════
# Security Configuration
# ═══════════════════════════════════════════════════════════

security = HTTPBearer()
# Suppress bcrypt version warning (passlib compatibility issue, but functionality works)
import warnings
import logging
# Suppress passlib/bcrypt warnings
logging.getLogger("passlib").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=UserWarning, module="passlib")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# ═══════════════════════════════════════════════════════════
# CORS Middleware
# ═══════════════════════════════════════════════════════════

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════════════
# Initialize Components
# ═══════════════════════════════════════════════════════════

processor = DocumentProcessor()
retriever = Retriever()
guardrails = SafetyGuardrails()
analytics = AnalyticsTracker()

# ═══════════════════════════════════════════════════════════
# User Database (Replace with real database)
# ═══════════════════════════════════════════════════════════

# Lazy initialization to avoid bcrypt compatibility issues at import time
_fake_users_db = None

def get_fake_users_db():
    """Get fake users database with lazy password hashing."""
    global _fake_users_db
    if _fake_users_db is None:
        _fake_users_db = {
            "demo": {
                "username": "demo",
                "hashed_password": pwd_context.hash("demo123")
            }
        }
    return _fake_users_db

# ═══════════════════════════════════════════════════════════
# Pydantic Models
# ═══════════════════════════════════════════════════════════

class QuestionRequest(BaseModel):
    question: str
    user_id: Optional[str] = "anonymous"


class QuestionResponse(BaseModel):
    answer: str
    sources: List[str]
    confidence: float
    flagged: bool


class Token(BaseModel):
    access_token: str
    token_type: str


class User(BaseModel):
    username: str
    password: str


# ═══════════════════════════════════════════════════════════
# Authentication Functions
# ═══════════════════════════════════════════════════════════

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify JWT token and return username."""
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        username = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        # Type checker now knows username is not None after the check
        return str(username)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


# ═══════════════════════════════════════════════════════════
# API Endpoints
# ═══════════════════════════════════════════════════════════

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Enterprise RAG System API",
        "version": "1.0.0",
        "status": "running"
    }


@app.post("/auth/login", response_model=Token)
async def login(user: User):
    """
    Authenticate user and return JWT token.
    
    Example:
        POST /auth/login
        Body: {"username": "demo", "password": "demo123"}
    """
    # Check if user exists
    fake_users_db = get_fake_users_db()
    db_user = fake_users_db.get(user.username)
    if not db_user or not verify_password(user.password, db_user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.username})
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    username: str = Depends(verify_token)
):
    """
    Upload and ingest a document.
    
    Requires authentication.
    Supports PDF, DOCX, and TXT files.
    """
    try:
        # Save uploaded file
        upload_dir = "data/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required"
            )
        file_path = os.path.join(upload_dir, file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Ingest document
        metadata = {
            "filename": file.filename,
            "uploaded_by": username,
            "upload_date": datetime.utcnow().isoformat()
        }
        result = processor.ingest_document(file_path, metadata)
        
        # Log event
        analytics.log_event("document_upload", {
            "user": username,
            "filename": file.filename,
            "chunks": result['chunks_created']
        })
        
        return {
            "status": "success",
            "message": f"Document '{file.filename}' ingested successfully",
            "details": result
        }
    
    except Exception as e:
        analytics.log_event("document_upload_error", {
            "user": username,
            "filename": file.filename,
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/query", response_model=QuestionResponse)
async def ask_question(
    request: QuestionRequest,
    username: str = Depends(verify_token)
):
    """
    Ask a question using RAG.
    
    Requires authentication.
    Includes safety checks and analytics logging.
    """
    try:
        start_time = datetime.utcnow()
        
        # Check for malicious input
        is_safe, warning = guardrails.check_input(request.question)
        if not is_safe:
            analytics.log_event("query_blocked", {
                "user": username,
                "reason": warning
            })
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Query blocked: {warning}"
            )
        
        # Get answer
        result = retriever.answer_question(request.question)
        
        # Check output safety
        is_safe_output, output_warning = guardrails.check_output(result['answer'])
        
        # Calculate latency
        latency = (datetime.utcnow() - start_time).total_seconds()
        
        # Log query
        analytics.log_query({
            "user": username,
            "question": request.question,
            "answer_length": len(result['answer']),
            "sources_count": len(result['sources']),
            "latency_seconds": latency,
            "flagged": not is_safe_output
        })
        
        return {
            "answer": result['answer'],
            "sources": result['sources'],
            "confidence": 0.85,
            "flagged": not is_safe_output
        }
    
    except HTTPException:
        raise
    except Exception as e:
        analytics.log_event("query_error", {
            "user": username,
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/analytics/summary")
async def get_analytics(username: str = Depends(verify_token)):
    """
    Get analytics summary.
    
    Requires authentication.
    Returns comprehensive usage statistics.
    """
    summary = analytics.get_summary()
    return summary


@app.post("/feedback")
async def submit_feedback(
    query_id: int,
    rating: int,
    username: str = Depends(verify_token)
):
    """
    Submit user feedback on answer quality.
    
    Args:
        query_id: ID of the query being rated
        rating: Rating from 1-5
    """
    if rating < 1 or rating > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be between 1 and 5"
        )
    
    analytics.log_feedback(query_id, username, rating)
    analytics.log_event("feedback", {
        "user": username,
        "query_id": query_id,
        "rating": rating
    })
    
    return {
        "status": "success",
        "message": "Feedback recorded"
    }


# Run with: uvicorn src.api.main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)