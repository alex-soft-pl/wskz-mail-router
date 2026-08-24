# Etap 2 — wyniki: agent pydantic-ai

Data: 2026-08-24 · commit `etap-2` (1fdf4b5) · pydantic-ai 2.33.0

## Co powstało

`app/agent.py` — agent podłączony do Ollamy przez endpoint OpenAI-compatible (`/v1`):

- Tool `send_email(department: Department)` — enum walidowany przez pydantic; dział spoza listy → automatyczny retry z komunikatem walidacji. **Reply-To wstrzykiwany z deps (kontekst requestu), model nie ma dostępu do adresu.**
- Konfiguracja z Etapu 0 przeniesiona 1:1: krótkie opisy działów, 3 przykłady few-shot jako `message_history` (`ToolCallPart`/`ToolReturnPart`), `temperature=0` + jawna reguła kadry vs human-resources.
- Niezawodność: retry ×2 przy braku tool calla → fallback `other@` + log WARNING (fallback w kodzie, nie w prompcie). Ollama niedostępna → `AgentUnavailableError` → **503** z czytelnym komunikatem, nigdy surowe 500. Timeout 120 s.
- Logi strukturalne: `request_id`, dział, liczba prób, czas.

## Weryfikacja (punkty planu ✅)

| Punkt | Wynik |
|---|---|
| `pytest -q` bez Ollamy | 16 passed (`FunctionModel`) |
| e2e 8 wiadomości z Etapu 0 | 8/8 tool calli, 7/8 poprawnych działów (progi: ≥7/8, ≥6/8) |
| Maile w MailHog | właściwi adresaci, `Reply-To` z requestu |
| Wyłączona Ollama | kontrolowane 503, zero maili |

## Zakres testów (FunctionModel — bez prawdziwej Ollamy)

- Happy path: tool call → mail + `RoutingResult(attempts=1, fallback=False)`.
- Fallback: model uparcie odpowiada tekstem → dokładnie `MAX_ATTEMPTS` prób → jeden mail na `other@`.
- Dział spoza enum (`marketing`) → retry-prompt walidacji → poprawny wybór; zły dział nigdy nie dociera do mailera.
- Ollama down (prawdziwy klient HTTP na martwy port) → `AgentUnavailableError`, zero maili.
- Endpoint: 200/422/503, kontrakt odpowiedzi, Swagger.

## Znane ograniczenie (świadoma decyzja)

„Potrzebuję zaświadczenie o zatrudnieniu" → `human-resources` (powinno: `kadry`), deterministycznie. Model 3B przez endpoint `/v1` (inny szablon tooli niż natywne `/api/chat` z Etapu 0) kojarzy „zatrudnienie" z HR. Sprawdzono 4 konfiguracje promptu/few-shot — każda daje stabilne 7/8, błąd tylko przeskakuje między przypadkami granicznymi kadry/HR; dalsze dostrajanie = przeuczenie pod 8 zdań testowych. Progi planu spełnione. Do opisania w README jako limit modelu 3B.
