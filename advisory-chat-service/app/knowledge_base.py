"""
Knowledge Base module for RAG.
Handles document embedding, storage, and vector similarity search using pgvector.
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# Lazy-loaded embedding model singleton
_embedding_model = None


def _get_embedding_model():
    """Load sentence-transformers model (lazy singleton)."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        model_name = getattr(settings, 'EMBEDDING_MODEL_NAME', 'sentence-transformers/all-MiniLM-L6-v2')
        logger.info("Loading embedding model: %s", model_name)
        _embedding_model = SentenceTransformer(model_name)
        logger.info("Embedding model loaded successfully")
    return _embedding_model


def embed_text(text):
    """Embed a single text string, returns a list of floats."""
    model = _get_embedding_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def embed_texts(texts):
    """Embed multiple texts, returns list of lists of floats."""
    model = _get_embedding_model()
    embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32)
    return [e.tolist() for e in embeddings]


def chunk_text(text, chunk_size=500, overlap=50):
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks


def embed_and_store_document(title, content, source):
    """Embed a document and store it in the KB."""
    from .models import KnowledgeDocument

    embedding = embed_text(f"{title}. {content}")
    doc = KnowledgeDocument.objects.create(
        title=title,
        content=content,
        source=source,
        embedding=embedding,
    )
    logger.info("Stored KB document: %s [%s]", title, source)
    return doc


def bulk_embed_and_store(documents):
    """
    Bulk embed and store documents.
    documents: list of dicts with keys: title, content, source
    """
    from .models import KnowledgeDocument

    if not documents:
        return []

    texts = [f"{d['title']}. {d['content']}" for d in documents]
    embeddings = embed_texts(texts)

    kb_docs = []
    for doc_data, embedding in zip(documents, embeddings):
        kb_doc = KnowledgeDocument(
            title=doc_data['title'],
            content=doc_data['content'],
            source=doc_data['source'],
            embedding=embedding,
        )
        kb_docs.append(kb_doc)

    created = KnowledgeDocument.objects.bulk_create(kb_docs)
    logger.info("Bulk stored %d KB documents", len(created))
    return created


def search_kb(query, top_k=3, source_filter=None):
    """
    Search the knowledge base using vector similarity.
    Returns list of dicts with title, content, source, similarity score.
    """
    from .models import KnowledgeDocument
    from pgvector.django import CosineDistance

    query_embedding = embed_text(query)

    qs = KnowledgeDocument.objects.annotate(
        distance=CosineDistance('embedding', query_embedding)
    ).order_by('distance')

    if source_filter:
        qs = qs.filter(source=source_filter)

    results = []
    for doc in qs[:top_k]:
        results.append({
            'id': doc.id,
            'title': doc.title,
            'content': doc.content,
            'source': doc.source,
            'similarity': round(1 - doc.distance, 4),
        })

    return results
