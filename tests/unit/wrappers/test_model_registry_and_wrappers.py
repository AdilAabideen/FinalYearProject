from __future__ import annotations

import json

import pytest
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from app.agentic.model_registry import (
    build_llama_model,
    list_registered_models,
    resolve_model_spec,
    validate_model_for_agent,
)
from app.agentic.models.dr7_medical_chat import Dr7MedicalChatModel
from app.agentic.models.llama_server_chat import LlamaServerChat
from pydantic import ValidationError


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text="", headers=None):
        self.status_code = status_code
        self._payload = payload
        self.text = text or (json.dumps(payload) if payload is not None else "")
        self.headers = headers or {}

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeClient:
    def __init__(self, response, recorder):
        self.response = response
        self.recorder = recorder

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, headers, json):
        self.recorder.append({"url": url, "headers": headers, "json": json})
        return self.response


class SequencedFakeClient:
    def __init__(self, responses, recorder):
        self.responses = list(responses)
        self.recorder = recorder

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, headers, json):
        self.recorder.append({"url": url, "headers": headers, "json": json})
        if not self.responses:
            raise AssertionError("No fake responses remaining")
        return self.responses.pop(0)


@tool
def lookup_value(value: str) -> dict:
    """Return a lookup payload."""
    return {"value": value}


def _patched_client(monkeypatch, response, recorder):
    import httpx

    monkeypatch.setattr(httpx, "Client", lambda timeout: FakeClient(response, recorder))


def _patched_sequenced_client(monkeypatch, responses, recorder):
    import httpx

    monkeypatch.setattr(httpx, "Client", lambda timeout: SequencedFakeClient(responses, recorder))


@pytest.mark.unit
@pytest.mark.wrapper
def test_ut_wrp_001_dr7_wrapper_builds_bearer_auth_header(monkeypatch, load_json_fixture):
    recorded = []
    _patched_client(monkeypatch, FakeResponse(payload=load_json_fixture("provider_payloads/dr7_native_tool_calls.json")), recorded)
    model = Dr7MedicalChatModel(model="medgemma-4b-it", base_url="https://dr7.test", api_key="secret")
    model._generate([HumanMessage(content="hi")], tools=[])
    assert recorded[0]["headers"]["Authorization"] == "Bearer secret"


@pytest.mark.unit
@pytest.mark.wrapper
def test_ut_wrp_003_dr7_wrapper_injects_tool_instruction_when_tools_bound(monkeypatch, load_json_fixture):
    recorded = []
    _patched_client(monkeypatch, FakeResponse(payload=load_json_fixture("provider_payloads/dr7_native_tool_calls.json")), recorded)
    model = Dr7MedicalChatModel(model="medgemma-4b-it", base_url="https://dr7.test", api_key="secret")
    model._generate([HumanMessage(content="hi")], tools=[{"function": {"name": "lookup_value", "description": "", "parameters": {}}}], tool_choice="any")
    assert "<tool_rules>" in recorded[0]["json"]["messages"][0]["content"]


@pytest.mark.unit
@pytest.mark.wrapper
def test_ut_wrp_004_dr7_wrapper_parses_provider_native_tool_calls(monkeypatch, load_json_fixture):
    recorded = []
    _patched_client(monkeypatch, FakeResponse(payload=load_json_fixture("provider_payloads/dr7_native_tool_calls.json")), recorded)
    model = Dr7MedicalChatModel(model="medgemma-4b-it", base_url="https://dr7.test", api_key="secret")
    result = model._generate([HumanMessage(content="hi")], tools=[{"function": {"name": "lookup_value", "description": "", "parameters": {}}}])
    assert result.generations[0].message.tool_calls[0]["name"] == "lookup_value"


@pytest.mark.unit
@pytest.mark.wrapper
def test_ut_wrp_006_dr7_wrapper_raises_on_http_error(monkeypatch):
    recorded = []
    _patched_client(monkeypatch, FakeResponse(status_code=500, payload={"detail": "bad"}, text="bad"), recorded)
    model = Dr7MedicalChatModel(model="medgemma-4b-it", base_url="https://dr7.test", api_key="secret")
    with pytest.raises(RuntimeError):
        model._generate([HumanMessage(content="hi")], tools=[])


