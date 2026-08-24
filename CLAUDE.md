# CLAUDE.md — WSKZ PoC: AI Message Router

## Czym jest ten projekt

Proof of Concept mikroserwisowej aplikacji-routera wiadomości (zadanie rekrutacyjne WSKZ, stanowisko AI Automation Engineer). API przyjmuje `{email, message}`, agent AI (pydantic-ai + lokalna Ollama) interpretuje treść i **poprzez tool calling** wysyła e-mail do właściwego działu. Mail przechwytuje MailHog.

Pełna treść zadania: `docs/ZADANIE.md` (przeczytaj przed rozpoczęciem pracy).

## Stack — decyzje NIEPODLEGAJĄCE zmianie bez zgody użytkownika

- **Python 3.12 + FastAPI + pydantic-ai** (nie langchain)
- **Ollama** z modelem `qwen2.5:3b` (tool calling + dobra polszczyzna)
- **MailHog** (`mailhog/mailhog`) — SMTP :1025, web UI :8025
- Swagger MUSI być pod `/api/v1/docs` (FastAPI: `docs_url="/api/v1/docs"`)
- Docker Compose z auto-pullem modelu (wzorzec ollama-init + `service_completed_successfully`)

## Architektura

```
POST /api/v1/route  {email, message}
        │
        ▼
  Agent (pydantic-ai) ──► Ollama (OLLAMA_URL, model z env MODEL)
        │  tool: send_email(department)
        ▼
  SMTP → MailHog (Reply-To = email z requestu)
```

### Reguły krytyczne

1. **Reply-To pochodzi z requestu, NIE od modelu.** Tool przyjmuje od agenta wyłącznie wybór działu (enum); adres nadawcy jest wstrzykiwany z kontekstu requestu. Model nigdy nie przepisuje adresu e-mail.
2. **Dozwolone działy — twardy enum** (`Literal` w schemacie toola + walidacja w kodzie):
   - `human-resources@example.com` — sprawy HR "miękkie"/anglojęzyczne: rekrutacja, benefity, onboarding
   - `kadry@example.com` — sprawy kadrowo-administracyjne PL: urlopy, L4, zaświadczenia, umowy
   - `help-desk@example.com` — ogólne wsparcie użytkownika, dostępy, hasła
   - `it@example.com` — awarie sprzętu/systemów, infrastruktura
   - `other@example.com` — fallback dla nierozpoznanych
3. **Fallback w kodzie, nie tylko w prompcie**: brak tool calla po N=2 retry → wyślij na `other@` i zaloguj incydent. API nigdy nie zwraca 500 z powodu "głupiego" modelu.
4. **Timeout klienta HTTP do Ollamy: 120 s** (CPU w kontenerze jest wolne; pierwszy request ładuje model).
5. Konfiguracja wyłącznie przez env: `OLLAMA_URL`, `MODEL`, `SMTP_HOST`, `SMTP_PORT`. Zero hardkodów — kod musi działać identycznie natywnie (dev, Metal) i w compose.

## Środowiska

- **Dev (domyślne przy pracy z Claude Code):** natywna Ollama na hoście (`http://localhost:11434`, Metal, szybka), API przez `uvicorn` na hoście, MailHog jako pojedynczy kontener.
- **Weryfikacja końcowa:** pełny `docker compose up -d` od zera (`docker compose down -v` wcześniej).

## Workflow pracy — OBOWIĄZKOWY

Praca przebiega etapami wg `docs/PLAN.md`. Zasady:

1. **Jeden etap na raz.** Nie zaczynaj kolejnego etapu, dopóki bieżący nie przejdzie swojej sekcji "Weryfikacja".
2. **Każdy etap kończy się:** (a) przejściem testów automatycznych `pytest`, (b) wykonaniem komend weryfikacyjnych z planu, (c) krótkim podsumowaniem dla użytkownika: co zrobione, co zweryfikowane, co dalej.
3. **Testy piszemy razem z kodem**, nie po fakcie. Minimalny zestaw: testy jednostkowe logiki toola i walidacji + testy integracyjne endpointu (z mockiem agenta) + smoke-test e2e opisany w planie.
4. **Commity po każdym etapie** z prefiksem `etap-N:` — użytkownik ma widzieć historię przyrostu.
5. **Punkty STOP (wymagana obecność użytkownika)** są oznaczone w `docs/PLAN.md` — zatrzymaj się i poproś o potwierdzenie, nie kontynuuj automatycznie.
6. Jeśli coś nie działa zgodnie z założeniem (np. model nie robi tool calli) — **nie zmieniaj cicho architektury**. Opisz problem, zaproponuj 2 opcje, czekaj na decyzję.

## Komendy

```bash
# dev
uvicorn app.main:app --reload --port 8000
pytest -q
ruff check . && ruff format --check .

# smoke test lokalny
curl -s -X POST localhost:8000/api/v1/route \
  -H 'Content-Type: application/json' \
  -d '{"email":"jan.nowak@example.com","message":"Nie działa mi komputer"}'

# pełny stack
docker compose down -v && docker compose up -d --build
open http://localhost:8025   # MailHog UI
```

## Definicja ukończenia projektu (DoD z zadania)

- [ ] `docker compose up -d` podnosi API + MailHog + Ollamę z pobranym modelem
- [ ] Swagger pod `/api/v1/docs`
- [ ] `README.md` z instrukcją, decyzjami architektonicznymi i przykładowym cURL
- [ ] Request → analiza → mail widoczny w MailHog
- [ ] Mail zaadresowany do prawidłowego działu
- [ ] Mail ma poprawny nagłówek `Reply-To`
