from retriva_eval.core.config import Settings
from retriva_eval.adapters.retriva_client import (
    BaseRetrivaClient,
    GatewayHttpClient,
)


class _RecordingClient(BaseRetrivaClient):
    """Exercises the base-class default ingest_documents loop."""

    def __init__(self, settings):
        super().__init__(settings)
        self.calls = []

    def query(self, query_record, run_id):  # pragma: no cover - unused
        raise NotImplementedError

    def ingest_document(self, file_path, document_id, run_id, suite_name):
        self.calls.append((file_path, document_id, run_id, suite_name))


def test_base_ingest_documents_loops_each_doc():
    client = _RecordingClient(Settings())
    docs = [("/tmp/a.md", "a"), ("/tmp/b.md", "b"), ("/tmp/c.md", "c")]
    client.ingest_documents(docs, run_id="r1", suite_name="ragbench")
    assert [c[1] for c in client.calls] == ["a", "b", "c"]
    assert all(c[2] == "r1" and c[3] == "ragbench" for c in client.calls)


def test_gateway_groups_by_batch_size(monkeypatch):
    settings = Settings()
    settings.eval_ingest_batch_size = 2
    client = GatewayHttpClient(settings)

    seen_groups = []

    def fake_ingest_one_batch(group, run_id, suite_name):
        seen_groups.append([doc_id for _, doc_id in group])

    monkeypatch.setattr(client, "_ingest_one_batch", fake_ingest_one_batch)

    docs = [(f"/tmp/{i}.md", str(i)) for i in range(5)]
    client.ingest_documents(docs, run_id="r1", suite_name="ragbench")

    # 5 docs with batch_size=2 -> groups of [0,1], [2,3], [4]
    assert seen_groups == [["0", "1"], ["2", "3"], ["4"]]
