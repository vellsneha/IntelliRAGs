# Intelli RAG System

A production-ready **Retrieval-Augmented Generation (RAG)** system that enables intelligent document Q&A through semantic search and AI-powered answer generation. Built with FastAPI backend, Streamlit dashboard, Cohere LLMS and ChromaDB.


## Features

Focused on implementing the Basic RAG structure, thus contains all the basic requirements such as, the semantic search, JWT Authentication, Dashboard and also the Safety Guardrails.

### Enterprise Features
- **Security First**: JWT tokens, input validation, safety checks
- **Analytics Tracking**: SQLite-based analytics with performance metrics
- **RESTful API**: Fully documented FastAPI endpoints
- **State Management**: Persistent vector database with ChromaDB

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

## Installation

### Prerequisites

- **Python 3.13+** (tested with Python 3.13.5)
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

## Project Structure
It Should Look like this.

```
enterprise-rag-system/
├── src/
│   ├── api/
│   │   └── main.py              # FastAPI application & endpoints
│   ├── dashboard/
│   │   ├── app.py               # Login page 
│   │   └── pages/
│   │       ├── 1_Dashboard.py   # Main dashboard 
│   │       └── 2_Statistics.py  # Analytics & statistics
│   ├── ingestion/
│   │   └── document_processor.py # Document parsing, chunking, embeddings
│   ├── retrieval/
│   │   └── retriever.py         # RAG pipeline 
│   ├── analytics/
│   │   └── tracker.py           # Analytics tracking & SQLite DB
│   └── guardrails/
│       └── safety.py            # Security checks 
├── data/
│   └── uploads/                 # Uploaded documents storage
├── chroma_db/                   # ChromaDB vector database 
├── analytics.db                 # SQLite analytics database 
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables 
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

   ```

---


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


#### 1. **Streamlit Login Not Redirecting**
**Solution**: After login, manually click "Dashboard" or "Statistics" in the sidebar. This is expected behavior in Streamlit 1.29.0 (automatic redirect requires newer version).

#### 2. **bcrypt/passlib Warning**
```
passlib/handlers/bcrypt.py:XXX: UserWarning: ...
```
**Solution**: This is harmless and suppressed. The system works correctly.

#### 3. **Pandas Installation Issues (Python 3.13)**
```bash
# Solution: Install build dependencies first
pip install --upgrade pip setuptools wheel
pip install Cython>=3.0.0 numpy>=1.26.0
pip install pandas>=2.2.0
```

---

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



## Acknowledgments

- **Cohere** - For embeddings and LLM capabilities
- **ChromaDB** - For vector database functionality
- **FastAPI** - For the excellent web framework
- **Streamlit** - For rapid dashboard development

---


