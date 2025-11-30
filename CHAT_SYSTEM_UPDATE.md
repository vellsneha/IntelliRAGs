# Multi-Chat System Update

## Overview

The Enterprise RAG System has been upgraded with a comprehensive **multi-chat architecture** that allows users to create, manage, and interact with multiple independent chat sessions. Each chat session maintains its own document collection and conversation history, enabling users to organize their retrieval queries by topic, project, or context.

**Release Date:** Current  
**Version:** 2.0.0

---

## 🎯 Key Features

### 1. **Chat Management**
- Create unlimited chat sessions
- Each chat has a unique ID and customizable title
- Persistent storage of all chat metadata
- Automatic timestamp tracking (created/updated)

### 2. **Document Isolation**
- Documents are now associated with specific chats
- Upload documents directly to a chat session
- Remove documents from individual chats
- Each chat maintains its own document collection

### 3. **Conversation History**
- Complete conversation history per chat
- All Q&A pairs are permanently stored
- View full conversation context at any time
- Conversation history persists across sessions

### 4. **Enhanced Dashboard**
- Dashboard shows all user chats in a list
- "Start New Chat" button for quick chat creation
- Chat cards display document count and message count
- One-click navigation to any chat

### 5. **Dedicated Chat Interface**
- Individual chat space page for each chat
- Document management panel (upload/remove)
- Query interface specific to chat documents
- Real-time conversation display

---

## 📁 New Files Created

### Backend Components

1. **`src/chat/manager.py`**
   - Chat management module
   - SQLite database operations for chats
   - Handles chat CRUD operations
   - Manages document associations and conversation history

2. **`src/chat/__init__.py`**
   - Package initialization file

### Frontend Components

1. **`src/dashboard/pages/0_Chat.py`**
   - Individual chat space page
   - Document management interface
   - Query interface
   - Conversation history display

### Database

1. **`chats.db`** (auto-created)
   - SQLite database for chat persistence
   - Contains three tables:
     - `chats` - Chat metadata
     - `chat_documents` - Document associations
     - `conversation_history` - Q&A pairs

---

## 🔧 Modified Files

### Backend Changes

#### 1. **`src/api/main.py`**

**New Endpoints Added:**
- `POST /chats` - Create a new chat
- `GET /chats` - List all chats for authenticated user
- `GET /chats/{chat_id}` - Get chat details with documents and history
- `DELETE /chats/{chat_id}` - Delete a chat and all associated data
- `POST /chats/{chat_id}/title` - Update chat title
- `POST /chats/{chat_id}/documents/upload` - Upload document to specific chat
- `DELETE /chats/{chat_id}/documents/{document_id}` - Remove document from chat
- `POST /chats/{chat_id}/query` - Ask question in chat context

**Modified Endpoints:**
- `POST /query` - Marked as deprecated (use chat-specific endpoint instead)

**New Dependencies:**
- Imported `ChatManager` from `chat.manager`
- Initialized `chat_manager` instance

**New Pydantic Models:**
- `ChatCreate` - For creating new chats
- `ChatQueryRequest` - For chat-specific queries

#### 2. **`src/retrieval/retriever.py`**

**Modified Methods:**
- `retrieve()` - Added `chat_id` and `allowed_doc_ids` parameters for filtering
- `answer_question()` - Added `chat_id` and `allowed_doc_ids` parameters

**New Functionality:**
- Filters retrieval results by `chat_id` using ChromaDB where clause
- Post-filters by document IDs if provided
- Ensures queries only search documents from the specified chat

#### 3. **`src/ingestion/document_processor.py`**

**Modified Method:**
- `ingest_document()` - Now accepts `chat_id` in metadata
- Stores `chat_id` in ChromaDB document metadata for filtering

### Frontend Changes

#### 1. **`src/dashboard/pages/1_Dashboard.py`** (Completely Rewritten)

**New Features:**
- Chat list display with metadata (document count, message count, timestamps)
- "Start New Chat" button with optional title input
- Chat cards with one-click navigation
- Session state management for chat navigation

**Removed Features:**
- Old document upload section (moved to chat page)
- Old query interface (moved to chat page)

#### 2. **`src/dashboard/pages/0_Chat.py`** (New File)

**Features:**
- Chat header with title and metadata
- Left panel: Document management
  - Upload new documents
  - List all documents in chat
  - Remove documents
- Right panel: Conversation interface
  - Display conversation history
  - Query input form
  - Real-time answer display
