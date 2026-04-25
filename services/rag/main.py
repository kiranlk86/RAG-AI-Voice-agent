"""
RAG (Retrieval-Augmented Generation) Service
Qdrant vector database + sentence-transformers embeddings
Supports PDF, TXT, and MD ingestion
"""
import os
import uuid
import tempfile
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import fitz  # PyMuPDF

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG Service", version="1.0.0")

# ── Config ──────────────────────────────────────────────────────
COLLECTION    = "knowledge_base"
VECTOR_SIZE   = 384    # dimensions for all-MiniLM-L6-v2
CHUNK_WORDS   = 400    # words per chunk
CHUNK_OVERLAP = 60     # overlap between chunks for better retrieval

# ── Embedding model ─────────────────────────────────────────────
logger.info("Loading sentence-transformer embedding model...")
embedder = SentenceTransformer("all-MiniLM-L6-v2")
logger.info("Embedding model ready")

# ── Qdrant client ────────────────────────────────────────────────
QDRANT_HOST = os.getenv("QDRANT_HOST", "va-qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def ensure_collection() -> None:
    """Create Qdrant collection if it doesn't exist."""
    existing = {c.name for c in qdrant.get_collections().collections}
    if COLLECTION not in existing:
        qdrant.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info(f"Created Qdrant collection: '{COLLECTION}'")


ensure_collection()


def chunk_text(text: str) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    chunks = []
    step = CHUNK_WORDS - CHUNK_OVERLAP
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + CHUNK_WORDS])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract plain text from a PDF, TXT, or MD file."""
    fname = filename.lower()
    if fname.endswith(".pdf"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            doc = fitz.open(tmp_path)
            return " ".join(page.get_text() for page in doc)
        finally:
            os.unlink(tmp_path)
    elif fname.endswith((".txt", ".md")):
        return file_bytes.decode("utf-8", errors="replace")
    else:
        raise ValueError(f"Unsupported file type: {filename}")


# ── Endpoints ────────────────────────────────────────────────────

@app.get("/health")
async def health():
    info = qdrant.get_collection(COLLECTION)
    return {
        "status": "ok",
        "collection": COLLECTION,
        "chunks_indexed": info.points_count,
        "vector_size": VECTOR_SIZE,
    }


@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    """Ingest a PDF, TXT, or MD file into the knowledge base."""
    filename = file.filename or "upload.txt"
    content  = await file.read()

    try:
        text = extract_text(content, filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not text.strip():
        raise HTTPException(status_code=400, detail="No text extracted from file")

    chunks  = chunk_text(text)
    vectors = embedder.encode(chunks, show_progress_bar=False).tolist()
    points  = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vectors[i],
            payload={
                "text":        chunks[i],
                "source":      filename,
                "chunk_index": i,
            },
        )
        for i in range(len(chunks))
    ]

    qdrant.upsert(collection_name=COLLECTION, points=points)
    logger.info(f"Ingested {len(chunks)} chunks from '{filename}'")

    return {
        "status":       "ingested",
        "filename":     filename,
        "chunks_added": len(chunks),
        "total_chunks": qdrant.get_collection(COLLECTION).points_count,
    }


class QueryRequest(BaseModel):
    query:     str
    n_results: int = 3


@app.post("/query")
async def query(req: QueryRequest):
    """Find the most semantically relevant chunks for a query."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    vec     = embedder.encode(req.query).tolist()
    results = qdrant.query_points(
        collection_name=COLLECTION,
        query=vec,
        limit=req.n_results,
    ).points

    chunks  = [r.payload["text"] for r in results]
    scores  = [round(r.score, 4) for r in results]
    context = "\n\n---\n\n".join(chunks)

    return {
        "context": context,
        "chunks":  chunks,
        "scores":  scores,
    }


@app.delete("/reset")
async def reset():
    """Wipe the collection and recreate it."""
    qdrant.delete_collection(COLLECTION)
    ensure_collection()
    logger.info("Knowledge base reset")
    return {"status": "reset", "collection": COLLECTION}
