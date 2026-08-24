# Etap 4 — wyniki: README + polish

Data: 2026-08-24 · commit `etap-4` (4818933)

## Co powstało

- **`README.md`** — pełna dokumentacja projektu:
  - uruchomienie z czasami (zimny start ~70 s z pullem 1.9 GB, restart ~10 s),
  - 4 przykładowe cURL-e (it, kadry, help-desk, other/fallback),
  - diagram architektury ASCII + opis kontenerów,
  - sekcja „Decyzje architektoniczne": pydantic-ai vs langchain, walidacja
    qwen2.5:3b sondą przed napisaniem aplikacji (+ konieczność few-shot),
    Reply-To z requestu (bezpieczeństwo), jawna reguła kadry vs
    human-resources ze wskazaniem limitu modelu 3B, fallback/retry w kodzie,
    fix wydajności `num_thread` (0.33 → 36 tok/s), CPU vs GPU, dev na
    natywnej Ollamie,
  - tabela zmiennych env, sekcja rozwoju i testów.
- **`.env.example`** — skomentowany; wszystkie wartości mają domyślne
  (plik opcjonalny).

## Checklista DoD z zadania — zweryfikowana na żywym stacku ✅

| Punkt DoD | Wynik |
|---|---|
| `docker compose up -d` podnosi API + MailHog + Ollamę z modelem | 3 kontenery healthy |
| Swagger pod `/api/v1/docs` | HTTP 200 |
| `README.md` z instrukcją, decyzjami i przykładowym cURL | jest |
| Request → analiza → mail w MailHog | „Padł serwer produkcyjny!" → mail w skrzynce |
| Mail do prawidłowego działu | `To: it@example.com` |
| Poprawny nagłówek `Reply-To` | `dod.check@example.com` (z requestu) |

## Higiena repo

- `pytest -q`: 16 passed (bez Ollamy, `FunctionModel`).
- `ruff check` + `ruff format --check`: czyste.
- Brak sekretów (grep po `api_key|secret|password|token` — jedyne trafienie
  to placeholder `api_key="ollama"` wymagany przez klienta OpenAI).
- `.gitignore` (`.DS_Store`, `__pycache__`, `.venv`, `.env`).
- Historia commitów etapowa: `etap-0` … `etap-4` + raporty w `docs/`.

## Status projektu

Wszystkie etapy `docs/PLAN.md` ukończone. Projekt czeka na finalną
akceptację użytkownika (STOP Etapu 4): samodzielne przejście ścieżki
rekrutera wyłącznie według README przed wysłaniem do WSKZ.
