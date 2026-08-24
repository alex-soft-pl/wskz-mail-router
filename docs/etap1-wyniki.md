# Etap 1 — wyniki: szkielet API + MailHog (bez AI)

Data: 2026-08-24 · commit `etap-1` (7cfdf34)

## Co powstało

```
api/
  app/
    main.py          # FastAPI, docs_url="/api/v1/docs", POST /api/v1/route, GET /api/v1/health
    config.py        # Settings z env: OLLAMA_URL, MODEL, SMTP_HOST, SMTP_PORT (zero hardkodów)
    schemas.py       # RouteRequest{email: EmailStr, message: str 1..10000}, RouteResponse
    mailer.py        # build_message + send_email przez smtplib; Reply-To z requestu
    departments.py   # StrEnum 5 działów + krótkie opisy (jedno źródło prawdy)
  tests/             # 11 testów
  pyproject.toml     # zarządzanie przez uv, Python 3.12, ruff
```

Routing na tym etapie atrapowy (zawsze `other@`), ale mail realnie wychodzi do MailHog.

## Weryfikacja (wszystkie punkty planu ✅)

| Punkt | Wynik |
|---|---|
| `pytest -q` | 11 passed |
| `ruff check` + `ruff format --check` | czysto |
| cURL → MailHog (`/api/v2/messages`) | mail widoczny, `To: other@example.com` |
| Nagłówek `Reply-To` | `jan.nowak@example.com` (z requestu) ✅ |
| Swagger `/api/v1/docs` | HTTP 200 |

## Zakres testów

- Walidacja wejścia: zły e-mail, pusty message, brakujące pola → 422, mail nie wychodzi.
- Mailer: nagłówki MIME (`To`/`Reply-To`/`From`/`Subject`), poprawny adresat dla każdego działu, użycie hosta/portu z `Settings` (fake `smtplib.SMTP`).
- Endpoint: kontrakt odpowiedzi, przekazanie `Reply-To` (mock mailera).

## Decyzje

- `uv` + lockfile zamiast requirements.txt — deterministyczna instalacja, ta sama ścieżka w Dockerfile (Etap 3).
- MailHog w dev jako pojedynczy kontener (`mailhog-dev`), pełny compose dopiero w Etapie 3.
