"""Agent pydantic-ai: interpretuje wiadomość i wysyła mail przez tool calling.

Konfiguracja promptu (krótkie opisy działów + few-shot + temperature=0) pochodzi
z walidacji w Etapie 0 (docs/etap0-wyniki.md) — bez few-shot qwen2.5:3b robi
tool call tylko w ~50% przypadków.
"""

import logging
import time
import uuid
from dataclasses import dataclass
from functools import lru_cache

from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import ModelAPIError, UnexpectedModelBehavior
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app import mailer
from app.config import Settings
from app.departments import DEPARTMENT_DESCRIPTIONS, Department

logger = logging.getLogger(__name__)

OLLAMA_TIMEOUT_S = 120  # CPU w kontenerze jest wolne; pierwszy request ładuje model
MAX_ATTEMPTS = 3  # 1 próba + 2 retry przy braku tool calla (reguła krytyczna nr 3)

INSTRUCTIONS = (
    "Jesteś routerem zgłoszeń pracowniczych. Zawsze wywołaj narzędzie send_email, "
    "wybierając jeden dział:\n"
    + "\n".join(f"- {d.value}: {desc}" for d, desc in DEPARTMENT_DESCRIPTIONS.items())
    + "\nZaświadczenia, urlopy, L4 i umowy to zawsze dział kadry."
    "\nNigdy nie odpowiadaj tekstem."
)


class AgentUnavailableError(Exception):
    """Ollama niedostępna / model nie odpowiada — endpoint ma zwrócić 503, nie 500."""


@dataclass
class RouterDeps:
    settings: Settings
    reply_to: str
    message: str
    sent_department: Department | None = None


@dataclass
class RoutingResult:
    department: Department
    attempts: int
    fallback: bool
    request_id: str


router_agent = Agent(deps_type=RouterDeps, instructions=INSTRUCTIONS)


@router_agent.tool
def send_email(ctx: RunContext[RouterDeps], department: Department) -> str:
    """Przekaż zgłoszenie użytkownika do wybranego działu."""
    if ctx.deps.sent_department is not None:
        return "Zgłoszenie zostało już przekazane."
    mailer.send_email(
        settings=ctx.deps.settings,
        department=department,
        reply_to=ctx.deps.reply_to,
        body=ctx.deps.message,
    )
    ctx.deps.sent_department = department
    return "OK, zgłoszenie przekazane."


def _few_shot_pair(user_msg: str, department: Department, call_id: str) -> list[ModelMessage]:
    return [
        ModelRequest(parts=[UserPromptPart(content=user_msg)]),
        ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="send_email",
                    args={"department": department.value},
                    tool_call_id=call_id,
                )
            ]
        ),
        ModelRequest(
            parts=[
                ToolReturnPart(
                    tool_name="send_email",
                    content="OK, zgłoszenie przekazane.",
                    tool_call_id=call_id,
                )
            ]
        ),
    ]


FEW_SHOT: list[ModelMessage] = [
    *_few_shot_pair("Zepsuła mi się drukarka", Department.IT, "fs1"),
    *_few_shot_pair("Poproszę o zaświadczenie o zarobkach", Department.KADRY, "fs2"),
    *_few_shot_pair("Zapomniałem hasła do poczty", Department.HELP_DESK, "fs3"),
]


@lru_cache(maxsize=4)
def _build_model(ollama_url: str, model_name: str) -> Model:
    client = AsyncOpenAI(
        base_url=f"{ollama_url.rstrip('/')}/v1",
        api_key="ollama",  # wymagany przez klienta OpenAI, ignorowany przez Ollamę
        timeout=OLLAMA_TIMEOUT_S,
        max_retries=1,
    )
    provider = OpenAIProvider(openai_client=client)
    return OpenAIChatModel(model_name, provider=provider)


def get_model(settings: Settings) -> Model:
    return _build_model(settings.ollama_url, settings.model)


async def route_and_send(
    settings: Settings,
    email: str,
    message: str,
    model: Model | None = None,
) -> RoutingResult:
    """Uruchom agenta z retry; przy braku tool calla po MAX_ATTEMPTS — fallback other@."""
    request_id = uuid.uuid4().hex[:8]
    model = model or get_model(settings)
    deps = RouterDeps(settings=settings, reply_to=email, message=message)
    t0 = time.perf_counter()

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            await router_agent.run(
                message,
                deps=deps,
                model=model,
                message_history=FEW_SHOT,
                model_settings={"temperature": 0.0},
            )
        except ModelAPIError as exc:  # połączenie/timeout/HTTP — Ollama niedostępna
            logger.error("request_id=%s ollama niedostępna: %s", request_id, exc)
            raise AgentUnavailableError(str(exc)) from exc
        except UnexpectedModelBehavior as exc:
            logger.warning(
                "request_id=%s attempt=%d nieudany przebieg agenta: %s", request_id, attempt, exc
            )

        if deps.sent_department is not None:
            elapsed = time.perf_counter() - t0
            logger.info(
                "request_id=%s department=%s attempts=%d fallback=False elapsed=%.2fs",
                request_id,
                deps.sent_department.value,
                attempt,
                elapsed,
            )
            return RoutingResult(
                department=deps.sent_department,
                attempts=attempt,
                fallback=False,
                request_id=request_id,
            )

        logger.warning("request_id=%s attempt=%d model nie wywołał toola", request_id, attempt)

    # Fallback w kodzie, nie w prompcie: model nie użył toola — wysyłamy na other@.
    mailer.send_email(settings=settings, department=Department.OTHER, reply_to=email, body=message)
    elapsed = time.perf_counter() - t0
    logger.warning(
        "request_id=%s department=other attempts=%d fallback=True elapsed=%.2fs "
        "(incydent: brak tool calla po %d próbach)",
        request_id,
        MAX_ATTEMPTS,
        elapsed,
        MAX_ATTEMPTS,
    )
    return RoutingResult(
        department=Department.OTHER,
        attempts=MAX_ATTEMPTS,
        fallback=True,
        request_id=request_id,
    )
