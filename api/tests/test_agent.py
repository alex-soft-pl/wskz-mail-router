"""Testy agenta bez prawdziwej Ollamy — FunctionModel/TestModel z pydantic-ai."""

import pytest
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app import agent as agent_mod
from app.agent import AgentUnavailableError, route_and_send
from app.config import Settings
from app.departments import Department


@pytest.fixture
def sent_mails(monkeypatch):
    sent = []

    def fake_send(settings, department, reply_to, body):
        sent.append({"department": department, "reply_to": reply_to, "body": body})

    monkeypatch.setattr(agent_mod.mailer, "send_email", fake_send)
    return sent


SETTINGS = Settings(smtp_host="smtp.test", smtp_port=2525)


def _tool_call(department: str) -> ModelResponse:
    return ModelResponse(
        parts=[ToolCallPart(tool_name="send_email", args={"department": department})]
    )


async def test_happy_path_model_picks_department(sent_mails):
    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        last = messages[-1].parts[-1]
        if last.part_kind == "tool-return":  # po udanym toolu — zwykła odpowiedź tekstowa
            return ModelResponse(parts=[TextPart(content="Przekazano.")])
        return _tool_call("it")

    result = await route_and_send(
        SETTINGS, "jan@example.com", "Nie działa mi komputer", model=FunctionModel(model_fn)
    )

    assert result.department is Department.IT
    assert result.fallback is False
    assert result.attempts == 1
    assert sent_mails == [
        {
            "department": Department.IT,
            "reply_to": "jan@example.com",
            "body": "Nie działa mi komputer",
        }
    ]


async def test_fallback_when_model_never_calls_tool(sent_mails):
    calls = []

    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        calls.append(1)
        return ModelResponse(parts=[TextPart(content="Nie wiem, co zrobić.")])

    result = await route_and_send(SETTINGS, "jan@example.com", "???", model=FunctionModel(model_fn))

    assert result.department is Department.OTHER
    assert result.fallback is True
    assert result.attempts == agent_mod.MAX_ATTEMPTS
    assert len(calls) == agent_mod.MAX_ATTEMPTS
    # fallback wysyła dokładnie jeden mail, na other@, z Reply-To z requestu
    assert sent_mails == [
        {"department": Department.OTHER, "reply_to": "jan@example.com", "body": "???"}
    ]


async def test_invalid_department_is_rejected_then_retried(sent_mails):
    """Model najpierw wskazuje dział spoza enum — walidacja odrzuca, retry naprawia."""
    seen_retry_prompts = []

    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        last = messages[-1].parts[-1]
        if last.part_kind == "retry-prompt":
            seen_retry_prompts.append(last)
            return _tool_call("kadry")
        if last.part_kind == "tool-return":
            return ModelResponse(parts=[TextPart(content="Przekazano.")])
        return _tool_call("marketing")  # spoza enum

    result = await route_and_send(
        SETTINGS, "jan@example.com", "Wniosek o urlop", model=FunctionModel(model_fn)
    )

    assert seen_retry_prompts, "walidacja powinna odrzucić dział spoza enum"
    assert result.department is Department.KADRY
    assert [m["department"] for m in sent_mails] == [Department.KADRY]


async def test_ollama_down_raises_agent_unavailable(sent_mails):
    """Prawdziwy klient HTTP na zamknięty port — kontrolowany wyjątek, zero maili."""
    agent_mod._build_model.cache_clear()
    settings = Settings(smtp_host="smtp.test", smtp_port=2525)
    model = agent_mod._build_model("http://localhost:9", "qwen2.5:3b")

    with pytest.raises(AgentUnavailableError):
        await route_and_send(settings, "jan@example.com", "test", model=model)

    assert sent_mails == []
