from __future__ import annotations

from cae.ai.llm_client import (
    DEFAULT_OLLAMA_MODEL,
    resolve_ollama_model_name,
    resolve_ollama_model_name_with_source,
)
from cae.config import settings


def test_resolve_ollama_model_name_prefers_explicit(monkeypatch) -> None:
    monkeypatch.setenv("CAE_AI_MODEL", "env-model")
    monkeypatch.setitem(settings._data, "active_model", "active-model")

    assert resolve_ollama_model_name("explicit-model") == "explicit-model"
    assert resolve_ollama_model_name_with_source("explicit-model") == ("explicit-model", "explicit")


def test_resolve_ollama_model_name_uses_env_before_settings(monkeypatch) -> None:
    monkeypatch.setenv("CAE_AI_MODEL", "env-model")
    monkeypatch.setitem(settings._data, "active_model", "active-model")

    assert resolve_ollama_model_name(None) == "env-model"
    assert resolve_ollama_model_name_with_source(None) == ("env-model", "env")


def test_resolve_ollama_model_name_uses_settings_before_default(monkeypatch) -> None:
    monkeypatch.delenv("CAE_AI_MODEL", raising=False)
    monkeypatch.setitem(settings._data, "active_model", "active-model")

    assert resolve_ollama_model_name(None) == "active-model"
    assert resolve_ollama_model_name_with_source(None) == ("active-model", "settings")


def test_resolve_ollama_model_name_falls_back_to_default(monkeypatch) -> None:
    monkeypatch.delenv("CAE_AI_MODEL", raising=False)
    monkeypatch.delitem(settings._data, "active_model", raising=False)

    assert resolve_ollama_model_name(None) == DEFAULT_OLLAMA_MODEL
    assert resolve_ollama_model_name_with_source(None) == (DEFAULT_OLLAMA_MODEL, "default")