@pytest.mark.unit
@pytest.mark.wrapper
def test_ut_wrp_007_dr7_wrapper_raises_on_invalid_json_body(monkeypatch):
    recorded = []
    _patched_client(monkeypatch, FakeResponse(payload=ValueError("bad"), text="oops"), recorded)
    model = Dr7MedicalChatModel(model="medgemma-4b-it", base_url="https://dr7.test", api_key="secret")
    with pytest.raises(RuntimeError):
        model._generate([HumanMessage(content="hi")], tools=[])


@pytest.mark.unit
@pytest.mark.wrapper
def test_ut_wrp_008_dr7_wrapper_raises_on_missing_choices_message(monkeypatch):
    recorded = []
    _patched_client(monkeypatch, FakeResponse(payload={"choices": []}), recorded)
    model = Dr7MedicalChatModel(model="medgemma-4b-it", base_url="https://dr7.test", api_key="secret")
    with pytest.raises(RuntimeError):
        model._generate([HumanMessage(content="hi")], tools=[])


@pytest.mark.unit
@pytest.mark.wrapper
def test_ut_wrp_009_dr7_wrapper_retries_once_on_429_then_succeeds(monkeypatch, load_json_fixture):
    recorded = []
    sleeps = []
    _patched_sequenced_client(
        monkeypatch,
        [
            FakeResponse(
                status_code=429,
                payload={"error": {"message": "rate limited"}},
                text='{"error":{"message":"rate limited"}}',
            ),
            FakeResponse(payload=load_json_fixture("provider_payloads/dr7_native_tool_calls.json")),
        ],
        recorded,
    )
    monkeypatch.setattr("app.agentic.models.dr7_medical_chat.time.sleep", lambda seconds: sleeps.append(seconds))
    model = Dr7MedicalChatModel(
        model="medgemma-4b-it",
        base_url="https://dr7.test",
        api_key="secret",
        rate_limit_max_retries=2,
        rate_limit_backoff_initial_s=10.0,
        rate_limit_backoff_multiplier=2.0,
        rate_limit_backoff_max_s=40.0,
    )

    result = model._generate([HumanMessage(content="hi")], tools=[{"function": {"name": "lookup_value", "description": "", "parameters": {}}}])

    assert result.generations[0].message.tool_calls[0]["name"] == "lookup_value"
    assert sleeps == [10.0]
    assert len(recorded) == 2


@pytest.mark.unit
@pytest.mark.wrapper
def test_ut_wrp_010_llama_wrapper_includes_auth_header_when_api_key_provided(monkeypatch, load_json_fixture):
    recorded = []
    _patched_client(monkeypatch, FakeResponse(payload=load_json_fixture("provider_payloads/llama_native_tool_calls.json")), recorded)
    model = LlamaServerChat(model="esi1", base_url="https://llama.test", api_key="secret")
    model._generate([HumanMessage(content="hi")], tools=[])
    assert recorded[0]["headers"]["Authorization"] == "Bearer secret"


@pytest.mark.unit
@pytest.mark.wrapper
def test_ut_wrp_011_llama_wrapper_accepts_full_chat_completions_url(monkeypatch, load_json_fixture):
    recorded = []
    _patched_client(monkeypatch, FakeResponse(payload=load_json_fixture("provider_payloads/llama_native_tool_calls.json")), recorded)
    model = LlamaServerChat(
        model="medgemma-4b-it",
        base_url="https://llama.test/v1/chat/completions",
    )
    model._generate([HumanMessage(content="hi")], tools=[])
    assert recorded[0]["url"] == "https://llama.test/v1/chat/completions"


@pytest.mark.unit
@pytest.mark.wrapper
def test_ut_wrp_012_llama_wrapper_resolves_adapter_by_model_id_fallback():
    model = LlamaServerChat(model="esi345")
    assert model._resolve_adapter_id() == 2


