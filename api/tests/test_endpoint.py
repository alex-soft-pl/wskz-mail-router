import pytest
from fastapi.testclient import TestClient

from app import main
from app.agent import AgentUnavailableError, RoutingResult
from app.departments import Department


@pytest.fixture
def routed_calls(monkeypatch):
    calls = []

    async def fake_route(settings, email, message):
        calls.append({"email": email, "message": message})
        return RoutingResult(
            department=Department.IT, attempts=1, fallback=False, request_id="test1234"
        )

    monkeypatch.setattr(main, "route_and_send", fake_route)
    return calls


@pytest.fixture
def client():
    return TestClient(main.app)


def test_route_returns_department_and_recipient(client, routed_calls):
    resp = client.post(
        "/api/v1/route",
        json={"email": "jan.nowak@example.com", "message": "Nie działa mi komputer"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"department": "it", "recipient": "it@example.com"}


def test_route_passes_email_and_message_to_agent(client, routed_calls):
    client.post(
        "/api/v1/route",
        json={"email": "anna.kowalska@firma.pl", "message": "Ile dni urlopu mi zostało?"},
    )
    assert routed_calls == [
        {"email": "anna.kowalska@firma.pl", "message": "Ile dni urlopu mi zostało?"}
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "nie-email", "message": "test"},
        {"email": "jan@example.com", "message": ""},
        {"email": "jan@example.com"},
        {"message": "test"},
        {},
    ],
)
def test_route_invalid_input_returns_422(client, routed_calls, payload):
    resp = client.post("/api/v1/route", json=payload)
    assert resp.status_code == 422
    assert routed_calls == []


def test_route_returns_503_when_ollama_unavailable(client, monkeypatch):
    async def fake_route(settings, email, message):
        raise AgentUnavailableError("connection refused")

    monkeypatch.setattr(main, "route_and_send", fake_route)
    resp = client.post("/api/v1/route", json={"email": "jan@example.com", "message": "test"})
    assert resp.status_code == 503
    assert "Ollama" in resp.json()["detail"]


def test_swagger_available_under_api_v1_docs(client):
    assert client.get("/api/v1/docs").status_code == 200
    openapi = client.get("/api/v1/openapi.json")
    assert openapi.status_code == 200
    paths = openapi.json()["paths"]
    assert "/api/v1/route" in paths
    assert "/api/v1/health" in paths
