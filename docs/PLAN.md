# PLAN.md — Etapy pracy z weryfikacją

> Zasada: etap = kod + testy + weryfikacja + commit `etap-N: ...` + raport dla użytkownika.
> 🛑 STOP = wymagana obecność i decyzja użytkownika przed kontynuacją.

---

## Etap 0 — Walidacja środowiska i modelu 🛑 STOP na końcu

**Cel:** potwierdzić, że qwen2.5:3b robi niezawodny tool calling po polsku, ZANIM powstanie jakikolwiek kod aplikacji.

Zadania:
1. Sprawdź `ollama ls` — model `qwen2.5:3b` pobrany (jeśli nie: poproś użytkownika, nie pobieraj sam bez pytania — 2 GB).
2. Napisz skrypt `scripts/probe_tool_calling.py` (czysty httpx, bez pydantic-ai): wysyła do `/api/chat` definicję toola `send_email(department: enum)` + kolejno 8 wiadomości testowych:
   - "Nie działa mi komputer" → it
   - "Chciałbym zgłosić urlop na jutro" → kadry
   - "Potrzebuję zaświadczenie o zatrudnieniu" → kadry
   - "Nie mogę się zalogować do systemu" → help-desk
   - "Pytanie o proces rekrutacji na stanowisko developera" → human-resources
   - "Ile dni urlopu mi zostało?" → kadry
   - "Padł serwer produkcyjny!" → it
   - "Kupię tanio garaż" → other
3. Skrypt raportuje: % odpowiedzi będących tool callem, % poprawnych działów, czas odpowiedzi.

**Weryfikacja:**
- [ ] ≥ 7/8 wiadomości kończy się tool callem (nie tekstem)
- [ ] ≥ 6/8 trafia we właściwy dział
- [ ] wynik zapisany do `docs/etap0-wyniki.md`

🛑 **STOP:** pokaż wyniki użytkownikowi. Jeśli poniżej progu — przedstaw opcje (inny model / mocniejszy prompt / few-shot) i czekaj na decyzję.

---

## Etap 1 — Szkielet API + MailHog (bez AI)

**Cel:** działający FastAPI z toolem mailowym wywoływanym "ręcznie" — AI jeszcze nie ma.

Zadania:
1. Struktura projektu:
   ```
   api/
     app/
       main.py          # FastAPI, docs_url="/api/v1/docs"
       config.py        # env: OLLAMA_URL, MODEL, SMTP_HOST, SMTP_PORT
       schemas.py       # RouteRequest{email: EmailStr, message: str}, RouteResponse
       mailer.py        # send_email(department, subject, body, reply_to) przez smtplib
       departments.py   # enum działów + opisy (jedno źródło prawdy)
     tests/
   ```
2. Endpoint `POST /api/v1/route` — na tym etapie routing atrapowy (zawsze `other@`), ale mail realnie wychodzi do MailHog z Reply-To.
3. Testy: walidacja wejścia (zły email → 422), mailer (asercja nagłówków przez aiosmtpd-owy fake serwer lub inspekcję MIME), endpoint zwraca strukturę odpowiedzi.

**Weryfikacja:**
- [ ] `pytest -q` zielony
- [ ] `docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog` + cURL z CLAUDE.md → mail widoczny w MailHog API (`curl localhost:8025/api/v2/messages`)
- [ ] w mailu poprawny `Reply-To: jan.nowak@example.com`
- [ ] Swagger odpowiada pod `/api/v1/docs`

---

## Etap 2 — Agent pydantic-ai

**Cel:** podmiana atrapy na prawdziwego agenta z toolem.

Zadania:
1. `app/agent.py`: agent pydantic-ai podłączony do Ollamy (OpenAI-compatible endpoint), tool `send_email(department: Literal[...])` — adres nadawcy wstrzykiwany przez deps/kontekst, NIE przez argument od modelu.
2. System prompt po polsku z regułami rozstrzygania `kadry` vs `human-resources` (spisanymi w CLAUDE.md).
3. Logika niezawodności: retry ×2 przy braku tool calla → fallback `other@` + log WARNING. Timeout 120 s.
4. Logowanie strukturalne: request_id, wybrany dział, liczba prób, czas inferencji.
5. Testy: agent z `TestModel`/`FunctionModel` z pydantic-ai (bez prawdziwej Ollamy) — ścieżka happy, ścieżka fallback, walidacja że model nie może wskazać działu spoza enum.

**Weryfikacja:**
- [ ] `pytest -q` zielony (testy NIE wymagają działającej Ollamy)
- [ ] e2e na natywnej Ollamie: 8 wiadomości z Etapu 0 przez endpoint → wyniki nie gorsze niż w Etapie 0, maile w MailHog z właściwymi adresatami
- [ ] wyłączenie Ollamy → request kończy się kontrolowaną odpowiedzią (fallback/503 z sensownym komunikatem), nie surowym 500

---

## Etap 3 — Docker Compose (pełna konteneryzacja) 🛑 STOP na końcu

**Cel:** `docker compose up -d` od zera podnosi wszystko, zgodnie z wzorcem z CLAUDE.md.

Zadania:
1. `api/Dockerfile` (obraz `python:3.12-slim`, non-root user).
2. `docker-compose.yml`: ollama (+ named volume, healthcheck, `OLLAMA_KEEP_ALIVE=-1`, przypięty tag obrazu), ollama-init (pull + warm-up "ping"), mailhog, api (`service_completed_successfully`).
3. Warm-up i keep-alive zgodnie z ustaleniami.

**Weryfikacja (symulacja rekrutera):**
- [ ] `docker compose down -v && docker compose up -d --build` → wszystkie kontenery healthy (pierwsze uruchomienie może trwać kilka minut — pobranie modelu; zmierz i zapisz czas do README)
- [ ] cURL testowy → mail w MailHog UI
- [ ] Swagger działa pod `localhost:8000/api/v1/docs`
- [ ] restart (`down` bez `-v` + `up -d`) → start w sekundach, model z cache

🛑 **STOP:** użytkownik osobiście wykonuje pełną ścieżkę rekrutera na czystym stanie i akceptuje czasy.

---

## Etap 4 — README + polish 🛑 STOP na końcu

Zadania:
1. `README.md`: uruchomienie, przykładowe cURL-e (min. 3 różne działy), architektura z diagramem, sekcja "Decyzje architektoniczne":
   - pydantic-ai zamiast langchain (uzasadnienie)
   - wybór qwen2.5:3b + wyniki probe z Etapu 0
   - Reply-To z requestu, nie od modelu (bezpieczeństwo)
   - kadry vs human-resources — jawna reguła
   - fallback i retry — niezawodność
   - CPU-only w Dockerze na macOS; adnotacja o GPU na Linux/NVIDIA
   - dev na natywnej Ollamie (Metal), weryfikacja w compose
2. Przejdź DoD z CLAUDE.md punkt po punkcie — checklistę wklej do raportu.
3. `ruff check` czysty, brak sekretów w repo, `.gitignore`, `.env.example`.

**Weryfikacja:**
- [ ] osoba "z zewnątrz" (użytkownik) jest w stanie uruchomić projekt wyłącznie na podstawie README
- [ ] wszystkie punkty DoD odhaczone

🛑 **STOP:** finalna akceptacja przed wysłaniem do WSKZ.
