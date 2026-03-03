# Enterprise RAG System

A production-ready **Retrieval-Augmented Generation (RAG)** system that enables intelligent document Q&A through semantic search and AI-powered answer generation. Built with FastAPI backend and Streamlit dashboard.

## What is RAG?

**Retrieval-Augmented Generation (RAG)** solves the problem of AI models not knowing your specific data by:

1. **Retrieving**: Finding relevant information from your documents using semantic search
2. **Augmenting**: Adding that retrieved context to the AI prompt
3. **Generating**: Creating accurate, contextual answers based on your actual documents

Instead of relying on pre-trained knowledge, RAG uses **your documents** as the source of truth.

---

## Features

### Core Capabilities
- **Multi-format Document Support**: Upload PDF, DOCX, and TXT files
- **Semantic Search**: Find relevant document chunks using vector embeddings
- **Intelligent Q&A**: Get answers grounded in your uploaded documents
- **JWT Authentication**: Secure API access with token-based authentication
- **Analytics Dashboard**: Track queries, performance, and user behavior
- **Safety Guardrails**: Protection against prompt injection, PII leakage, and malicious inputs

### User Interface
- **Modern Streamlit Dashboard**: Beautiful, intuitive web interface
- **Drag-and-drop Upload**: Easy document ingestion
- **Interactive Q&A**: Real-time question answering
- **Statistics Page**: Comprehensive analytics and visualizations
- **Feedback System**: Rate answers to improve the system

### Enterprise Features
- **Security First**: JWT tokens, input validation, safety checks
- **Analytics Tracking**: SQLite-based analytics with performance metrics
- **RESTful API**: Fully documented FastAPI endpoints
- **State Management**: Persistent vector database (ChromaDB)

---

## Architecture

```
┌─────────────────┐
│  Streamlit UI   │ ← User Interface (Dashboard)
└────────┬────────┘
         │ HTTP/HTTPS
         ▼
┌─────────────────┐
│   FastAPI API   │ ← REST API Layer
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌─────────┐ ┌─────────────┐
│Document │ │  Retriever  │
│Processor│ │   (RAG)     │
└────┬────┘ └──────┬──────┘
     │             │
     ▼             ▼
┌─────────────────────┐
│    ChromaDB         │ ← Vector Database (Embeddings)
│  (Vector Storage)   │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│   Cohere API        │ ← Embeddings & LLM
│  (Embed + Generate) │
└─────────────────────┘
```

### Component Flow

1. **Document Upload** → `DocumentProcessor` extracts text, chunks it, generates embeddings
2. **Embeddings** → Stored in ChromaDB for fast similarity search
3. **User Query** → `Retriever` finds relevant chunks using semantic search
4. **Context + Query** → Sent to Cohere LLM to generate answer
5. **Response** → Displayed to user with source citations
6. **Analytics** → All interactions logged for insights

---

## Tech Stack

### Backend
- **FastAPI** - Modern, fast Python web framework
- **Uvicorn** - ASGI server for FastAPI
- **Python-JOSE** - JWT token generation/validation
- **Passlib** - Password hashing (bcrypt)

### AI & ML
- **Cohere** - Embeddings (`embed-english-v3.0`) and LLM (`command-r7b-12-2024`)
- **ChromaDB** - Vector database for embeddings
- **NumPy** - Numerical operations

### Document Processing
- **PyPDF2** - PDF text extraction
- **python-docx** - DOCX file handling
- **Pandas** - Data manipulation

### Frontend
- **Streamlit** - Interactive dashboard framework
- **Plotly** - Interactive charts and graphs

### Database & Storage
- **SQLite** - Analytics database (lightweight, embedded)
- **ChromaDB** - Persistent vector storage

### Development
- **Pytest** - Testing framework
- **Python-dotenv** - Environment variable management

---

## Installation

### Prerequisites

