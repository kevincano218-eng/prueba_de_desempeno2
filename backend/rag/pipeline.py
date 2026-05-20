"""
RAG Pipeline (Bonus Points)
Scrapes a URL, chunks the content, generates embeddings,
stores in FAISS, and retrieves relevant context for the agent.

Source URL: Configurable via RAG_SOURCE_URL in .env
Default: https://en.wikipedia.org/wiki/Artificial_intelligence
"""

import os
import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

# Lazy imports to avoid slow startup if RAG is not used
_vector_store = None
_rag_initialized = False


def _get_embeddings():
    from langchain_openai import OpenAIEmbeddings
    # OpenAI Embeddings take almost 0 RAM (API call) instead of 400MB+ for local models.
    return OpenAIEmbeddings(model="text-embedding-3-small")

def _get_supabase_client():
    from supabase.client import Client, create_client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)

def _init_vector_store():
    global _vector_store, _rag_initialized
    if _vector_store is not None:
        return True
    
    supabase = _get_supabase_client()
    if not supabase:
        print("[RAG] Supabase credentials not found in .env")
        return False
        
    from langchain_community.vectorstores import SupabaseVectorStore
    embeddings = _get_embeddings()
    _vector_store = SupabaseVectorStore(
        client=supabase,
        embedding=embeddings,
        table_name="documents",
        query_name="match_documents"
    )
    _rag_initialized = True
    return True


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current = []
    current_len = 0

    for sentence in sentences:
        words = sentence.split()
        if current_len + len(words) > chunk_size and current:
            chunks.append(" ".join(current))
            # Keep last overlap words
            current = current[-overlap:] if len(current) > overlap else []
            current_len = len(current)
        current.extend(words)
        current_len += len(words)

    if current:
        chunks.append(" ".join(current))

    return [c for c in chunks if len(c.strip()) > 50]


def initialize_rag(url: Optional[str] = None) -> bool:
    """
    Scrape a URL, create embeddings, and build the FAISS vector store.
    Returns True on success, False on failure.
    """
    global _vector_store, _rag_initialized

    if _rag_initialized:
        # Avoid scraping again if we already connected to Supabase in this session
        return True

    # Initialize connection to the persistent store
    if not _init_vector_store():
        return False

    source_url = url or os.getenv("RAG_SOURCE_URL", "")
    if not source_url:
        print("[RAG] RAG_SOURCE_URL not set, skipping RAG indexing.")
        return False

    try:
        print(f"[RAG] Fetching content from: {source_url} to index into Supabase")
        response = requests.get(source_url, timeout=15, headers={"User-Agent": "VoiceAgent/1.0"})
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        
        meta_desc = ""
        desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if desc_tag:
            meta_desc = desc_tag.get("content", "").strip()
            
        title = ""
        title_tag = soup.find("title") or soup.find("meta", attrs={"property": "og:title"})
        if title_tag:
            title = title_tag.get_text() if hasattr(title_tag, "get_text") else title_tag.get("content", "").strip()

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        raw_text = soup.get_text(separator=" ", strip=True)
        body_text = re.sub(r"\s+", " ", raw_text).strip()
        
        parts = []
        if title:
            parts.append(f"Título: {title}")
        if meta_desc:
            parts.append(f"Descripción: {meta_desc}")
        if body_text:
            parts.append(f"Contenido: {body_text}")
            
        text = ". ".join(parts).strip()

        if len(text) < 50:
            print("[RAG] Scraped content too short, aborting.")
            return False

        chunks = _chunk_text(text)
        print(f"[RAG] Created {len(chunks)} chunks from {len(text)} characters.")

        from langchain.schema import Document
        docs = [Document(page_content=chunk, metadata={"source": source_url, "chunk": i})
                for i, chunk in enumerate(chunks)]

        # Add documents directly to the already-initialized Supabase Vector Store
        global _vector_store
        _vector_store.add_documents(docs)
        print("[RAG] Chunks successfully persisted to Supabase.")
        return True

    except Exception as e:
        print(f"[RAG] Initialization failed: {e}")
        return False


def retrieve_context(query: str, k: int = 3) -> str:
    """
    Retrieve relevant context chunks for a given query.
    Returns empty string if RAG is not initialized.
    """
    global _vector_store
    
    # Try to initialize connection to Supabase if not done yet
    if not _rag_initialized:
        _init_vector_store()

    if not _rag_initialized or _vector_store is None:
        return ""

    try:
        docs = _vector_store.similarity_search(query, k=k)
        if not docs:
            return ""

        context_parts = [f"[Relevant info {i+1}]: {doc.page_content}"
                         for i, doc in enumerate(docs)]
        return "\n\n".join(context_parts)

    except Exception as e:
        print(f"[RAG] Retrieval error: {e}")
        return ""


def update_rag_with_text(text: str, url: str) -> bool:
    """
    Chunk the provided text, generate embeddings, and add them to the Supabase vector store.
    """
    global _vector_store, _rag_initialized

    # Initialize connection to Supabase
    if not _rag_initialized:
        if not _init_vector_store():
            return False

    try:
        chunks = _chunk_text(text)
        if not chunks:
            print("[RAG] No chunks created from text.")
            return False

        from langchain.schema import Document
        docs = [Document(page_content=chunk, metadata={"source": url, "chunk": i})
                for i, chunk in enumerate(chunks)]

        _vector_store.add_documents(docs)
        print(f"[RAG] Successfully added {len(chunks)} chunks to Supabase from {url}")
        return True

    except Exception as e:
        print(f"[RAG] Failed to update RAG with text: {e}")
        return False
