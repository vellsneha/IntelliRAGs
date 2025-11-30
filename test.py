# test_api.py

"""
Python script to test all API endpoints.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

print("🧪 Testing Enterprise RAG API\n")
print("=" * 80)

# Test 1: Health Check
print("\n1️⃣  Health Check")
response = requests.get(f"{BASE_URL}/")
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

# Test 2: Login
print("\n2️⃣  Login")
response = requests.post(
    f"{BASE_URL}/auth/login",
    json={"username": "demo", "password": "demo123"}
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    token_data = response.json()
    print(f"Token received: {token_data['access_token'][:20]}...")
else:
    print(f"Error: {response.text}")
    print("Make sure the FastAPI server is running with: uvicorn src.api.main:app --reload")
    exit(1)

token = token_data['access_token']
headers = {"Authorization": f"Bearer {token}"}

# Test 3: Upload Document
print("\n3️⃣  Upload Document")
# Create a test document first
with open("test_document.txt", "w") as f:
    f.write("Our vacation policy provides 15 days of paid time off for full-time employees.")

with open("test_document.txt", "rb") as f:
    files = {"file": ("test_document.txt", f, "text/plain")}
    response = requests.post(
        f"{BASE_URL}/documents/upload",
        headers=headers,
        files=files
    )
    
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

# Test 4: Ask Question
print("\n4️⃣  Ask Question")
response = requests.post(
    f"{BASE_URL}/query",
    headers=headers,
    json={"question": "How many vacation days do employees get?"}
)
print(f"Status: {response.status_code}")
result = response.json()
print(f"Answer: {result['answer']}")
print(f"Sources: {result['sources']}")
print(f"Flagged: {result['flagged']}")

# Test 5: Analytics
print("\n5️⃣  Analytics Summary")
response = requests.get(
    f"{BASE_URL}/analytics/summary",
    headers=headers
)
print(f"Status: {response.status_code}")
summary = response.json()
print(f"Total Queries: {summary['total_queries']}")
print(f"Avg Latency: {summary['avg_latency_seconds']}s")

print("\n" + "=" * 80)
print("✅ All tests complete!\n")