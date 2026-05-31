from typing import List
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from retriva_eval.core.config import QdrantConfig
from retriva_eval.core.schemas import CorpusRecord
from retriva_eval.utils.logging import get_logger

logger = get_logger("qdrant_adapter")

class QdrantAdapter:
    def __init__(self, config: QdrantConfig):
        self.config = config
        
        # Initialize client
        if self.config.api_key:
            self.client = QdrantClient(url=self.config.url, api_key=self.config.api_key)
        else:
            self.client = QdrantClient(url=self.config.url)
            
    def verify_collection(self) -> None:
        """Verify the collection exists. Fail fast if it does not."""
        name = self.config.collection_name
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == name for c in collections)
            if not exists:
                raise ValueError(
                    f"Qdrant collection '{name}' does not exist. "
                    "MVP requires manual creation of the evaluation collection."
                )
            logger.info(f"Verified Qdrant collection '{name}' exists.")
        except Exception as e:
            logger.error(f"Failed to verify Qdrant collection '{name}': {e}")
            raise
            
    def upsert_chunks(self, records: List[CorpusRecord], run_id: str) -> None:
        """Upsert records into the collection. Embeddings should be included in the record payload or handled before this step.
        For simplicity in MVP, we assume the user embedding model is used to create actual vector representations.
        If chunks don't have vectors, we might need an embedder. Wait, the ingest.py will handle embedding and pass points.
        Actually, let's keep the adapter simple and accept Qdrant points directly.
        """
        pass
        
    def upsert_points(self, points: List[rest.PointStruct]) -> None:
        """Upsert raw points into Qdrant."""
        self.client.upsert(
            collection_name=self.config.collection_name,
            points=points
        )
        logger.info(f"Upserted {len(points)} points into '{self.config.collection_name}'")

    def safe_delete_collection(self) -> None:
        """Safety wrapper: MVP explicitly disables collection deletion."""
        logger.warning(
            f"Deletion of collection '{self.config.collection_name}' is disabled in MVP "
            "(mode: {self.config.collection_lifecycle.mode})."
        )
        # We do not call self.client.delete_collection() here to enforce FR-004.
