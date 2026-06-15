"""Tests for model spec configuration helpers."""

from src.config import to_model_spec


def test_to_model_spec_adds_anthropic_prefix():
    assert to_model_spec("claude-haiku-4-5") == "anthropic:claude-haiku-4-5"


def test_to_model_spec_preserves_existing_prefix():
    assert to_model_spec("openai:gpt-5-mini") == "openai:gpt-5-mini"


def test_to_model_spec_strips_whitespace():
    assert to_model_spec("  claude-haiku-4-5  ") == "anthropic:claude-haiku-4-5"
