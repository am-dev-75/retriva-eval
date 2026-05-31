import pytest
from retriva_eval.adapters.qdrant_store import QdrantAdapter
from retriva_eval.core.config import Settings

def test_safe_delete_collection(caplog):
    settings = Settings()
    adapter = QdrantAdapter(settings)
    adapter.safe_delete_collection()
    
    assert "Deletion of collection" in caplog.text
    assert "disabled in MVP" in caplog.text
    # Ensure client.delete_collection is not called (implicitly because we don't mock it and it didn't throw connection error)