@pytest.mark.unit
@pytest.mark.wrapper
def test_ut_wrp_013_llama_wrapper_rejects_unsupported_adapter_id():
    model = LlamaServerChat(model="esi1", adapter_id=99)
    with pytest.raises(ValueError):
        model._resolve_adapter_id()


@pytest.mark.unit
@pytest.mark.wrapper
def test_ut_wrp_014_llama_wrapper_rejects_unsupported_adapter_name():
    with pytest.raises(ValidationError):
        LlamaServerChat(model="esi1", adapter="bad")


@pytest.mark.unit
@pytest.mark.wrapper
def test_ut_wrp_015_llama_wrapper_parses_tool_calls_when_present(monkeypatch, load_json_fixture):
    recorded = []
    _patched_client(monkeypatch, FakeResponse(payload=load_json_fixture("provider_payloads/llama_native_tool_calls.json")), recorded)
    model = LlamaServerChat(model="esi1", base_url="https://llama.test")
    result = model._generate([HumanMessage(content="hi")], tools=[{"function": {"name": "lookup_value", "description": "", "parameters": {}}}])
    assert result.generations[0].message.tool_calls[0]["name"] == "lookup_value"


@pytest.mark.unit
@pytest.mark.wrapper
def test_ut_wrp_016_llama_wrapper_applies_zero_value_adapter_id(monkeypatch, load_json_fixture):
    recorded = []
    _patched_client(monkeypatch, FakeResponse(payload=load_json_fixture("provider_payloads/llama_native_tool_calls.json")), recorded)
    model = LlamaServerChat(model="esi1", base_url="https://llama.test")
    model._generate([HumanMessage(content="hi")], tools=[])
    assert recorded[0]["json"]["lora"] == [{"id": 0, "scale": 1.0}]


@pytest.mark.unit
@pytest.mark.wrapper
def test_ut_wrp_017_llama_wrapper_raises_on_http_error(monkeypatch):
    recorded = []
    _patched_client(monkeypatch, FakeResponse(status_code=500, payload={"detail": "bad"}, text="bad"), recorded)
    model = LlamaServerChat(model="esi1", base_url="https://llama.test")
    with pytest.raises(RuntimeError):
        model._generate([HumanMessage(content="hi")], tools=[])


@pytest.mark.unit
@pytest.mark.wrapper
def test_ut_wrp_018_llama_wrapper_skips_lora_payload_for_medgemma(monkeypatch, load_json_fixture):
    recorded = []
    _patched_client(monkeypatch, FakeResponse(payload=load_json_fixture("provider_payloads/llama_native_tool_calls.json")), recorded)
    model = LlamaServerChat(model="medgemma-4b-it", base_url="https://llama.test")
    model._generate([HumanMessage(content="hi")], tools=[])
    assert "lora" not in recorded[0]["json"]


@pytest.mark.unit
def test_ut_wrp_019_medgemma_default_registry_entry_uses_dr7():
    spec = resolve_model_spec("medgemma-4b-it")
    assert spec.provider == "dr7"


@pytest.mark.unit
def test_ut_wrp_020_medgemma_llama_alias_keeps_provider_model_id():
    spec = resolve_model_spec("medgemma-4b-it-llama")
    model = build_llama_model(spec)
    assert isinstance(model, LlamaServerChat)
    assert model.model == "medgemma-4b-it"


@pytest.mark.unit
def test_ut_wrp_019_resolve_unknown_model_id_as_openai_provider_fallback():
    spec = resolve_model_spec("future-model")
    assert spec.provider == "openai"


@pytest.mark.unit
def test_ut_wrp_021_registered_models_list_is_stable_and_sorted():
    ids = [spec.id for spec in list_registered_models()]
    assert ids == sorted(ids)


@pytest.mark.unit
def test_ut_wrp_023_unknown_llama_model_mapping_raises_runtime_error():
    with pytest.raises(RuntimeError):
        build_llama_model(resolve_model_spec("unknown-llama"))
