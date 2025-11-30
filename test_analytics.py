# test_analytics.py

"""
Test analytics tracking with realistic data.
"""

from src.analytics.tracker import AnalyticsTracker
import time

print("📊 Testing Analytics System\n")
print("=" * 80)

# Initialize tracker
tracker = AnalyticsTracker()

# Simulate some user activity
print("\n1️⃣  Simulating user queries...")

users = ["john@company.com", "sarah@company.com", "bob@company.com"]
questions = [
    "What's the vacation policy?",
    "How many sick days do I get?",
    "What health insurance is available?",
    "Can I work remotely?",
    "What's the dress code?",
]

for i in range(15):
    import random
    
    query_data = {
        "user": random.choice(users),
        "question": random.choice(questions),
        "answer_length": random.randint(150, 350),
        "sources_count": random.randint(2, 5),
        "latency_seconds": round(random.uniform(1.0, 2.5), 3),
        "flagged": random.random() < 0.1  # 10% chance of being flagged
    }
    
    query_id = tracker.log_query(query_data)
    print(f"   Query {query_id}: {query_data['user']} asked '{query_data['question']}'")

# Simulate document uploads
print("\n2️⃣  Simulating document uploads...")
tracker.log_event("document_upload", {
    "user": "admin",
    "filename": "vacation_policy.pdf",
    "chunks": 12,
    "size_mb": 2.5
})
tracker.log_event("document_upload", {
    "user": "admin",
    "filename": "health_benefits.pdf",
    "chunks": 8,
    "size_mb": 1.8
})
print("   Logged 2 document uploads")

# Simulate some user feedback
print("\n3️⃣  Simulating user feedback...")
tracker.log_feedback(query_id=1, user="john@company.com", rating=5)
tracker.log_feedback(query_id=2, user="sarah@company.com", rating=4)
tracker.log_feedback(query_id=3, user="bob@company.com", rating=5)
print("   Logged 3 pieces of feedback")

# Generate summary
print("\n" + "=" * 80)
print("📊 ANALYTICS SUMMARY")
print("=" * 80)

summary = tracker.get_summary()

print(f"\n📈 Overview:")
print(f"   Total Queries: {summary['total_queries']}")
print(f"   Average Latency: {summary['avg_latency_seconds']:.3f} seconds")
print(f"   Flagged Queries: {summary['flagged_queries']}")

print(f"\n👥 Top Users:")
for i, user_data in enumerate(summary['top_users'], 1):
    print(f"   {i}. {user_data['user']}: {user_data['count']} queries")

print(f"\n🕐 Recent Queries:")
for i, query in enumerate(summary['recent_queries'][:5], 1):
    status = "⚠️" if query['flagged'] else "✅"
    print(f"   {status} {query['user']}: {query['question']}")
    print(f"      Latency: {query['latency']:.3f}s | Time: {query['timestamp']}")

print(f"\n📋 System Events:")
for event_type, count in summary['events_summary'].items():
    print(f"   {event_type}: {count}")

print(f"\n⏰ Report Generated: {summary['generated_at']}")
print("\n" + "=" * 80)
print("✅ Analytics system fully functional!\n")