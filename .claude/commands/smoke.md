---
description: Symulacja rekrutera — zimny start compose i weryfikacja DoD e2e
allowed-tools: Bash(docker compose*), Bash(docker inspect*), Bash(curl*), Bash(sleep*), Bash(date*), Read
---

# Smoke test: pierwsze uruchomienie oczami rekrutera

Symulujesz osobę, która właśnie sklonowała repo i zna WYŁĄCZNIE README.
Wykonaj i zmierz:

1. **Zimny stan:** `docker compose down -v` (kasuje też volume z modelem —
   to celowe: rekruter nie ma naszego cache). Zanotuj czas startu procedury.

2. **Start:** `docker compose up -d --build`. Czekaj na `api` = `healthy`
   (pętla na `docker inspect`, max 15 min — pull modelu). Zmierz łączny czas
   od `up` do `healthy` i porównaj z deklaracją w README (~70 s na szybkim
   łączu); rozbieżność > 2× → zaznacz do korekty README.

3. **Ścieżka DoD** — dokładnie te asercje, w tej kolejności:
   - cURL z README ("Nie działa mi komputer") → HTTP 200, `department` = `it`,
   - Swagger: `curl -sf localhost:8000/api/v1/docs` → 200,
   - MailHog API (`localhost:8025/api/v2/messages`): ostatni mail ma
     `To == ["it@example.com"]` i `Reply-To` równy adresowi z requestu,
   - drugi cURL (urlop → kadry) i trzeci (garaż → other) — z README,
     każdorazowo sprawdź mail w MailHog, nie tylko odpowiedź API,
   - restart bez `-v` (`down` + `up -d`) → API healthy w < 30 s
     (model z volume, bez ponownego pobierania).

4. **Raport końcowy:** tabela DoD (punkt / wynik / czas), zmierzone czasy
   zimnego i ciepłego startu, lista rozbieżności z README (jeśli są).

## Zasady

- Niczego nie naprawiaj w trakcie — smoke ma zmierzyć stan faktyczny.
  Problemy zbierz do raportu; naprawy to osobna decyzja po przeglądzie.
- Jeśli którykolwiek krok wymaga wiedzy spoza README (np. brakująca
  instrukcja, niejawna zmienna env) — to jest DEFEKT README, zapisz go
  nawet jeśli sam znasz obejście.
