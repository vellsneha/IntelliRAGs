# src/analytics/tracker.py

"""
Analytics Tracker Module

Comprehensive analytics system for tracking:
- User queries and responses
- System performance metrics
- User behavior patterns
- System events (uploads, errors, etc.)
- User feedback and ratings

Database: SQLite (lightweight, embedded, no server needed)
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List
from pathlib import Path


class AnalyticsTracker:
    """
    Track and analyze system usage and performance.
    
    Core responsibilities:
    1. Log every query with performance metrics
    2. Track system events (uploads, errors, etc.)
    3. Store user feedback
    4. Generate analytics summaries
    5. Identify usage trends
    """
    
    def __init__(self, db_path: str = "analytics.db"):
        """
        Initialize analytics tracker.
        
        Args:
            db_path: Path to SQLite database file
                    Creates file if doesn't exist
                    Default: "analytics.db" in current directory
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """
        Initialize SQLite database with required tables.
        
        Creates three tables:
        1. queries: All user questions and responses
        2. events: System events (uploads, errors, etc.)
        3. feedback: User ratings on query quality
        
        Uses CREATE TABLE IF NOT EXISTS for safety.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Queries table: stores all user Q&A interactions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user TEXT NOT NULL,
                question TEXT NOT NULL,
                answer_length INTEGER,
                sources_count INTEGER,
                latency_seconds REAL,
                flagged INTEGER DEFAULT 0
            )
        ''')
        
        # Events table: stores system events
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                user TEXT,
                data TEXT
            )
        ''')
        
        # Feedback table: stores user ratings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                query_id INTEGER,
                user TEXT,
                rating INTEGER,
                FOREIGN KEY (query_id) REFERENCES queries(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_query(self, query_data: Dict) -> int:
        """
        Log a user query with performance metrics.
        
        Args:
            query_data: Dictionary containing:
                - user: Username or email
                - question: The question text
                - answer_length: Length of generated answer
                - sources_count: Number of source documents used
                - latency_seconds: Time to generate response
                - flagged: Whether response was flagged (bool)
        
        Returns:
            Database ID of inserted query (for linking feedback)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO queries (timestamp, user, question, answer_length, 
                                sources_count, latency_seconds, flagged)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.utcnow().isoformat(),
            query_data.get('user', 'anonymous'),
            query_data.get('question', ''),
            query_data.get('answer_length', 0),
            query_data.get('sources_count', 0),
            query_data.get('latency_seconds', 0.0),
            1 if query_data.get('flagged', False) else 0
        ))
        
        conn.commit()
        query_id = cursor.lastrowid
        conn.close()
        
        if query_id is None:
            raise RuntimeError("Failed to get query ID from database")
        
        return query_id
    
    def log_event(self, event_type: str, data: Dict):
        """
        Log a system event.
        
        Args:
            event_type: Type of event (e.g., "document_upload", "error")
            data: Dictionary with event details (stored as JSON)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO events (timestamp, event_type, user, data)
            VALUES (?, ?, ?, ?)
        ''', (
            datetime.utcnow().isoformat(),
            event_type,
            data.get('user', 'system'),
            json.dumps(data)
        ))
        
        conn.commit()
        conn.close()
    
    def log_feedback(self, query_id: int, user: str, rating: int):
        """
        Log user feedback on a query response.
        
        Args:
            query_id: ID of the query being rated
            user: Username providing feedback
            rating: Rating (1-5 stars)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO feedback (timestamp, query_id, user, rating)
            VALUES (?, ?, ?, ?)
        ''', (
            datetime.utcnow().isoformat(),
            query_id,
            user,
            rating
        ))
        
        conn.commit()
        conn.close()
    
    def get_summary(self, days: int = 7) -> Dict:
        """
        Generate analytics summary.
        
        Returns comprehensive statistics including:
        - Total queries
        - Average latency
        - Flagged queries count
        - Top users
        - Recent queries
        - Event counts
        
        Args:
            days: Number of days to include (currently not filtered)
        
        Returns:
            Dictionary with all metrics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total queries
        cursor.execute('SELECT COUNT(*) FROM queries')
        total_queries = cursor.fetchone()[0]
        
        # Average latency
        cursor.execute('SELECT AVG(latency_seconds) FROM queries')
        avg_latency = cursor.fetchone()[0] or 0
        
        # Flagged queries
        cursor.execute('SELECT COUNT(*) FROM queries WHERE flagged = 1')
        flagged_count = cursor.fetchone()[0]
        
        # Top users by query count
        cursor.execute('''
            SELECT user, COUNT(*) as query_count 
            FROM queries 
            GROUP BY user 
            ORDER BY query_count DESC 
            LIMIT 5
        ''')
        top_users = [{"user": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        # Recent queries
        cursor.execute('''
            SELECT timestamp, user, question, latency_seconds, flagged
            FROM queries 
            ORDER BY timestamp DESC 
            LIMIT 10
        ''')
        recent_queries = [{
            "timestamp": row[0],
            "user": row[1],
            "question": row[2][:100] + "..." if len(row[2]) > 100 else row[2],
            "latency": row[3],
            "flagged": bool(row[4])
        } for row in cursor.fetchall()]
        
        # Events summary
        cursor.execute('''
            SELECT event_type, COUNT(*) as count
            FROM events
            GROUP BY event_type
        ''')
        events_summary = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            "total_queries": total_queries,
            "avg_latency_seconds": round(avg_latency, 3),
            "flagged_queries": flagged_count,
            "top_users": top_users,
            "recent_queries": recent_queries,
            "events_summary": events_summary,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def get_query_trends(self, days: int = 7) -> List[Dict]:
        """
        Get daily query volume trends.
        
        Args:
            days: Number of days to include
        
        Returns:
            List of dictionaries with date and count
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DATE(timestamp) as date, COUNT(*) as count
            FROM queries
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            GROUP BY DATE(timestamp)
            ORDER BY date
        ''', (days,))
        
        trends = [{"date": row[0], "count": row[1]} for row in cursor.fetchall()]
        conn.close()
        
        return trends


