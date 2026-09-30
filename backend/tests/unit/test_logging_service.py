"""Unit tests for structured JSON logging with PII masking (E1-S3)."""

import json
import logging

import pytest

from app.service.logging_service import get_logger


def test_log_entry_is_single_json_object_with_required_keys(
    capsys: pytest.CaptureFixture[str],
) -> None:
    logger = get_logger("test.logging_service.basic")

    logger.info("Subscriber registered")

    captured = capsys.readouterr().out.strip()
    entry = json.loads(captured)
    assert entry["level"] == "INFO"
    assert entry["message"] == "Subscriber registered"
    assert "timestamp" in entry


def test_mobile_number_in_context_is_masked_to_last_four_digits(
    capsys: pytest.CaptureFixture[str],
) -> None:
    logger = get_logger("test.logging_service.mobile")

    logger.info("Activation requested", extra={"context": {"mobile_number": "9876547890"}})

    captured = capsys.readouterr().out.strip()
    entry = json.loads(captured)
    assert entry["context"]["mobile_number"] == "******7890"
    assert "9876547890" not in captured


def test_aadhaar_and_pan_refs_are_masked_with_same_partial_reveal_rule(
    capsys: pytest.CaptureFixture[str],
) -> None:
    logger = get_logger("test.logging_service.kyc")

    logger.info(
        "KYC document captured",
        extra={
            "context": {
                "aadhaar_ref": "234567890123",
                "pan_ref": "ABCDE1234F",
            }
        },
    )

    captured = capsys.readouterr().out.strip()
    entry = json.loads(captured)
    assert entry["context"]["aadhaar_ref"] == "********0123"
    assert entry["context"]["pan_ref"] == "******234F"
    assert "234567890123" not in captured
    assert "ABCDE1234F" not in captured


def test_all_three_pii_fields_together_never_appear_unmasked_in_emitted_json(
    capsys: pytest.CaptureFixture[str],
) -> None:
    logger = get_logger("test.logging_service.all_pii")
    raw_mobile = "9123456780"
    raw_aadhaar = "456789012345"
    raw_pan = "FGHIJ5678K"

    logger.info(
        "Full KYC payload received",
        extra={
            "context": {
                "mobile_number": raw_mobile,
                "aadhaar_ref": raw_aadhaar,
                "pan_ref": raw_pan,
            }
        },
    )

    captured = capsys.readouterr().out.strip()
    assert raw_mobile not in captured
    assert raw_aadhaar not in captured
    assert raw_pan not in captured
    entry = json.loads(captured)
    assert entry["context"]["mobile_number"].endswith(raw_mobile[-4:])
    assert entry["context"]["aadhaar_ref"].endswith(raw_aadhaar[-4:])
    assert entry["context"]["pan_ref"].endswith(raw_pan[-4:])


def test_non_pii_context_fields_pass_through_unmasked(
    capsys: pytest.CaptureFixture[str],
) -> None:
    logger = get_logger("test.logging_service.non_pii")

    logger.info("Plan published", extra={"context": {"plan_id": "PLAN-UNLIMITED-5G"}})

    captured = capsys.readouterr().out.strip()
    entry = json.loads(captured)
    assert entry["context"]["plan_id"] == "PLAN-UNLIMITED-5G"


def test_get_logger_does_not_attach_duplicate_handlers_on_repeated_calls() -> None:
    first = get_logger("test.logging_service.idempotent")
    second = get_logger("test.logging_service.idempotent")

    assert first is second
    assert len(second.handlers) == 1


def test_get_logger_returns_a_standard_library_logger() -> None:
    logger = get_logger("test.logging_service.type_check")
    assert isinstance(logger, logging.Logger)
