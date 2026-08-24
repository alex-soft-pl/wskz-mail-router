import pytest
from fastapi.testclient import TestClient

from app import main
from app.departments import Department


@pytest.fixture
def sent_mails(monkeypatch):
    sent = []

    def fake_send(settings, department, reply_to, body):
        sent.append({"department": department, "reply_to": reply_to, "body": body})

    monkeypatch.setattr(main.mailer, "send_email", fake_send)
    return sent


@pytest.fixture
def client():
    return TestClient(main.app)


def test_route_returns_department_and_recipient(client, sent_mails):
    resp = client.post(
        "/api/v1/route",
        json={"email": "jan.nowak@example.com", "message": "Nie działa mi komputer"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["department"] in [d.value for d in Department]
    assert data["recipient"] == f"{data['department']}@example.com"


def test_route_sends_mail_with_reply_to_from_request(client, sent_mails):
    client.post(
        "/api/v1/route",
        json={"email": "anna.kowalska@firma.pl", "message": "Ile dni urlopu mi zostało?"},
    )
    assert len(sent_mails) == 1
    assert sent_mails[0]["reply_to"] == "anna.kowalska@firma.pl"
    assert sent_mails[0]["body"] == "Ile dni urlopu mi zostało?"


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
def test_route_invalid_input_returns_422(client, sent_mails, payload):
    resp = client.post("/api/v1/route", json=payload)
    assert resp.status_code == 422
    assert sent_mails == []


def test_swagger_available_under_api_v1_docs(client):
    assert client.get("/api/v1/docs").status_code == 200
    openapi = client.get("/api/v1/openapi.json")
    assert openapi.status_code == 200
    assert "/api/v1/route" in openapi.json()["paths"]
