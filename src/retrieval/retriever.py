# src/retrieval/retriever.py

"""
Retriever Module - The Heart of RAG

This module implements the complete Retrieval-Augmented Generation pipeline:
1. Semantic Search: Find relevant document chunks
2. Context Preparation: Format chunks for LLM
3. Answer Generation: Use LLM to create response

RAG solves the problem of LLMs not knowing your specific data by:
- Retrieving: Finding relevant information from your documents
- Augmenting: Adding that info to the prompt
- Generating: Creating an answer based on retrieved context
"""

import cohere
import chromadb
from typing import List, Dict
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Retriever:
    """
    Handles document retrieval and answer generation for RAG system.
    
    Architecture:
    ┌─────────┐     ┌──────────┐     ┌─────────┐
    │  Query  │────▶│ Retrieve │────▶│Generate │────▶Answer
    └─────────┘     └──────────┘     └─────────┘
                         │
                         ▼
                    ┌──────────┐
                    │ChromaDB  │
                    │(Vectors) │
                    └──────────┘
    """
    
    def __init__(self):
        """
        Initialize retriever with necessary clients.
        
        Establishes connections to:
        1. Cohere API - for embeddings and text generation
        2. ChromaDB - for vector storage and similarity search
        
        Raises:
            Exception: If ChromaDB collection doesn't exist (no documents ingested)
        """
        # Initialize Cohere client for API calls
        cohere_api_key = os.getenv("COHERE_API_KEY")
        if not cohere_api_key:
            raise ValueError("COHERE_API_KEY environment variable is not set")
        self.co = cohere.Client(cohere_api_key)
        
        # Connect to persistent ChromaDB instance
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        
        # Get the documents collection
        # Note: Using get_collection (not get_or_create) because collection
        # should already exist from document ingestion
        try:
            self.collection = self.chroma_client.get_collection(name="documents")
        except Exception as e:
            raise Exception(
                "Documents collection not found! "
                "Please ingest documents first using DocumentProcessor. "
                f"Error: {e}"
            )
    
    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Retrieve most relevant document chunks using semantic search.
        
        How it works:
        1. Convert query to embedding (vector)
        2. Search ChromaDB for similar embeddings
        3. Return top_k most similar chunks
        
        Similarity is measured using cosine distance:
        - 0.0 = identical
        - 1.0 = completely different
        
        Args:
            query: User's question (e.g., "What is the vacation policy?")
            top_k: Number of chunks to retrieve (default: 5)
                  More chunks = more context but slower
                  Fewer chunks = faster but might miss info
            
        Returns:
            List of dictionaries, each containing:
            - id: Unique chunk identifier
            - text: The actual text of the chunk
            - metadata: Information about source document
            - distance: Similarity score (lower = more similar)
            
        Example:
            >>> retriever = Retriever()
            >>> results = retriever.retrieve("dress code policy", top_k=3)
            >>> for result in results:
            ...     print(f"Distance: {result['distance']:.3f}")
            ...     print(f"Text: {result['text'][:100]}...")
            Distance: 0.123
            Text: Our dress code is business casual. Employees should...
        """
        
        # Step 1: Generate query embedding
        # Use 'search_query' input type (optimized for questions)
        query_embedding = self.co.embed(
            texts=[query],  # Must be a list (even for single query)
            model='embed-english-v3.0',  # Cohere's embedding model
            input_type='search_query'  # Different from 'search_document'!
        ).embeddings[0]  # Extract first (and only) embedding
        
        # Step 2: Query ChromaDB for similar vectors
        results = self.collection.query(
            query_embeddings=[query_embedding],  # List of query vectors
            n_results=top_k  # How many results to return
        )
        
        # Step 3: Format results into clean list of dictionaries
        # ChromaDB returns nested lists, we flatten for easier use
        retrieved_docs = []
        ids = results.get('ids')
        documents = results.get('documents')
        metadatas = results.get('metadatas')
        distances = results.get('distances')
        
        if not ids or not ids[0]:
            return retrieved_docs  # No results found
        
        for i in range(len(ids[0])):
            retrieved_docs.append({
                "id": ids[0][i],
                "text": documents[0][i] if documents and documents[0] else "",
                "metadata": metadatas[0][i] if metadatas and metadatas[0] else {},
                "distance": distances[0][i] if distances and distances[0] else 0.0
            })
        
        return retrieved_docs
    
    def generate_answer(self, query: str, context_docs: List[Dict]) -> Dict:
        """
        Generate answer using LLM with retrieved context.
        
        This is where the "Generation" in RAG happens!
        
        Process:
        1. Format retrieved chunks into context string
        2. Create prompt with instructions, context, and question
        3. Call Cohere's LLM
        4. Return answer with sources
        
        Prompt Engineering Tips:
        - Be explicit about what to do
        - Provide clear structure (Context, Question, Answer)
        - Handle edge cases (what if answer not in context?)
        - Keep it simple but comprehensive
        
        Args:
            query: User's question
            context_docs: List of retrieved chunks from retrieve()
            
        Returns:
            Dictionary containing:
            - answer: Generated response from LLM
            - sources: List of source documents used
            - context_used: Number of chunks provided to LLM
            
        Example:
            >>> context = retriever.retrieve("vacation policy", top_k=3)
            >>> result = retriever.generate_answer("vacation policy", context)
            >>> print(result['answer'])
            "Full-time employees receive 15 days of vacation..."
            >>> print(result['sources'])
            ['employee_handbook.pdf']
        """
        
        # Step 1: Prepare context from retrieved documents
        # Format each chunk with a number for reference
        context = "\n\n".join([
            f"Document {i+1}:\n{doc['text']}" 
            for i, doc in enumerate(context_docs)
        ])
        
        # Why enumerate? Gives us (index, value) pairs:
        # enumerate(['a', 'b', 'c']) → (0, 'a'), (1, 'b'), (2, 'c')
        
        # Step 2: Create the prompt
        # This is CRITICAL - good prompts = good answers!
        prompt = f"""Based on the following context documents, answer the user's question. 
