"""Structured JSON logging with PII masking (E1-S3).

Service layer. Per system-design.md 5.3, this module is a pure
formatting/masking utility with no persistence concern: it imports the
cross-cutting `lib/pii_mask` masking primitive (architecture.md's documented
"all layers import from lib" exception) but never reaches into Repository,
API, or another Service module.
"""

import json
import logging
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import TextIO

from app.lib.pii_mask import mask_last_n

PII_FIELD_NAMES: frozenset[str] = frozenset(
    {"mobile_number", "aadhaar_ref", "pan_ref", "identity_proof_ref"}
)


class _CurrentStdoutHandler(logging.StreamHandler[TextIO]):
    """A StreamHandler that re-resolves sys.stdout on every emit.

    logging.getLogger(name) caches Logger objects globally by name, and
    get_logger() only attaches a handler once per name (idempotent, by
    design). A plain StreamHandler(stream=sys.stdout) binds a fixed
    reference to whatever sys.stdout was at construction time — which
    breaks pytest's capsys fixture, since capsys replaces sys.stdout with
    a fresh object per test. Without this override, only the first test
    to ever trigger a given logger name would observe captured output;
    every later test reusing that logger name would silently write into
    an earlier, already-torn-down capture buffer. Re-reading sys.stdout on
    every emit call keeps each log line going to whichever stdout is
    actually live right now.
    """

    def emit(self, record: logging.LogRecord) -> None:
        self.stream = sys.stdout
        super().emit(record)


class JsonFormatter(logging.Formatter):
    """Formats a LogRecord as one JSON object, masking PII context fields."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        context = getattr(record, "context", None)
        if isinstance(context, Mapping):
            entry["context"] = _mask_context(context)
        return json.dumps(entry)


def _mask_context(context: Mapping[str, object]) -> dict[str, object]:
    """Mask any PII_FIELD_NAMES key in context; pass all other keys through."""
    masked: dict[str, object] = {}
    for key, value in context.items():
        if key in PII_FIELD_NAMES and value is not None:
            masked[key] = mask_last_n(str(value))
        else:
            masked[key] = value
    return masked


def get_logger(name: str) -> logging.Logger:
    """Return a module-named logger that emits masked, single-line JSON to stdout.

    Idempotent: calling this twice with the same name returns the same
    logger without attaching a second handler.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = _CurrentStdoutHandler(stream=sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
