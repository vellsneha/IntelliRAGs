# src/chat/manager.py

"""
Chat Management Module

Handles chat session creation, persistence, and management:
- Create and list chat sessions
- Associate documents with chats
- Store conversation history
- Manage chat metadata (timestamps, titles, etc.)
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import uuid


class ChatManager:
    """
    Manages chat sessions and their associated documents and conversations.
    
    Stores:
    - Chat metadata (ID, title, created date, updated date)
    - Documents attached to each chat
    - Conversation history (queries and responses)
    """
    
    def __init__(self, db_path: str = "chats.db"):
        """
        Initialize chat manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with chat-related tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Chats table: stores chat session metadata
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                chat_id TEXT PRIMARY KEY,
                user TEXT NOT NULL,
                title TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Chat documents table: links documents to chats
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE,
                UNIQUE(chat_id, document_id)
            )
        ''')
        
        # Conversation history table: stores Q&A pairs in chats
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                sources TEXT,
                FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
            )
        ''')
        
        # Create indexes for better query performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_chats_user ON chats(user)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_chats_updated ON chats(updated_at)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_chat_docs_chat ON chat_documents(chat_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_conversation_chat ON conversation_history(chat_id)
        ''')
        
        conn.commit()
        conn.close()
    
    def create_chat(self, user: str, title: Optional[str] = None) -> str:
        """
        Create a new chat session.
        
        Args:
            user: Username creating the chat
            title: Optional chat title (defaults to "Chat {timestamp}")
            
        Returns:
            chat_id: Unique identifier for the chat
        """
        chat_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        if not title:
            title = f"Chat {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO chats (chat_id, user, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (chat_id, user, title, timestamp, timestamp))
        
        conn.commit()
        conn.close()
        
        return chat_id
    
    def get_chat(self, chat_id: str) -> Optional[Dict]:
        """Get chat metadata by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM chats WHERE chat_id = ?', (chat_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def list_chats(self, user: str) -> List[Dict]:
        """
        List all chats for a user, sorted by most recently updated.
        
        Args:
            user: Username
            
        Returns:
            List of chat dictionaries with metadata
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT chats.*, 
                   COUNT(chat_documents.id) as document_count,
                   COUNT(conversation_history.id) as message_count
            FROM chats
            LEFT JOIN chat_documents ON chats.chat_id = chat_documents.chat_id
            LEFT JOIN conversation_history ON chats.chat_id = conversation_history.chat_id
            WHERE chats.user = ?
            GROUP BY chats.chat_id
            ORDER BY chats.updated_at DESC
        ''', (user,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def add_document_to_chat(self, chat_id: str, document_id: str, 
                            filename: str, file_path: str) -> bool:
        """
        Associate a document with a chat.
        
        Args:
            chat_id: Chat identifier
            document_id: Document identifier (from ChromaDB)
            filename: Original filename
            file_path: Path to stored file
            
        Returns:
            True if successful
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            timestamp = datetime.utcnow().isoformat()
            cursor.execute('''
                INSERT OR REPLACE INTO chat_documents 
                (chat_id, document_id, filename, file_path, uploaded_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (chat_id, document_id, filename, file_path, timestamp))
            
            # Update chat's updated_at timestamp
            cursor.execute('''
                UPDATE chats SET updated_at = ? WHERE chat_id = ?
            ''', (timestamp, chat_id))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def get_chat_documents(self, chat_id: str) -> List[Dict]:
        """
        Get all documents associated with a chat.
        
        Args:
            chat_id: Chat identifier
            
        Returns:
            List of document dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM chat_documents 
            WHERE chat_id = ?
            ORDER BY uploaded_at DESC
        ''', (chat_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def remove_document_from_chat(self, chat_id: str, document_id: str) -> bool:
        """
        Remove a document from a chat.
        
        Args:
            chat_id: Chat identifier
            document_id: Document identifier
            
        Returns:
            True if successful
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                DELETE FROM chat_documents 
                WHERE chat_id = ? AND document_id = ?
            ''', (chat_id, document_id))
            
            # Update chat's updated_at timestamp
            timestamp = datetime.utcnow().isoformat()
            cursor.execute('''
                UPDATE chats SET updated_at = ? WHERE chat_id = ?
            ''', (timestamp, chat_id))
            
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def add_conversation(self, chat_id: str, question: str, answer: str, 
                        sources: Optional[List[str]] = None) -> int:
        """
        Add a Q&A pair to conversation history.
        
        Args:
            chat_id: Chat identifier
            question: User's question
            answer: Generated answer
            sources: List of source document filenames
            
        Returns:
            Conversation ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.utcnow().isoformat()
        sources_json = json.dumps(sources) if sources else None
        
        cursor.execute('''
            INSERT INTO conversation_history 
            (chat_id, timestamp, question, answer, sources)
            VALUES (?, ?, ?, ?, ?)
        ''', (chat_id, timestamp, question, answer, sources_json))
        
        conversation_id = cursor.lastrowid
        
        # Update chat's updated_at timestamp
        cursor.execute('''
            UPDATE chats SET updated_at = ? WHERE chat_id = ?
        ''', (timestamp, chat_id))
        
        conn.commit()
        conn.close()
        
        return conversation_id if conversation_id is not None else 0
    
    def get_conversation_history(self, chat_id: str) -> List[Dict]:
        """
        Get full conversation history for a chat.
        
        Args:
            chat_id: Chat identifier
            
        Returns:
            List of conversation dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM conversation_history 
            WHERE chat_id = ?
            ORDER BY timestamp ASC
        ''', (chat_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        result = []
        for row in rows:
            conv_dict = dict(row)
            # Parse sources JSON
            if conv_dict.get('sources'):
                try:
                    conv_dict['sources'] = json.loads(conv_dict['sources'])
                except:
                    conv_dict['sources'] = []
            else:
                conv_dict['sources'] = []
            result.append(conv_dict)
        
        return result
    
    def update_chat_title(self, chat_id: str, title: str) -> bool:
        """Update chat title."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE chats SET title = ?, updated_at = ? WHERE chat_id = ?
        ''', (title, datetime.utcnow().isoformat(), chat_id))
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        
        return success
    
    def delete_chat(self, chat_id: str) -> bool:
        """
        Delete a chat and all its associated data.
        
        Cascading deletes will remove documents and conversation history.
        
        Args:
            chat_id: Chat identifier
            
        Returns:
            True if successful
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM chats WHERE chat_id = ?', (chat_id,))
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        
        return success

