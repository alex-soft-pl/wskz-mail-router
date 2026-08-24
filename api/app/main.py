import logging

from fastapi import FastAPI, HTTPException

from app.agent import AgentUnavailableError, route_and_send
from app.config import get_settings
from app.schemas import RouteRequest, RouteResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="WSKZ AI Message Router",
    version="0.2.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
)


@app.post("/api/v1/route", response_model=RouteResponse)
async def route_message(request: RouteRequest) -> RouteResponse:
    """Przyjmij zgłoszenie; agent AI wybiera dział i wysyła e-mail z Reply-To nadawcy."""
    settings = get_settings()
    try:
        result = await route_and_send(
            settings=settings, email=str(request.email), message=request.message
        )
    except AgentUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail="Silnik LLM (Ollama) jest chwilowo niedostępny. Spróbuj ponownie później.",
        ) from exc
    return RouteResponse(department=result.department, recipient=result.department.email)


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    """Prosty healthcheck API (używany też przez healthcheck kontenera)."""
    return {"status": "ok"}
