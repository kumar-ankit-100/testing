"""Unit tests for the low-level PII masking primitive (E1-S3)."""

import pytest

from app.lib.pii_mask import mask_last_n


def test_mask_last_n_reveals_only_the_final_four_characters_by_default() -> None:
    assert mask_last_n("9876547890") == "******7890"


def test_mask_last_n_fully_masks_a_value_shorter_than_the_reveal_length() -> None:
    assert mask_last_n("123") == "***"


def test_mask_last_n_fully_masks_a_value_exactly_the_reveal_length() -> None:
    assert mask_last_n("1234") == "****"


def test_mask_last_n_honors_a_custom_reveal_length() -> None:
    assert mask_last_n("ABCDE1234F", reveal=2) == "********4F"


def test_mask_last_n_rejects_a_negative_reveal_length() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        mask_last_n("9876547890", reveal=-1)
