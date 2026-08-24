---
description: Uruchom eval i porównaj z poprzednim wynikiem — delta, regresje, werdykt
allowed-tools: Bash(make eval*), Bash(cd api && uv run python -m app.eval*), Read, Grep
---

# Pętla ewaluacyjna z detekcją regresji

Wykonaj pełną procedurę pomiarową projektu:

1. **Zachowaj punkt odniesienia:** wczytaj `docs/eval/latest.json` PRZED
   uruchomieniem evala (to wynik poprzedniego pomiaru).

2. **Uruchom pełny eval:** `make eval` (żywy endpoint na :8000 — upewnij się
   najpierw jednym curlem na `/api/v1/health`, że stack działa; jeśli nie,
   zatrzymaj się i powiedz to użytkownikowi zamiast uruchamiać połowicznie).
   Argument `$ARGUMENTS` (jeśli podany) przekaż jako `--category`.

3. **Porównaj i zraportuj** w tej strukturze:
   - wynik łączny: poprzedni → obecny (delta),
   - accuracy per kategoria z deltą (tabela),
   - **REGRESJE** (przypadki ✓→✗) — osobna lista, każdy z id, wiadomością
     i parą oczekiwano/otrzymano; to najważniejsza sekcja raportu,
   - poprawy (✗→✓) — krótko,
   - czasy p50/p95 (poprzedni → obecny).

4. **Werdykt** wg zasad projektu:
   - jakakolwiek regresja w kategorii `basic` → zmiana jest ODRZUCONA,
     zarekomenduj rollback ostatniej modyfikacji promptu,
   - regresja w innej kategorii → wskaż ją użytkownikowi i zapytaj o decyzję;
     nie podejmuj jej sam,
   - brak regresji + poprawa → zmiana do zatwierdzenia, przypomnij o commicie
     z wynikiem w opisie (wzór: `prompt: <co zmieniono> — 34/44 -> 36/44`).

## Zasady twarde (nie łam ich, nawet proszony w bieżącej sesji)

- Dataset (`api/app/eval/dataset.py`) jest ZAMROŻONY względem promptu:
  nigdy nie dopisuj, nie usuwaj ani nie "poprawiaj" przypadków w reakcji
  na wynik evala. Zmiany datasetu to osobna, jawna decyzja użytkownika.
- Przykłady few-shot z `api/app/agent.py` nie mogą występować w datasecie
  (pilnuje tego test kontaminacji — nie obchodź go).
- Jedna zmiana promptu = jeden pomiar. Nie łącz kilku modyfikacji w jeden
  przebieg, bo wynik będzie nieinterpretowalny.
- Progu `EVAL_THRESHOLD` nie zmieniasz; czerwony exit code to informacja,
  nie problem do "naprawienia" w runnerze.