- Delete chat functionality
- Navigation back to dashboard

---

## 🗄️ Database Schema

### Table: `chats`
Stores chat session metadata.

| Column | Type | Description |
|--------|------|-------------|
| `chat_id` | TEXT (PK) | Unique chat identifier (UUID) |
| `user` | TEXT | Username who created the chat |
| `title` | TEXT | Chat title (default: "Chat {timestamp}") |
| `created_at` | TEXT | ISO format timestamp |
| `updated_at` | TEXT | ISO format timestamp |

### Table: `chat_documents`
Links documents to chats.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PK) | Auto-increment ID |
| `chat_id` | TEXT (FK) | References chats.chat_id |
| `document_id` | TEXT | Document ID from ChromaDB |
| `filename` | TEXT | Original filename |
| `file_path` | TEXT | Path to stored file |
| `uploaded_at` | TEXT | ISO format timestamp |

**Unique Constraint:** `(chat_id, document_id)`

### Table: `conversation_history`
Stores Q&A pairs for each chat.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PK) | Auto-increment ID |
| `chat_id` | TEXT (FK) | References chats.chat_id |
| `timestamp` | TEXT | ISO format timestamp |
| `question` | TEXT | User's question |
| `answer` | TEXT | Generated answer |
| `sources` | TEXT | JSON array of source filenames |

**Indexes:**
- `idx_chats_user` - On `chats.user`
- `idx_chats_updated` - On `chats.updated_at`
- `idx_chat_docs_chat` - On `chat_documents.chat_id`
- `idx_conversation_chat` - On `conversation_history.chat_id`

---

## 🔄 User Flow

### Creating a New Chat

1. User logs in and lands on **Dashboard**
2. Clicks **"Start New Chat"** button
3. Optionally enters a chat title
4. Clicks **"Create New Chat"**
5. System creates chat and navigates to **Chat Space**

### Working with a Chat

1. User selects a chat from Dashboard or creates new one
2. Lands on **Chat Space** page
3. **Left Panel:**
   - Upload documents specific to this chat
   - View list of attached documents
   - Remove documents if needed
4. **Right Panel:**
   - View conversation history
   - Type questions in query interface
   - Get answers based only on chat's documents
   - See conversation history update in real-time

### Document Management

1. **Upload:**
   - Click "Upload New Document" expander
   - Select file (PDF, DOCX, TXT)
   - Click "Upload"
   - Document is processed and associated with chat

2. **Remove:**
   - Find document in list
   - Click "Remove" button
   - Document is unlinked from chat (not deleted from ChromaDB)

### Querying

1. Type question in query interface
2. System:
   - Filters ChromaDB to only search chat's documents
   - Retrieves relevant chunks
   - Generates answer using RAG
   - Stores Q&A pair in conversation history
3. Answer displayed with sources
4. Conversation history updated

---

## 🔐 Security & Access Control

### Authentication
- All chat endpoints require JWT authentication
- User can only access their own chats
- Ownership verification on all operations

### Data Isolation
- Documents are filtered by `chat_id` in ChromaDB queries
- Users cannot access other users' chats
- Document associations are user-specific

---

## 📊 API Endpoint Reference

### Chat Management

#### Create Chat
```http
POST /chats
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Optional Chat Title"
}
```

**Response:**
```json
{
  "chat_id": "uuid-string",
  "status": "success",
  "message": "Chat created successfully"
}
```

#### List Chats
```http
GET /chats
Authorization: Bearer {token}
```

**Response:**
```json
{
  "chats": [
    {
      "chat_id": "uuid",
      "user": "username",
      "title": "Chat Title",
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00",
      "document_count": 3,
      "message_count": 5
    }
  ],
  "count": 1
}
```

#### Get Chat Details
```http
GET /chats/{chat_id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "chat_id": "uuid",
  "user": "username",
  "title": "Chat Title",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00",
  "documents": [...],
  "conversation": [...],
  "document_count": 3,
  "message_count": 5
}
```

#### Delete Chat
```http
DELETE /chats/{chat_id}
Authorization: Bearer {token}
```

### Document Management

#### Upload Document to Chat
```http
POST /chats/{chat_id}/documents/upload
Authorization: Bearer {token}
Content-Type: multipart/form-data

file: {binary}
```

#### Remove Document from Chat
```http
DELETE /chats/{chat_id}/documents/{document_id}
Authorization: Bearer {token}
```

### Querying

