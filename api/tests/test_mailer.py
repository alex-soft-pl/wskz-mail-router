import smtplib

from app.config import Settings
from app.departments import Department
from app.mailer import FROM_ADDRESS, build_message, send_email


def test_build_message_headers():
    msg = build_message(
        department=Department.IT,
        reply_to="jan.nowak@example.com",
        body="Nie działa mi komputer",
    )
    assert msg["To"] == "it@example.com"
    assert msg["Reply-To"] == "jan.nowak@example.com"
    assert msg["From"] == FROM_ADDRESS
    assert msg["Subject"]
    assert "Nie działa mi komputer" in msg.get_content()


def test_build_message_every_department_has_valid_recipient():
    for dept in Department:
        msg = build_message(department=dept, reply_to="a@b.pl", body="x")
        assert msg["To"] == f"{dept.value}@example.com"


class _FakeSMTP:
    sent: list = []

    def __init__(self, host, port, timeout=None):
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def send_message(self, msg):
        _FakeSMTP.sent.append((self.host, self.port, msg))


def test_send_email_uses_settings_and_sends(monkeypatch):
    _FakeSMTP.sent.clear()
    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)
    settings = Settings(smtp_host="smtp.test", smtp_port=2525)

    send_email(
        settings=settings,
        department=Department.KADRY,
        reply_to="anna@example.com",
        body="Wniosek o urlop",
    )

    assert len(_FakeSMTP.sent) == 1
    host, port, msg = _FakeSMTP.sent[0]
    assert (host, port) == ("smtp.test", 2525)
    assert msg["To"] == "kadry@example.com"
    assert msg["Reply-To"] == "anna@example.com"
