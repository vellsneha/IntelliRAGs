# test_rag.py

"""
Complete RAG System Test

This script demonstrates the full pipeline:
1. Ingest documents
2. Ask questions
3. Get answers with sources
"""

from src.ingestion.document_processor import DocumentProcessor
from src.retrieval.retriever import Retriever

# Step 1: Create and ingest sample documents
print("📄 Creating sample documents...\n")

# Create sample policy document
with open("vacation_policy.txt", "w") as f:
    f.write("""
    VACATION POLICY
    
    Our company provides generous vacation benefits for all employees.
    
    Full-time employees receive 15 days of paid vacation annually.
    Part-time employees receive vacation days prorated based on their hours worked.
    
    Vacation requests must be submitted at least 2 weeks in advance through the HR portal.
    Employees can roll over up to 5 unused vacation days to the following year.
    
    During the first year of employment, vacation days accrue at a rate of 1.25 days per month.
    """)

# Create sample benefits document
with open("health_benefits.txt", "w") as f:
    f.write("""
    HEALTH BENEFITS
    
    We offer comprehensive health insurance coverage for all full-time employees.
    
    Medical insurance covers doctor visits, hospital stays, and prescription medications.
    Dental insurance includes preventive care, fillings, and major procedures.
    Vision insurance covers eye exams and prescription glasses or contacts.
    
    Employees can choose from three plan tiers: Bronze, Silver, and Gold.
    The company covers 80% of premiums for Bronze plans, 70% for Silver, and 60% for Gold.
    
    Health insurance coverage begins on the first day of the month following your start date.
    """)

# Step 2: Ingest documents
print("⚙️  Ingesting documents...\n")
processor = DocumentProcessor()

result1 = processor.ingest_document("vacation_policy.txt", 
                                   metadata={"type": "policy", "department": "HR"})
print(f"✅ Ingested vacation_policy.txt: {result1['chunks_created']} chunks")

result2 = processor.ingest_document("health_benefits.txt",
                                   metadata={"type": "benefits", "department": "HR"})
print(f"✅ Ingested health_benefits.txt: {result2['chunks_created']} chunks")

# Step 3: Initialize retriever
print("\n🔍 Initializing retriever...\n")
retriever = Retriever()

# Step 4: Ask questions!
print("=" * 80)
print("💬 ASKING QUESTIONS")
print("=" * 80)

questions = [
    "How many vacation days do full-time employees get?",
    "What health insurance plans are available?",
    "Can I roll over unused vacation days?",
    "When does health insurance start?",
    "What is the remote work policy?"  # This one isn't in our docs!
]

for i, question in enumerate(questions, 1):
    print(f"\n\n{'─' * 80}")
    print(f"Question {i}: {question}")
    print('─' * 80)
    
    # Get answer
    result = retriever.answer_question(question)
    
    # Display answer
    print(f"\n🤖 Answer:\n{result['answer']}")
    
    # Display sources
    unique_sources = set(result['sources'])
    print(f"\n📚 Sources: {', '.join(unique_sources)}")
    
    # Show retrieval quality
    print(f"\n📊 Retrieval Details:")
    print(f"   Chunks used: {result['context_used']}")
    print(f"   Best match distance: {result['retrieved_docs'][0]['distance']:.4f}")

print("\n\n" + "=" * 80)
print("✅ Testing complete!")
print("=" * 80)