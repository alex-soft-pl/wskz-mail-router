# Etap 6 — wyniki: uruchamialny eval z macierzą pomyłek

Data: 2026-08-24 · branch `etap6` (PR #1, zmergowany do main) · commity `d43dd9b`, `c01f45f`

## Co powstało

- **Dataset** `api/app/eval/dataset.py` — 44 zamrożone przypadki w 6 kategoriach:
  basic 10 (oryginalne 8 z Etapu 0 — ciągłość pomiaru), code-switching 6,
  typos 6, multi-topic 5, adversarial 12, edge 5. Test jednostkowy pilnuje
  braku kontaminacji przykładami few-shot z promptu.
- **Runner** `make eval` / `python -m app.eval` — bije w żywy endpoint API
  (pełny tor z retry/fallbackiem); flagi `--direct`, `--category`, `--runs N`;
  raport markdown + `latest.json` do `docs/eval/`; macierz pomyłek, accuracy
  per kategoria, p50/p95; exit code ≠ 0 przy accuracy < `EVAL_THRESHOLD` (0.85).
- 11 testów jednostkowych logiki evala (bez modelu i HTTP); łącznie 28 testów.

## Wyniki: 24/44 (55%) → 34/44 (77%)

| kategoria | start | po iteracjach |
|---|---|---|
| basic | 9/10 | **10/10** |
| typos | 5/6 | **6/6** |
| code-switching | 4/6 | **6/6** |
| edge | 2/5 | **4/5** |
| multi-topic | 2/5 | 3/5 |
| adversarial | 2/12 | 5/12 |