# Etap 0 — wyniki walidacji tool callingu (qwen2.5:3b)

Data: 2026-08-24 · Ollama 0.32.15 natywnie na hoście (Metal) · `temperature=0` · skrypt: `scripts/probe_tool_calling.py`

## Wynik końcowy (konfiguracja few-shot)

| Wiadomość | Oczekiwany dział | Otrzymany | Czas |
|---|---|---|---|
| Nie działa mi komputer | it | it ✓ | 0.52 s |
| Chciałbym zgłosić urlop na jutro | kadry | kadry ✓ | 0.55 s |
| Potrzebuję zaświadczenie o zatrudnieniu | kadry | kadry ✓ | 0.62 s |
| Nie mogę się zalogować do systemu | help-desk | help-desk ✓ | 0.84 s |
| Pytanie o proces rekrutacji na stanowisko developera | human-resources | human-resources ✓ | 0.86 s |
| Ile dni urlopu mi zostało? | kadry | kadry ✓ | 0.78 s |
| Padł serwer produkcyjny! | it | it ✓ | 0.68 s |
| Kupię tanio garaż | other | other ✓ | 0.66 s |

- **Tool calle: 8/8 (100%)** — próg ≥ 7/8 ✅
- **Poprawny dział: 8/8 (100%)** — próg ≥ 6/8 ✅
- Czas odpowiedzi: 0.5–0.9 s (avg ~0.7 s) na natywnej Ollamie z Metal; w kontenerze CPU będzie wolniej.
- Stabilność: 3 pełne przebiegi z rzędu, wszystkie 8/8.

## Kluczowe odkrycie: few-shot jest NIEZBĘDNY

Bez przykładów few-shot (sam system prompt, nawet z instrukcją „zawsze wywołaj narzędzie") model osiągał tylko **4/8 tool calli**. Dwa tryby porażki:

1. **Odpowiedź tekstowa** zamiast tool calla (model dopytuje użytkownika).
2. **Pusta odpowiedź** — `eval_count≈15` przy pustym `content` i braku `tool_calls`: model emituje źle sformatowany tool call, który parser Ollamy odrzuca po cichu.

Konfiguracja zwycięska (do przeniesienia do agenta w Etapie 2):

- System prompt: krótka lista działów z **krótkimi** opisami (długie opisy pogarszały wynik: 6/8) + „Nigdy nie odpowiadaj tekstem."
- **3 przykłady few-shot** w historii wiadomości: `user → assistant(tool_call)` dla działów it, kadry, help-desk.
- `temperature=0`.

| Konfiguracja | Tool calle | Poprawne |
|---|---|---|
| sam system prompt (długi) | 4/8 | 4/8 |
| sam system prompt (krótki) | ~5–6/8 | ~5/8 |
| few-shot + długie opisy działów | 7/8 | 6/8 |
| **few-shot + krótkie opisy działów** | **8/8** | **8/8** |

## Wniosek

`qwen2.5:3b` przechodzi próg z zapasem — **pod warunkiem** użycia few-shot i krótkiego promptu. Mimo to fallback w kodzie (retry ×2 → `other@`) pozostaje konieczny (reguła krytyczna nr 3 w CLAUDE.md), bo tryb „pustej odpowiedzi" może wystąpić dla nietypowych wiadomości spoza zestawu testowego.

Surowe wyniki ostatniego przebiegu: `scripts/probe_results.json`.
