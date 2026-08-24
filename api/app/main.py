import logging

from fastapi import FastAPI

from app import mailer
from app.config import get_settings
from app.departments import Department
from app.schemas import RouteRequest, RouteResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="WSKZ AI Message Router",
    version="0.1.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
)


@app.post("/api/v1/route", response_model=RouteResponse)
def route_message(request: RouteRequest) -> RouteResponse:
    """Przyjmij zgłoszenie, wybierz dział i wyślij e-mail z Reply-To nadawcy."""
    # Etap 1: routing atrapowy — agent AI wejdzie w Etapie 2.
    department = Department.OTHER
    settings = get_settings()
    mailer.send_email(
        settings=settings,
        department=department,
        reply_to=request.email,
        body=request.message,
    )
    return RouteResponse(department=department, recipient=department.email)


@app.get("/api/v1/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "ok"}