If the answer cannot be found in the context, say so clearly.
Be concise but complete. Use information only from the provided context.

Context:
{context}

Question: {query}

Answer:"""
        
        # Prompt breakdown:
        # - "Based on..." = Grounds the answer in context
        # - "If not found..." = Prevents hallucination
        # - "Be concise..." = Controls output style
        # - Clear sections = Helps LLM understand structure
        
        # Step 3: Call Cohere's chat model
        # Note: command-r-plus is the current recommended model (command-r was deprecated Sept 2025)
        response = self.co.chat(
            message=prompt,  # The complete prompt
            model='command-r7b-12-2024',  # Cohere's instruction-following model
            temperature=0.3  # Low = more deterministic, high = more creative
        )
        
        # Temperature guide:
        # 0.0-0.3: Factual tasks (RAG, Q&A) ← We use this
        # 0.4-0.7: Balanced (chatbots, summarization)
        # 0.8-1.0: Creative tasks (stories, brainstorming)
        
        # Step 4: Extract and format results
        return {
            "answer": response.text,  # The generated answer
            "sources": [doc['metadata']['source'] for doc in context_docs],  # Where info came from
            "context_used": len(context_docs)  # How many chunks we used
        }
    
    def answer_question(self, query: str) -> Dict:
        """
        Complete RAG pipeline - this is the main method!
        
        Orchestrates the full process:
        1. Retrieve relevant chunks (semantic search)
        2. Generate answer (LLM with context)
        3. Return comprehensive results
        
        This method combines retrieve() and generate_answer() into
        a single convenient interface.
        
        Args:
            query: User's natural language question
            
        Returns:
            Dictionary containing:
            - answer: Generated response
            - sources: List of source files
            - context_used: Number of chunks used
            - retrieved_docs: Full details of retrieved chunks (for debugging)
            
        Example Usage:
            >>> retriever = Retriever()
            >>> 
            >>> # Simple usage
            >>> result = retriever.answer_question("What is the dress code?")
            >>> print(result['answer'])
            >>> 
            >>> # With source verification
            >>> result = retriever.answer_question("How many sick days?")
            >>> print(f"Answer: {result['answer']}")
            >>> print(f"Sources: {', '.join(result['sources'])}")
            >>> 
            >>> # Debugging
            >>> result = retriever.answer_question("Remote work policy?")
            >>> for doc in result['retrieved_docs']:
            ...     print(f"Chunk {doc['id']}: distance={doc['distance']:.3f}")
        """
        
        # Step 1: Retrieve relevant documents using semantic search
        # top_k=5 is a good default (adjust based on your needs)
        docs = self.retrieve(query, top_k=5)
        
        # Step 2: Generate answer using retrieved docs
        result = self.generate_answer(query, docs)
        
        # Step 3: Add retrieved docs for transparency/debugging
        # This allows users to see exactly what context was used
        result['retrieved_docs'] = docs
        
        # Why include retrieved_docs?
        # - Transparency: Users see what info was used
        # - Debugging: Check if right chunks were found
        # - Citations: Can show exact sources
        # - Trust: Builds confidence in system
        
        return result


# Test code - runs when you execute this file directly
if __name__ == "__main__":
    """
    Test the retriever with sample queries.
    
    Prerequisites:
    - Documents must be ingested first using DocumentProcessor
    - COHERE_API_KEY must be set in .env file
    """
    
    print("🧪 Testing Retriever\n")
    print("=" * 60)
    
    try:
        # Initialize retriever
        retriever = Retriever()
        print("✅ Retriever initialized successfully\n")
        
        # Test question
        query = "What is machine learning?"
        print(f"📝 Query: '{query}'\n")
        
        # Get answer
        result = retriever.answer_question(query)
        
        # Display results
        print("🤖 Answer:")
        print(result['answer'])
        print(f"\n📚 Sources: {', '.join(set(result['sources']))}")
        print(f"📊 Chunks used: {result['context_used']}")
        
        print("\n" + "=" * 60)
        print("🔍 Retrieved Chunks (for debugging):\n")
        
        for i, doc in enumerate(result['retrieved_docs'], 1):
            print(f"Chunk {i}:")
            print(f"  Distance: {doc['distance']:.4f}")
            print(f"  Text: {doc['text'][:150]}...")
            print(f"  Source: {doc['metadata'].get('source', 'unknown')}")
            print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Make sure you've:")
        print("   1. Ingested documents using DocumentProcessor")
        print("   2. Set COHERE_API_KEY in .env file")
        print("   3. Installed all dependencies")