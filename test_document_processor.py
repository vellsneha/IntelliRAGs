# test_processor.py
from src.ingestion.document_processor import DocumentProcessor

# Create a simple test document
with open("sample.txt", "w") as f:
    f.write("""
    Our company vacation policy is as follows:
    All full-time employees receive 15 days of paid vacation per year.
    Part-time employees receive vacation days prorated based on hours worked.
    Vacation requests must be submitted at least 2 weeks in advance.
    Our company vacation policy is as follows:
    All full-time employees receive 15 days of paid vacation per year.
    Part-time employees receive vacation days prorated based on hours worked.
    Vacation requests must be submitted at least 2 weeks in advance.
    Our company vacation policy is as follows:
    All full-time employees receive 15 days of paid vacation per year.
    Part-time employees receive vacation days prorated based on hours worked.
    Vacation requests must be submitted at least 2 weeks in advance.
    """)

# Initialize processor
processor = DocumentProcessor()

# Test ingestion
result = processor.ingest_document("sample.txt", metadata={"type": "policy"})
print("Ingestion result:", result)