- **Python 3.13+** (tested with Python 3.13.5)
- **pip** (Python package manager)
- **Cohere API Key** ([Get one here](https://dashboard.cohere.com/))

### Step-by-Step Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd enterprise-rag-system
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install --upgrade pip setuptools wheel
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Create a `.env` file in the project root:
   ```bash
   touch .env
   ```
   
   Add the following variables:
   ```env
   # Required: Cohere API Key for embeddings and LLM
   COHERE_API_KEY=your_cohere_api_key_here
   
   # Optional: JWT Secret Key (change in production!)
   SECRET_KEY=your-secret-key-change-this-in-production
   
   # Optional: API Configuration
   API_HOST=localhost
   API_PORT=8000
   ```

5. **Verify installation**
   ```bash
   python -c "import chromadb, cohere, fastapi, streamlit; print('✅ All packages installed!')"
   ```

---

## Quick Start

### 1. Start the FastAPI Server

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start the API server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`

- **API Documentation**: `http://localhost:8000/docs` (Swagger UI)
- **Alternative Docs**: `http://localhost:8000/redoc` (ReDoc)

### 2. Start the Streamlit Dashboard

In a **new terminal window**:

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start the dashboard
streamlit run src/dashboard/app.py
```

The dashboard will open at: `http://localhost:8501`

### 3. Login and Use

1. **Login Page**: Enter credentials (default: `demo` / `demo123`)
2. **Dashboard**: Upload documents and ask questions
3. **Statistics**: View analytics and system metrics

---

## Usage Guide

### Using the Dashboard

#### Login Page (`app.py`)
- Enter username and password
- Click "Login" to authenticate
- After login, use the sidebar to navigate to Dashboard or Statistics

#### Main Dashboard (`pages/1_Dashboard.py`)
1. **Upload Document**
   - Click "Choose a file" or drag-and-drop
   - Supported formats: PDF, DOCX, TXT
   - Click "Upload Document" button
   - Wait for processing confirmation

2. **Ask Questions**
   - Type your question in the text area
   - Click "Ask Question"
   - View the answer with source citations
   - Provide feedback to improve the system

#### Statistics Page (`pages/2_Statistics.py`)
- View system overview metrics
- Analyze query trends over time
- Review recent queries and performance
- Check top users and system events

### Using the API

#### 1. Authentication

```python
import requests

# Login to get JWT token
response = requests.post(
    "http://localhost:8000/auth/login",
    json={"username": "demo", "password": "demo123"}
)
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
```

#### 2. Upload Document

```python
# Upload a document
with open("document.pdf", "rb") as f:
    files = {"file": ("document.pdf", f, "application/pdf")}
    response = requests.post(
        "http://localhost:8000/documents/upload",
        headers=headers,
        files=files
    )
print(response.json())
```

#### 3. Ask Question

```python
# Ask a question
response = requests.post(
    "http://localhost:8000/rag/query",
    headers=headers,
    json={"query": "What is the vacation policy?"}
)
result = response.json()
print(f"Answer: {result['answer']}")
print(f"Sources: {result['sources']}")
```

#### 4. Submit Feedback

```python
# Submit feedback
response = requests.post(
    "http://localhost:8000/feedback",
    headers=headers,
    json={
        "query_id": result['query_id'],
        "rating": "positive",  # or "negative"
        "comment": "Very helpful answer!"
    }
)
```

### API Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/` | GET | Health check | No |
| `/auth/login` | POST | Login and get JWT token | No |
| `/documents/upload` | POST | Upload and process document | Yes |
| `/rag/query` | POST | Ask a question (RAG) | Yes |
| `/feedback` | POST | Submit feedback on answer | Yes |
| `/analytics/overview` | GET | Get analytics overview | Yes |
| `/analytics/queries` | GET | Get query history | Yes |

See full API documentation at: `http://localhost:8000/docs`

---

## Project Structure

```
enterprise-rag-system/
├── src/
│   ├── api/
│   │   └── main.py              # FastAPI application & endpoints
│   ├── dashboard/
│   │   ├── app.py               # Login page (Streamlit)
│   │   └── pages/
│   │       ├── 1_Dashboard.py   # Main dashboard (upload + Q&A)
│   │       └── 2_Statistics.py  # Analytics & statistics
│   ├── ingestion/
│   │   └── document_processor.py # Document parsing, chunking, embeddings
│   ├── retrieval/
│   │   └── retriever.py         # RAG pipeline (retrieve + generate)
│   ├── analytics/
│   │   └── tracker.py           # Analytics tracking & SQLite DB
│   └── guardrails/
│       └── safety.py            # Security checks (PII, injection, etc.)
├── data/
│   └── uploads/                 # Uploaded documents storage
├── chroma_db/                   # ChromaDB vector database (auto-created)
├── analytics.db                 # SQLite analytics database (auto-created)
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (create this)
├── pyrightconfig.json           # Type checking configuration
└── README.md                    # This file
```

---

## Security Features

### Authentication & Authorization
- **JWT Tokens**: Secure token-based authentication
- **Password Hashing**: bcrypt with salt (via Passlib)
- **Token Expiration**: 30-minute token lifetime

### Input Validation
- **Safety Guardrails**: Protection against:
  - Prompt injection attacks
  - Jailbreak attempts
  - PII (Personally Identifiable Information) leakage
  - DoS attacks (input length limits)

### Data Protection
- **PII Detection**: Automatic detection of sensitive data
- **Output Filtering**: Scans LLM responses for security issues
- **Input Sanitization**: Validates all user inputs

### Best Practices
- Environment variables for sensitive data
- CORS configuration
- Secure password storage
- Input/output validation

**Important**: Change the default `SECRET_KEY` in production!

---

## Analytics & Monitoring

The system tracks comprehensive analytics:

### Metrics Tracked
- **Query Performance**: Response time, token usage
- **User Behavior**: Query frequency, top users
- **System Events**: Uploads, errors, feedback
- **Quality Metrics**: Answer ratings, user satisfaction

### Database Schema
- `queries`: Query logs with performance data
- `feedback`: User ratings and comments
- `system_events`: System-level events (uploads, errors)
- `users`: User activity tracking

### Accessing Analytics

**Via Dashboard**: Navigate to "Statistics" page

**Via API**:
```python
# Get overview
response = requests.get(
    "http://localhost:8000/analytics/overview",
    headers=headers
)

# Get recent queries
response = requests.get(
    "http://localhost:8000/analytics/queries?limit=10",
    headers=headers
)
```

---

## Testing

### Run Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest

# Run specific test file
pytest test_rag.py

# Run with verbose output
pytest -v
```

### Test Files
- `test.py` - API endpoint testing
- `test_rag.py` - RAG pipeline testing
- `test_security.py` - Security guardrails testing
- `test_analytics.py` - Analytics tracking testing
- `test_document_processor.py` - Document processing testing

### Manual Testing

1. **Test API**:
   ```bash
   python test.py
   ```

2. **Test RAG**:
   ```bash
   python test_rag.py
   ```

3. **Test Security**:
   ```bash
   python test_security.py
   ```

---

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `COHERE_API_KEY` | Cohere API key for embeddings/LLM | Yes | - |
| `SECRET_KEY` | JWT secret key (change in production!) | No | `your-secret-key...` |
| `API_HOST` | API server host | No | `localhost` |
| `API_PORT` | API server port | No | `8000` |

### ChromaDB Configuration

ChromaDB automatically creates a persistent database in `./chroma_db/`. To reset:

```bash
rm -rf chroma_db/
# Database will be recreated on next run
```

### Analytics Database

SQLite database stored in `analytics.db`. To reset:

```bash
rm analytics.db
# Database will be recreated on next run
```

---

## Troubleshooting

### Common Issues

#### 1. **Import Error: chromadb**
```bash
# Solution: Reinstall chromadb
pip uninstall chromadb
pip install chromadb>=1.3.5
```

#### 2. **Cohere API Key Error**
```
ValueError: COHERE_API_KEY environment variable is not set
```
**Solution**: Create `.env` file and add `COHERE_API_KEY=your_key_here`

#### 3. **Port Already in Use**
```
Error: [Errno 48] Address already in use
```
**Solution**: Change port or kill the process:
```bash
# Find process
lsof -i :8000
# Kill process
kill -9 <PID>
```

#### 4. **Streamlit Login Not Redirecting**
**Solution**: After login, manually click "Dashboard" or "Statistics" in the sidebar. This is expected behavior in Streamlit 1.29.0 (automatic redirect requires newer version).

#### 5. **bcrypt/passlib Warning**
```
passlib/handlers/bcrypt.py:XXX: UserWarning: ...
```
**Solution**: This is harmless and suppressed. The system works correctly.

#### 6. **Pandas Installation Issues (Python 3.13)**
```bash
# Solution: Install build dependencies first
pip install --upgrade pip setuptools wheel
pip install Cython>=3.0.0 numpy>=1.26.0
pip install pandas>=2.2.0
```

---

## Deployment

### Production Considerations

1. **Change Default Secrets**
   - Update `SECRET_KEY` in `.env`
   - Use strong, random secret keys

2. **Environment Variables**
   - Use a secrets manager (AWS Secrets Manager, Azure Key Vault, etc.)
   - Never commit `.env` files

3. **Database**
   - Consider migrating SQLite to PostgreSQL for production
   - Use managed ChromaDB or PostgreSQL with pgvector

4. **API Server**
   - Use production ASGI server (Gunicorn + Uvicorn workers)
   - Set up reverse proxy (Nginx)
   - Enable HTTPS/SSL

5. **Monitoring**
   - Set up logging (structured logs)
   - Add monitoring (Prometheus, Grafana)
   - Configure alerts

6. **Rate Limiting**
   - Implement rate limiting on API endpoints
   - Add request throttling

### Example Deployment Commands

```bash
# Production server with multiple workers
gunicorn src.api.main:app \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000

# With environment variables
export COHERE_API_KEY=your_key
export SECRET_KEY=your_secret
gunicorn src.api.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

---

## How RAG Works

### Step-by-Step Process

1. **Document Ingestion**
   ```
   PDF/DOCX/TXT → Extract Text → Chunk (512 tokens, 50 overlap)
   → Generate Embeddings (Cohere) → Store in ChromaDB
   ```

2. **Query Processing**
   ```
   User Question → Generate Query Embedding → Semantic Search
   → Retrieve Top 5 Relevant Chunks → Build Context
   ```

3. **Answer Generation**
   ```
   Context + Query → Cohere LLM → Generate Answer
   → Safety Check → Return to User
   ```

### Key Concepts

- **Embeddings**: Numerical vectors representing text meaning (768 dimensions)
- **Chunking**: Splitting documents into manageable pieces (512 tokens)
- **Semantic Search**: Finding similar meaning, not just keywords
- **Context Window**: LLM receives query + relevant document chunks

---

## Learning Resources

### RAG Concepts
- [Retrieval-Augmented Generation Explained](https://www.pinecone.io/learn/retrieval-augmented-generation/)
- [Vector Databases Guide](https://www.pinecone.io/learn/vector-database/)

### Technologies Used
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Cohere API Documentation](https://docs.cohere.com/)

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Add tests for new features
- Update documentation
- Run linters before committing

---



## Acknowledgments

- **Cohere** - For embeddings and LLM capabilities
- **ChromaDB** - For vector database functionality
- **FastAPI** - For the excellent web framework
- **Streamlit** - For rapid dashboard development

---


