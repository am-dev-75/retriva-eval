import pytest
from retriva_eval.adapters.qdrant_store import QdrantAdapter
from retriva_eval.core.config import QdrantConfig

def test_safe_delete_collection(caplog):
    config = QdrantConfig()
    adapter = QdrantAdapter(config)
    adapter.safe_delete_collection()
    
    assert "Deletion of collection" in caplog.text
    assert "disabled in MVP" in caplog.text
    # Ensure client.delete_collection is not called (implicitly because we don't mock it and it didn't throw connection error)
