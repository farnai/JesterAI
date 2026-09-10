import json
import logging
import time
from typing import Optional

logger = logging.getLogger("jester.audit")


def log_request_audit(
    request_id: str,
    user_id: str,
    conversation_id: str,
    provider: str,
    model: str,
    latency_ms: Optional[float],
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
    quota_status: str,
    remaining_free_questions: int,
    http_status: int,
    error: Optional[str] = None,
) -> None:
    """Emits lightweight structured JSON audit log per interaction turn."""
    audit_record = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "request_id": request_id,
        "user_id": user_id,
        "conversation_id": conversation_id,
        "provider": provider,
        "model": model,
        "latency_ms": latency_ms,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "quota_status": quota_status,
        "remaining_free_questions": remaining_free_questions,
        "http_status": http_status,
        "error": error,
    }
    logger.info("AUDIT %s", json.dumps(audit_record))
