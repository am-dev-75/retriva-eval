from retriva_eval.core.schemas import CorpusRecord, TokenUsage

def test_corpus_record():
    record = CorpusRecord(id="test", suite="ragas", document_id="doc1", text="text", metadata={"key": "value"})
    assert record.id == "test"
    assert record.metadata["key"] == "value"

def test_token_usage():
    usage = TokenUsage()
    assert usage.prompt is None