# Test code
if __name__ == "__main__":
    print("📊 Testing Analytics Tracker\n")
    print("=" * 80)
    
    tracker = AnalyticsTracker()
    
    # Test 1: Log some queries
    print("\n1️⃣  Logging test queries...")
    queries = [
        {"user": "john", "question": "What is ML?", "answer_length": 250, "sources_count": 3, "latency_seconds": 1.5, "flagged": False},
        {"user": "sarah", "question": "Vacation policy?", "answer_length": 180, "sources_count": 2, "latency_seconds": 1.2, "flagged": False},
        {"user": "john", "question": "Health benefits?", "answer_length": 300, "sources_count": 4, "latency_seconds": 1.8, "flagged": False},
    ]
    
    for q in queries:
        query_id = tracker.log_query(q)
        print(f"   Logged query {query_id}: {q['question']}")
    
    # Test 2: Log some events
    print("\n2️⃣  Logging test events...")
    tracker.log_event("document_upload", {"user": "admin", "filename": "policy.pdf", "chunks": 12})
    tracker.log_event("document_upload", {"user": "admin", "filename": "handbook.pdf", "chunks": 8})
    print("   Logged 2 document upload events")
    
    # Test 3: Get summary
    print("\n3️⃣  Generating summary...")
    summary = tracker.get_summary()
    
    print(f"\n📊 Summary:")
    print(f"   Total Queries: {summary['total_queries']}")
    print(f"   Avg Latency: {summary['avg_latency_seconds']:.3f}s")
    print(f"   Flagged: {summary['flagged_queries']}")
    
    print(f"\n👥 Top Users:")
    for user in summary['top_users']:
        print(f"   {user['user']}: {user['count']} queries")
    
    print(f"\n📅 Events:")
    for event_type, count in summary['events_summary'].items():
        print(f"   {event_type}: {count}")
    
    print("\n" + "=" * 80)
    print("✅ Analytics tracker working!\n")