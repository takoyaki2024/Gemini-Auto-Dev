import pytest

from core.local_client import LocalAIClient, LocalAIUnavailable


def test_choose_model_prefers_qwen():
    names = ["llama3.1:8b", "qwen2.5-coder:7b"]
    assert LocalAIClient.choose_model(names) == "qwen2.5-coder:7b"


def test_choose_requested_model():
    names = ["qwen2.5-coder:7b", "llama3.1:8b"]
    assert LocalAIClient.choose_model(names, "llama3.1") == "llama3.1:8b"


def test_choose_missing_requested_model_raises():
    with pytest.raises(LocalAIUnavailable):
        LocalAIClient.choose_model(["qwen2.5-coder:7b"], "missing-model")
