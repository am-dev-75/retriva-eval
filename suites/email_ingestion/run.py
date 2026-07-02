"""Run stage: verify ingestion, then query the gateway to check answer quality."""

import json
import os
import time
from typing import Optional

import httpx
import yaml

from retriva_eval.core.config import Settings
from retriva_eval.logger import get_logger

logger = get_logger("email_ingestion.run")


def _load_suite_config() -> dict:
    path = os.path.join("suites", "email_ingestion", "suite.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _resolve_gateway_base_url(suite_cfg: dict, settings: Settings) -> str:
    """Resolve the gateway base URL from env vars or suite config."""
    # Env var override takes priority
    host = os.environ.get("EMAIL_EVAL_GATEWAY_HOST")
    port = os.environ.get("EMAIL_EVAL_GATEWAY_PORT")
    if host:
        return f"http://{host}:{port or '8002'}"
    # Fall back to suite config, then global settings
    gw_cfg = suite_cfg.get("gateway", {})
    return gw_cfg.get("base_url", settings.gateway_base_url)


def _resolve_smtp_config(suite_cfg: dict) -> tuple[str, int, str]:
    """Resolve SMTP host/port/from from env vars or suite config."""
    smtp_cfg = suite_cfg.get("smtp", {})
    host = os.environ.get("EMAIL_EVAL_SMTP_HOST", smtp_cfg.get("host", "127.0.0.1"))
    port = int(os.environ.get("EMAIL_EVAL_SMTP_PORT", smtp_cfg.get("port", 8025)))
    from_addr = smtp_cfg.get("from_address", "eval@retriva-eval.local")
    return host, port, from_addr


def _search_documents(gateway_base_url: str, message_id: str,
                      poll_interval: int, timeout: int) -> dict:
    """Search the gateway for a document matching the given message_id."""
    deadline = time.time() + timeout
    search_url = f"{gateway_base_url.rstrip('/')}/gateway/documents/search"

    while time.time() < deadline:
        try:
            resp = httpx.post(
                search_url,
                json={
                    "query": "",
                    "metadata_filters": [
                        {
                            "field": "user_metadata.message_id",
                            "operator": "eq",
                            "value": message_id,
                        }
                    ],
                    "limit": 5,
                },
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", data.get("documents", []))
                if results:
                    return {"found": True, "document": results[0]}
            time.sleep(poll_interval)
        except Exception as e:
            logger.warning(f"Search error for {message_id}: {e}")
            time.sleep(poll_interval)

    return {"found": False}


def _query_gateway(gateway_base_url: str, chat_path: str,
                   question: str, message_id: str, kb_id: str,
                   metadata_filter_mode: str, timeout: int) -> dict:
    """Send a query to the gateway scoped to a specific email by message_id.

    Returns {"answered": bool, "answer": str, "citations": list, "error": str?}.
    """
    chat_url = f"{gateway_base_url.rstrip('/')}{chat_path}"
    payload = {
        "message": question,
        "kb_ids": [kb_id],
        "metadata_filters": [
            {
                "field": "message_id",
                "operator": "eq",
                "value": message_id,
            }
        ],
        "metadata_filter_mode": metadata_filter_mode,
        "stream": False,
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(chat_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            answer = data.get("content", "")
            citations = data.get("citations", [])
            return {
                "answered": bool(answer.strip()),
                "answer": answer,
                "citations": citations,
            }
    except Exception as e:
        return {"answered": False, "answer": "", "citations": [], "error": str(e)}


def _check_answer_relevance(answer: str, expected_answer: str) -> bool:
    """Heuristic check: does the answer contain key terms from the expected answer?

    This is a simple keyword-overlap check, not a full LLM-as-judge evaluation.
    It verifies that the answer mentions the key facts from the expected answer.
    """
    if not answer.strip():
        return False
    # Extract significant words from expected_answer (length > 3, not stopwords)
    stopwords = {"the", "and", "for", "with", "from", "that", "this", "was",
                 "were", "are", "has", "have", "will", "been", "not", "but",
                 "all", "new", "year", "into", "also", "than", "per", "min"}
    expected_words = set()
    for word in expected_answer.lower().replace(",", "").replace(".", "").split():
        if len(word) > 3 and word not in stopwords:
            expected_words.add(word)

    if not expected_words:
        return bool(answer.strip())

    answer_lower = answer.lower()
    matched = sum(1 for w in expected_words if w in answer_lower)
    # Require at least 50% of key terms to be present
    return matched >= max(1, len(expected_words) * 0.5)


def do_run(
    suite_name: str,
    settings: Settings,
    run_id: str,
    dry_run: bool,
    portion: float = 1.0,
    seed: Optional[int] = None,
):
    """Verify ingestion and query the gateway for answer quality."""
    report_dir = os.path.join(settings.eval_reports_dir, run_id, suite_name)
    send_results_path = os.path.join(report_dir, "send_results.jsonl")

    if not os.path.exists(send_results_path):
        raise FileNotFoundError(
            f"Send results not found: {send_results_path}. Run ingest stage first."
        )

    sent_results = []
    with open(send_results_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                sent_results.append(json.loads(line))

    # Only verify emails that were actually sent
    to_verify = [r for r in sent_results if r.get("sent", False)]

    suite_cfg = _load_suite_config()
    gateway_base_url = _resolve_gateway_base_url(suite_cfg, settings)
    gw_cfg = suite_cfg.get("gateway", {})
    chat_path = gw_cfg.get("chat_path", "/gateway/chat")
    poll_interval = gw_cfg.get("job_poll_interval_seconds", 2)
    job_timeout = gw_cfg.get("job_timeout_seconds", 120)
    # KB priority: suite.yaml gateway.kb_id < settings.eval_knowledge_base
    # (settings.eval_knowledge_base is overridden by --kb-id CLI option)
    kb_id = settings.eval_knowledge_base or gw_cfg.get("kb_id", "default")
    metadata_filter_mode = gw_cfg.get("metadata_filter_mode", "hard")

    # Load the selected emails to get questions/expected_answers
    selected_path = os.path.join(report_dir, "selected_emails.jsonl")
    selected_emails = {}
    if os.path.exists(selected_path):
        with open(selected_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    msg = json.loads(line)
                    selected_emails[msg["message_id"]] = msg

    logger.info(f"Verifying {len(to_verify)} emails ingested via gateway at {gateway_base_url}...")

    verification_results = []

    for i, sr in enumerate(to_verify):
        msg_data = selected_emails.get(sr["message_id"], {})
        question = msg_data.get("question", "")
        expected_answer = msg_data.get("expected_answer", "")

        if dry_run:
            logger.debug(
                f"[dry-run] Verifying email {i+1}/{len(to_verify)}:\n"
                f"  Message-ID: {sr['message_id']}\n"
                f"  To: {sr['to']}\n"
                f"  Subject: {sr.get('subject', '')}\n"
                f"  Pattern: {sr.get('address_pattern', '?')}\n"
                f"  Expected tags: {sr.get('expected_tags', {})}\n"
                f"  Expected KB: {sr.get('expected_kb', '')}\n"
                f"  Question: {question}\n"
                f"  Expected answer: {expected_answer}\n"
                f"  Simulated answer: {expected_answer}"
            )
            logger.info(f"[dry-run] Would verify email {i+1}/{len(to_verify)}: {sr['message_id']}")
            verification_results.append({
                "id": sr["id"],
                "message_id": sr["message_id"],
                "to": sr["to"],
                "subject": sr.get("subject", ""),
                "address_pattern": sr.get("address_pattern", ""),
                "expected_tags": sr.get("expected_tags", {}),
                "expected_kb": sr.get("expected_kb", ""),
                "ingested": True,
                "dry_run": True,
                "document": None,
                "decoded_tags": {},
                "decoded_kb": "",
                "tags_match": True,
                "kb_match": True,
                "question": question,
                "expected_answer": expected_answer,
                "answer": expected_answer,
                "answered": True,
                "citations": [],
                "answer_relevant": True,
            })
            continue

        # Step 1: Verify ingestion
        logger.debug(
            f"Verifying email {i+1}/{len(to_verify)}:\n"
            f"  Message-ID: {sr['message_id']}\n"
            f"  To: {sr['to']}\n"
            f"  Subject: {sr.get('subject', '')}\n"
            f"  Pattern: {sr.get('address_pattern', '?')}\n"
            f"  Expected tags: {sr.get('expected_tags', {})}\n"
            f"  Expected KB: {sr.get('expected_kb', '')}"
        )
        result = _search_documents(
            gateway_base_url, sr["message_id"], poll_interval, job_timeout
        )

        ingested = result.get("found", False)
        document = result.get("document")

        decoded_tags = {}
        decoded_kb = ""
        if document:
            metadata = document.get("user_metadata", document.get("metadata", {}))
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    metadata = {}
            system_keys = {
                "source_system", "source_id", "connector_id", "message_id",
                "subject", "from", "to", "cc", "date", "tags",
                "kb_id_override", "collection_name", "decoded_address",
            }
            for k, v in metadata.items():
                if k not in system_keys and not k.startswith("_"):
                    decoded_tags[k] = str(v)
            decoded_kb = metadata.get("kb_id_override", "")

        expected_tags = sr.get("expected_tags", {})
        expected_kb = sr.get("expected_kb", "")

        tags_match = (decoded_tags == expected_tags)
        kb_match = (decoded_kb == expected_kb) if expected_kb else True

        logger.debug(
            f"  Ingested: {ingested}, tags_match: {tags_match}, kb_match: {kb_match}\n"
            f"  Decoded tags: {decoded_tags}\n"
            f"  Decoded KB: {decoded_kb}"
        )

        # Step 2: Query the gateway with the email-specific question
        answered = False
        answer = ""
        citations = []
        answer_relevant = False
        query_error = None

        if ingested and question:
            logger.debug(
                f"  Querying gateway:\n"
                f"    Question: {question}\n"
                f"    Expected answer: {expected_answer}\n"
                f"    Filter: message_id={sr['message_id']}, mode={metadata_filter_mode}"
            )
            query_result = _query_gateway(
                gateway_base_url, chat_path, question,
                sr["message_id"], kb_id, metadata_filter_mode,
                timeout=60,
            )
            answered = query_result.get("answered", False)
            answer = query_result.get("answer", "")
            citations = query_result.get("citations", [])
            query_error = query_result.get("error")
            if answered and expected_answer:
                answer_relevant = _check_answer_relevance(answer, expected_answer)

            logger.debug(
                f"  Query result:\n"
                f"    Answered: {answered}\n"
                f"    Answer: {answer[:500]}\n"
                f"    Citations: {len(citations)}\n"
                f"    Relevant: {answer_relevant}\n"
                f"    Error: {query_error}"
            )

        verification_results.append({
            "id": sr["id"],
            "message_id": sr["message_id"],
            "to": sr["to"],
            "subject": sr.get("subject", ""),
            "address_pattern": sr.get("address_pattern", ""),
            "expected_tags": expected_tags,
            "expected_kb": expected_kb,
            "ingested": ingested,
            "document": document,
            "decoded_tags": decoded_tags,
            "decoded_kb": decoded_kb,
            "tags_match": tags_match,
            "kb_match": kb_match,
            "question": question,
            "expected_answer": expected_answer,
            "answer": answer,
            "answered": answered,
            "citations": citations,
            "answer_relevant": answer_relevant,
            "query_error": query_error,
        })

        status = "✓" if ingested else "✗"
        q_status = "✓" if answered else "✗"
        logger.info(
            f"  {status}{q_status} {i+1}/{len(to_verify)}: {sr['message_id']} "
            f"(pattern={sr.get('address_pattern', '?')}, "
            f"ingested={ingested}, answered={answered})"
        )

    # Write verification results
    results_path = os.path.join(report_dir, "verification_results.jsonl")
    with open(results_path, "w", encoding="utf-8") as f:
        for r in verification_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    ingested_count = sum(1 for r in verification_results if r["ingested"])
    answered_count = sum(1 for r in verification_results if r["answered"])
    logger.info(
        f"Verification complete: {ingested_count}/{len(to_verify)} ingested, "
        f"{answered_count}/{len(to_verify)} queries answered → {results_path}"
    )
