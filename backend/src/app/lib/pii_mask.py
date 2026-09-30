"""Low-level PII masking primitives.

Cross-cutting `lib/` utility per architecture.md — no project imports.
Reused by service/logging_service.py to mask mobile numbers, Aadhaar
references, and PAN references before any log line is emitted.
"""

_MASK_CHAR = "*"
_DEFAULT_REVEAL_SUFFIX_LENGTH = 4


def mask_last_n(raw: str, reveal: int = _DEFAULT_REVEAL_SUFFIX_LENGTH) -> str:
    """Return raw with all but its last `reveal` characters replaced by '*'.

    If raw is shorter than or equal to `reveal`, the entire value is masked
    (nothing is revealed) rather than leaking a short value in full.
    """
    if reveal < 0:
        raise ValueError("reveal must be non-negative")
    if len(raw) <= reveal:
        return _MASK_CHAR * len(raw)
    masked_length = len(raw) - reveal
    return (_MASK_CHAR * masked_length) + raw[-reveal:]
