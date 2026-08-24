# Etap 3 — wyniki: pełna konteneryzacja (Docker Compose)

Data: 2026-08-24 · commit `etap-3` (a490b2c)

## Co powstało

- `api/Dockerfile`: `python:3.12-slim`, zależności przez `uv sync --frozen` (binarka uv kopiowana z obrazu astral-sh), non-root user, healthcheck-owalny endpoint `/api/v1/health`.
- `docker-compose.yml`:
  - `ollama` — przypięty tag `ollama/ollama:0.32.15`, named volume `ollama-models`, healthcheck (`ollama ls`), `OLLAMA_KEEP_ALIVE=-1` (model w RAM na stałe),
  - `ollama-init` — jednorazowy: `ollama pull` → `ollama create router-model` (patrz niżej) → warm-up `ollama run router-model "ping"`,
  - `mailhog` — `mailhog/mailhog:v1.0.1`, `platform: linux/amd64` (obraz tylko amd64), UI na :8025, SMTP tylko wewnątrz sieci compose,
  - `api` — build, start dopiero po `ollama-init: service_completed_successfully`, env: `OLLAMA_URL`, `MODEL=router-model`, `SMTP_HOST`, `SMTP_PORT`.

## Kluczowy problem i fix: wydajność CPU w kontenerze

Pierwsza wersja: request trwał **126–138 s** (o włos od timeoutu 120 s). Pomiary z logów llama.cpp:

| Konfiguracja wątków | Szybkość generacji |
|---|---|
| autodetekcja: 10 wątków (10 vCPU w VM) | **0.33 tok/s** (~3 s/token) |
| `num_thread=4` | **32–36 tok/s** (~100× szybciej) |
| `num_thread=6` | 37 tok/s |

Przyczyna: spinlocki llama.cpp na wirtualizowanych rdzeniach P/E Apple (M4, OrbStack VM) — pełne 900% CPU bez postępu. Co istotne:

- `OLLAMA_NUM_THREADS` (env) — **ignorowane** przez serwer,
- `cpuset: "0-3"` — kontener widzi 4 CPU (`nproc`=4), ale Ollama i tak startuje 10 wątków (autodetekcja czyta fizyczną liczbę CPU),
- jedyne skuteczne miejsce: `PARAMETER num_thread` **zapisany w modelu** — stąd `ollama-init` tworzy model pochodny `router-model` (`FROM ${MODEL}` + `PARAMETER num_thread ${NUM_THREAD:-4}`).

Efekt uboczny diagnozy: 10-wątkowa inferencja na pełnym CPU położyła VM OrbStacka (EOF z demona; po restarcie OK).

## Weryfikacja — symulacja rekrutera (punkty planu ✅)

| Punkt | Wynik |
|---|---|
| `docker compose down -v && docker compose up -d --build` od zera | **68 s** do wszystkich healthy (w tym pull 1.9 GB) |
| 3 cURL-e (it / kadry / other) | poprawne działy, **3–8 s/request** |
| Maile w MailHog UI | 3 maile, właściwi adresaci, `Reply-To` z requestu |
| Swagger `localhost:8000/api/v1/docs` | HTTP 200 |
| Restart (`down` bez `-v` + `up -d`) | **11 s**, model z cache |

Czasy zmierzono na M4 / OrbStack / łącze ~szybkie; na wolniejszym łączu pierwszy start zdominuje pobranie modelu (1.9 GB).

## Do rozważenia w README (Etap 4)

- `NUM_THREAD` konfigurowalny przez env (na mocnym x86 warto podnieść).
- Adnotacja o GPU na Linux/NVIDIA i o CPU-only na macOS.
