# src/ingestion/document_processor.py

"""
Document Processor Module

This module handles the complete document ingestion pipeline:
1. Extract text from various file formats (PDF, DOCX, TXT)
2. Split text into manageable chunks
3. Generate embeddings using Cohere
4. Store in ChromaDB for semantic search

Key Concepts:
- Embeddings: Converting text to numerical vectors that capture meaning
- Chunking: Splitting documents into smaller pieces for better retrieval
- Vector Database: Storing embeddings for fast similarity search
"""

import hashlib
from pathlib import Path
from typing import List, Dict, Optional, cast, Any
import numpy as np
import PyPDF2
from docx import Document
import cohere
import chromadb
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()


class DocumentProcessor:
    """
    Handles document ingestion and processing for RAG system.
    
    This class provides methods to:
    - Read different document formats
    - Split text into chunks with overlap
    - Generate embeddings
    - Store in vector database
    """
    
    def __init__(self):
        """
        Initialize the document processor.
        
        Creates connections to:
        1. Cohere API (for embeddings)
        2. ChromaDB (for storage)
        """
        # Initialize Cohere client with API key from environment
        cohere_api_key = os.getenv("COHERE_API_KEY")
        if not cohere_api_key:
            raise ValueError("COHERE_API_KEY environment variable is not set")
        self.co = cohere.Client(cohere_api_key)
        
        # Initialize ChromaDB with persistent storage
        # PersistentClient = saves data to disk (survives restarts)
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        
        # Get or create collection for storing documents
        # Collection = like a table in traditional databases
        self.collection = self.chroma_client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity for search
        )
    
    def extract_text(self, file_path: str) -> str:
        """
        Extract text from PDF, DOCX, or TXT files.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Extracted text as a string
            
        Raises:
            ValueError: If file type is not supported
            
        Example:
            >>> processor = DocumentProcessor()
            >>> text = processor.extract_text("document.pdf")
            >>> print(len(text))
            5000
        """
        # Convert string path to Path object for easier manipulation
        path = Path(file_path)
        
        # Route to appropriate extraction method based on file extension
        if path.suffix.lower() == '.pdf':
            return self._extract_pdf(file_path)
        elif path.suffix.lower() in ['.docx', '.doc']:
            return self._extract_docx(file_path)
        elif path.suffix.lower() == '.txt':
            # For plain text, just read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # Unsupported file type
            raise ValueError(f"Unsupported file type: {path.suffix}")
    
    def _extract_pdf(self, file_path: str) -> str:
        """
        Extract text from PDF file.
        
        Note: Underscore prefix indicates this is a private method
        (should only be called internally by extract_text)
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Text extracted from all pages
        """
        text = []  # List to collect text from each page
        
        # Open PDF in binary mode ('rb' = read binary)
        with open(file_path, 'rb') as file:
            # Create PDF reader object
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Iterate through each page
            for page in pdf_reader.pages:
                # Extract text from current page and add to list
                text.append(page.extract_text())
        
        # Join all pages with newline separators
        return "\n".join(text)
    
    def _extract_docx(self, file_path: str) -> str:
        """
        Extract text from Microsoft Word (DOCX) file.
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            Text extracted from all paragraphs
        """
        # Open Word document
        doc = Document(file_path)
        
        # Extract text from each paragraph and join with newlines
        # List comprehension: [expression for item in iterable]
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Chunking is crucial for RAG because:
        1. LLMs have token limits (can't process entire long documents)
        2. Smaller chunks = more precise retrieval
        3. Overlap preserves context across boundaries
        
        Args:
            text: The text to split
            chunk_size: Number of words per chunk (default: 500)
            overlap: Number of words to overlap between chunks (default: 50)
            
        Returns:
            List of text chunks
            
        Example:
            >>> text = "The quick brown fox jumps over the lazy dog"
            >>> chunks = processor.chunk_text(text, chunk_size=5, overlap=2)
            >>> print(chunks[0])
            "The quick brown fox jumps"
            >>> print(chunks[1])
            "fox jumps over the lazy"  # Overlaps with "fox jumps"
        """
        # Split text into individual words
        words = text.split()
        
        # List to store chunks
        chunks = []
        
        # Sliding window approach:
        # Start at 0, move by (chunk_size - overlap) each step
        # This creates overlap between consecutive chunks
        for i in range(0, len(words), chunk_size - overlap):
            # Extract chunk_size words starting at position i
            # Slicing: words[start:end] gets items from start to end-1
            chunk = " ".join(words[i:i + chunk_size])
            
            # Only add non-empty chunks
            # .strip() removes leading/trailing whitespace
            if chunk.strip():
                chunks.append(chunk)
        
        return chunks
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings using Cohere's API.
        
        Embeddings are numerical representations of text that capture semantic meaning.
        Similar texts will have similar embeddings (close together in vector space).
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors (each vector is a list of floats)
            
        Example:
            >>> texts = ["hello world", "goodbye world"]
            >>> embeddings = processor.generate_embeddings(texts)
            >>> print(len(embeddings))
            2
            >>> print(len(embeddings[0]))
            1024  # Embedding dimension
        """
        # Call Cohere's embedding API
        response = self.co.embed(
            texts=texts,
            model='embed-english-v3.0',  # Cohere's English embedding model
            input_type='search_document'  # Optimized for document storage
        )
        
        # Return the embedding vectors
        return response.embeddings
    
    def ingest_document(self, file_path: str, metadata: Optional[Dict] = None) -> Dict:
        """
        Complete document ingestion pipeline.
        
        This is the main method that orchestrates the entire process:
        1. Extract text from file
        2. Chunk the text
        3. Generate embeddings
        4. Store in vector database
        
        Args:
            file_path: Path to document file
            metadata: Optional additional metadata to store with document
            
        Returns:
            Dictionary with ingestion results:
            {
                "doc_id": "unique_document_id",
                "chunks_created": 12,
                "status": "success"
            }
            
        Example:
            >>> processor = DocumentProcessor()
            >>> result = processor.ingest_document(
            ...     "company_policy.pdf",
            ...     metadata={"department": "HR", "year": 2024}
            ... )
            >>> print(result)
            {'doc_id': '5d41402...', 'chunks_created': 12, 'status': 'success'}
        """
        # Step 1: Extract text from file
        text = self.extract_text(file_path)
        
        # Step 2: Split text into chunks
        chunks = self.chunk_text(text)
        
        # Step 3: Generate embeddings for all chunks
        # We batch this operation for efficiency
        embeddings_list = self.generate_embeddings(chunks)
        
        # Convert embeddings to numpy array for ChromaDB compatibility
        # ChromaDB accepts numpy arrays or lists of sequences
        embeddings = np.array(embeddings_list, dtype=np.float32)
        
        # Step 4: Create unique document ID using hash of file path
        # MD5 hash creates a unique fingerprint for the file
        doc_id = hashlib.md5(file_path.encode()).hexdigest()
        
        # Step 5: Prepare metadata
        # Base metadata that all chunks share
        base_metadata = {
            "source": file_path,
            "doc_id": doc_id,
            "num_chunks": len(chunks)
        }
        # Add any additional metadata provided by user (including chat_id if provided)
        if metadata:
            base_metadata.update(metadata)
        
        # Step 6: Create unique IDs for each chunk
        # Format: {doc_id}_chunk_{chunk_number}
        ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        
        # Step 7: Create metadata list (one copy per chunk)
        # .copy() creates a new dict to avoid shared references
        metadatas = [base_metadata.copy() for _ in chunks]
        
        # Step 8: Store everything in ChromaDB
        # Type cast metadatas to satisfy ChromaDB type requirements
        from chromadb.types import Metadata
        self.collection.add(
            embeddings=embeddings,  # The numerical vectors (numpy array)
            documents=chunks,       # The actual text chunks
            metadatas=cast(List[Metadata], metadatas),  # Metadata for each chunk
            ids=ids                 # Unique identifiers
        )
        
        # Step 9: Return success information
        return {
            "doc_id": doc_id,
            "chunks_created": len(chunks),
            "status": "success"
        }


# Test code - only runs when you execute this file directly
if __name__ == "__main__":
    print("Testing DocumentProcessor...")
    
    # Create processor instance
    processor = DocumentProcessor()
    
    # Create a test document
    test_file = "test_doc.txt"
    with open(test_file, "w") as f:
        f.write("This is a test document about machine learning. "
                "Machine learning is a subset of artificial intelligence. "
                "It allows computers to learn from data without being explicitly programmed.")
    
    # Test the ingestion pipeline
    try:
        result = processor.ingest_document(test_file)
        print(f"Success! Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Clean up test file
    import os
    if os.path.exists(test_file):
        os.remove(test_file)