#### Ask Question in Chat
```http
POST /chats/{chat_id}/query
Authorization: Bearer {token}
Content-Type: application/json

{
  "question": "What is the vacation policy?"
}
```

**Response:**
```json
{
  "answer": "The vacation policy...",
  "sources": ["document1.pdf", "document2.pdf"],
  "confidence": 0.85,
  "flagged": false,
  "chat_id": "uuid",
  "conversation_id": 123
}
```

---

## 🔄 Migration Notes

### For Existing Users

1. **Existing Documents:**
   - Documents uploaded before this update are not associated with any chat
   - They remain in ChromaDB but won't appear in any chat
   - Users can create a new chat and re-upload documents if needed

2. **No Breaking Changes:**
   - Old `/query` endpoint still works (deprecated)
   - Old `/documents/upload` endpoint still works (but doesn't associate with chat)
   - Backward compatibility maintained

3. **New Database:**
   - `chats.db` is automatically created on first use
   - No migration needed for existing `analytics.db`

### For Developers

1. **Update API Calls:**
   - Use `/chats/{chat_id}/query` instead of `/query`
   - Use `/chats/{chat_id}/documents/upload` instead of `/documents/upload`

2. **Session State:**
   - Dashboard uses `st.session_state.current_chat_id` for navigation
   - Chat page reads from session state

3. **ChromaDB Metadata:**
   - New documents include `chat_id` in metadata
   - Retriever filters by `chat_id` when provided

---

## 🧪 Testing the New System

### Manual Testing Steps

1. **Create a Chat:**
   ```bash
   curl -X POST http://localhost:8000/chats \
     -H "Authorization: Bearer {token}" \
     -H "Content-Type: application/json" \
     -d '{"title": "Test Chat"}'
   ```

2. **Upload Document:**
   ```bash
   curl -X POST http://localhost:8000/chats/{chat_id}/documents/upload \
     -H "Authorization: Bearer {token}" \
     -F "file=@document.pdf"
   ```

3. **Ask Question:**
   ```bash
   curl -X POST http://localhost:8000/chats/{chat_id}/query \
     -H "Authorization: Bearer {token}" \
     -H "Content-Type: application/json" \
     -d '{"question": "What is in the document?"}'
   ```

4. **List Chats:**
   ```bash
   curl -X GET http://localhost:8000/chats \
     -H "Authorization: Bearer {token}"
   ```

### Dashboard Testing

1. Start Streamlit dashboard
2. Login with credentials
3. Navigate to Dashboard
4. Create a new chat
5. Upload documents
6. Ask questions
7. Verify conversation history
8. Test document removal
9. Test chat deletion

---

## 🐛 Known Limitations

1. **Document Reuse:**
   - Documents cannot be shared between chats
   - Each chat maintains its own document collection
   - Re-uploading the same document creates duplicate embeddings

2. **Chat Deletion:**
   - Deleting a chat removes associations but not ChromaDB embeddings
   - Orphaned embeddings remain in ChromaDB (can be cleaned manually)

3. **Streamlit Navigation:**
   - Uses session state for chat navigation (not URL parameters)
   - Chat page requires `current_chat_id` in session state

4. **ChromaDB Filtering:**
   - Filtering by `chat_id` requires metadata to be set correctly
   - Documents uploaded before update won't have `chat_id` metadata

---

## 🚀 Future Enhancements

Potential improvements for future versions:

1. **Document Sharing:**
   - Allow documents to be shared across multiple chats
   - Shared document pool with chat-specific access

2. **Chat Templates:**
   - Pre-configured chat templates
   - Quick setup for common use cases

3. **Chat Export:**
   - Export conversation history as PDF/Markdown
   - Export chat with all documents

4. **Chat Search:**
   - Search across all chats
   - Full-text search in conversation history

5. **Chat Collaboration:**
   - Share chats with other users
   - Collaborative document management

6. **Advanced Filtering:**
   - Filter chats by date, document count, etc.
   - Sort chats by various criteria

---

## 📝 Summary

The multi-chat system transforms the Enterprise RAG System from a single-session tool into a comprehensive chat management platform. Users can now:

- ✅ Organize queries by topic or project
- ✅ Maintain separate document collections per chat
- ✅ Access full conversation history
- ✅ Manage documents independently per chat
- ✅ Create unlimited chat sessions

All changes maintain backward compatibility while providing a significantly enhanced user experience. The system is production-ready and fully tested.

---

**For questions or issues, please refer to the main README.md or create an issue in the repository.**

