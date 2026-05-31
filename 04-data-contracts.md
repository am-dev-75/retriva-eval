# Data Contracts

## Corpus Record

```json
{
  "id": "doc_001_chunk_0001",
  "suite": "ragas_sample_markdown",
  "document_id": "doc_001",
  "text": "Markdown chunk text...",
  "metadata": {
    "source_file": "Sample_Docs_Markdown/example.md",
    "chunk_index": 1
  }
}
```

## Query Record

```json
{
  "id": "q_001",
  "suite": "ragas_sample_markdown",
  "question": "What does the document say about ...?",
  "reference_answer": "Expected answer...",
  "reference_context_ids": ["doc_001_chunk_0001"],
  "metadata": {
    "source": "ragas_synthetic",
    "difficulty": "simple"
  }
}
```

## Prediction Record

```json
{
  "query_id": "q_001",
  "suite": "ragas_sample_markdown",
  "question": "What does the document say about ...?",
  "answer": "Retriva answer...",
  "retrieved_contexts": [
    {
      "id": "doc_001_chunk_0001",
      "text": "Retrieved context text...",
      "score": 0.91,
      "rank": 1
    }
  ],
  "latency_ms": 1234,
  "tokens": {
    "prompt": null,
    "completion": null,
    "total": null
  },
  "error": null
}
```

## Metrics Record

```json
{
  "suite": "ragas_sample_markdown",
  "run_id": "20260531T090000Z",
  "sample_count": 25,
  "metrics": {
    "faithfulness": 0.84,
    "answer_relevancy": 0.79,
    "context_precision": 0.76,
    "context_recall": 0.81,
    "latency_p50_ms": 900,
    "latency_p95_ms": 2200,
    "error_rate": 0.0
  },
  "thresholds": {
    "faithfulness": 0.75,
    "answer_relevancy": 0.70,
    "context_precision": 0.70,
    "context_recall": 0.70
  },
  "status": "pass"
}
```
