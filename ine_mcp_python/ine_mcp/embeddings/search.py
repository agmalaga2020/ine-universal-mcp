"""
Semantic Search Engine - Vector-based search for INE series
Uses fastembed (lightweight, no PyTorch!) for embeddings and FAISS for fast similarity search
"""

import json
import logging
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
import faiss
from fastembed import TextEmbedding

logger = logging.getLogger(__name__)


class SemanticSearchEngine:
    """
    Semantic search engine for INE series using pre-computed embeddings

    This solves the vocabulary mismatch problem:
    - User searches "inflación comida" → finds "IPC Alimentos"
    - User searches "coste vida" → finds "IPC General"

    Much better than keyword matching which would miss these connections.
    """

    DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIM = 384  # Dimension of the model above

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        index_path: Optional[Path] = None,
        metadata_path: Optional[Path] = None,
    ):
        """
        Initialize semantic search engine

        Args:
            model_name: Sentence-transformers model name
            index_path: Path to saved FAISS index
            metadata_path: Path to saved series metadata
        """
        self.model_name = model_name
        self.index_path = index_path or Path("data/faiss_index.bin")
        self.metadata_path = metadata_path or Path("data/series_metadata.pkl")

        # Lazy loading
        self._model: Optional[TextEmbedding] = None
        self._index: Optional[faiss.Index] = None
        self._metadata: List[Dict[str, Any]] = []

        logger.info(f"Semantic search engine initialized with model: {model_name}")

    @property
    def model(self) -> TextEmbedding:
        """Lazy load the embedding model (FastEmbed - lightweight, no PyTorch!)"""
        if self._model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self._model = TextEmbedding(model_name=self.model_name)
            logger.info("Model loaded successfully")
        return self._model

    def create_index(self, series_list: List[Dict[str, Any]]) -> Tuple[int, float]:
        """
        Create FAISS index from list of series

        Args:
            series_list: List of series dictionaries with 'id', 'name', 'description'

        Returns:
            Tuple of (number of series indexed, size in MB)
        """
        logger.info(f"Creating FAISS index for {len(series_list)} series...")

        # Prepare text for embeddings (name + description)
        texts = []
        metadata = []

        for series in series_list:
            # Combine name and description for better semantic matching
            name = series.get("Nombre") or series.get("name") or ""
            desc = series.get("Descripcion") or series.get("description") or ""
            text = f"{name}. {desc}".strip()

            texts.append(text)
            metadata.append({
                "id": series.get("COD") or series.get("Id") or series.get("id"),
                "name": name,
                "description": desc,
            })

        # Generate embeddings using FastEmbed
        logger.info("Generating embeddings...")
        # FastEmbed returns a generator, convert to numpy array
        embeddings_list = list(self.model.embed(texts, batch_size=32))
        embeddings = np.array(embeddings_list)

        # Create FAISS index
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)  # Inner Product for cosine similarity

        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)

        # Add to index
        index.add(embeddings.astype(np.float32))

        self._index = index
        self._metadata = metadata

        # Calculate size
        index_size_mb = embeddings.nbytes / (1024 * 1024)

        logger.info(f"Index created: {len(series_list)} series, {index_size_mb:.2f}MB")

        return len(series_list), index_size_mb

    def save_index(self):
        """Save FAISS index and metadata to disk"""
        if self._index is None or not self._metadata:
            raise RuntimeError("No index to save. Call create_index() first.")

        # Create data directory
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        faiss.write_index(self._index, str(self.index_path))
        logger.info(f"FAISS index saved to {self.index_path}")

        # Save metadata
        with open(self.metadata_path, "wb") as f:
            pickle.dump(self._metadata, f)
        logger.info(f"Metadata saved to {self.metadata_path}")

    def load_index(self):
        """Load FAISS index and metadata from disk"""
        if not self.index_path.exists():
            raise FileNotFoundError(f"Index not found at {self.index_path}")
        if not self.metadata_path.exists():
            raise FileNotFoundError(f"Metadata not found at {self.metadata_path}")

        # Load FAISS index
        self._index = faiss.read_index(str(self.index_path))
        logger.info(f"FAISS index loaded from {self.index_path}")

        # Load metadata
        with open(self.metadata_path, "rb") as f:
            self._metadata = pickle.load(f)
        logger.info(f"Metadata loaded: {len(self._metadata)} series")

    def search(
        self,
        query: str,
        top_k: int = 10,
        score_threshold: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Search for series by semantic similarity

        Args:
            query: Search query (e.g., "inflación de alimentos")
            top_k: Number of top results to return
            score_threshold: Minimum similarity score (0-1)

        Returns:
            List of matching series with similarity scores
        """
        if self._index is None:
            raise RuntimeError("Index not loaded. Call load_index() first.")

        # Encode query using FastEmbed
        query_embeddings = list(self.model.embed([query]))
        query_embedding = np.array([query_embeddings[0]])  # Shape: (1, dim)

        # Normalize for cosine similarity
        faiss.normalize_L2(query_embedding)

        # Search
        scores, indices = self._index.search(query_embedding.astype(np.float32), top_k)

        # Filter by threshold and format results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if score >= score_threshold:
                metadata = self._metadata[idx]
                results.append({
                    **metadata,
                    "similarity_score": float(score),
                })

        logger.info(f"Search '{query}': {len(results)} results (threshold={score_threshold})")

        return results

    def is_ready(self) -> bool:
        """Check if index is loaded and ready to search"""
        return self._index is not None and len(self._metadata) > 0

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        if not self.is_ready():
            return {"status": "not_ready"}

        return {
            "status": "ready",
            "total_series": len(self._metadata),
            "model": self.model_name,
            "dimension": self.EMBEDDING_DIM,
            "index_file": str(self.index_path),
            "metadata_file": str(self.metadata_path),
        }


async def build_index_from_api(
    api_client,
    output_dir: Path = Path("data"),
    max_operations: Optional[int] = None,
) -> SemanticSearchEngine:
    """
    Build semantic search index by scraping all series from INE API

    This is the initialization step that should be run once to build the index.
    After that, the index can be loaded from disk.

    Args:
        api_client: INEClient instance
        output_dir: Directory to save index files
        max_operations: Maximum number of operations to process (None = all)

    Returns:
        Initialized SemanticSearchEngine with loaded index
    """
    logger.info("Starting index building from INE API...")

    all_series = []

    # Get all operations
    operations = await api_client.get_operations()
    logger.info(f"Found {len(operations)} operations")

    if max_operations:
        operations = operations[:max_operations]
        logger.info(f"Limited to {max_operations} operations")

    # Fetch series for each operation
    for i, operation in enumerate(operations, 1):
        op_code = operation.get("Cod") or operation.get("code")
        op_name = operation.get("Nombre") or operation.get("name")

        logger.info(f"[{i}/{len(operations)}] Fetching series for operation: {op_name} ({op_code})")

        try:
            series = await api_client.get_operation_series(op_code)
            all_series.extend(series)
            logger.info(f"  → {len(series)} series found")

        except Exception as e:
            logger.error(f"  → Error fetching series: {e}")
            continue

    logger.info(f"Total series collected: {len(all_series)}")

    # Create search engine and build index
    engine = SemanticSearchEngine(
        index_path=output_dir / "faiss_index.bin",
        metadata_path=output_dir / "series_metadata.pkl",
    )

    num_indexed, size_mb = engine.create_index(all_series)
    engine.save_index()

    logger.info(f"Index building complete: {num_indexed} series, {size_mb:.2f}MB")

    return engine
