---
description: Checklista przed wysyłką repo do rekrutera — świeży klon, spójność, higiena
allowed-tools: Bash(git*), Bash(docker compose*), Bash(curl*), Bash(ls*), Bash(cat*), Bash(grep*), Bash(mktemp*), Read, Grep, Glob
---

# Release check: ostatnia mila przed wysyłką

Przejdź checklistę i zwróć raport ✅/⚠️/❌ per punkt. Niczego nie poprawiaj
bez pytania — od decyzji jest użytkownik.

## 1. Świeży klon

- sklonuj repo z GitHuba (nie kopiuj lokalnego katalogu!) do katalogu tmp,
- porównaj: czy stan `main` na GitHubie == lokalny (`git fetch && git status`),
- w klonie: czy jest wszystko, czego wymaga README, i NIC ponadto
  (żadnych plików spoza `.gitignore`, które wyciekły do repo).

## 2. Higiena repo

- `.gitignore` pokrywa: `.env`, `__pycache__`, `.venv`, `.DS_Store`,
- brak sekretów: przeszukaj repo pod kątem wzorców (api_key, token, password,
  prywatne adresy e-mail inne niż example.com),
- LICENSE istnieje (repo publiczne) — jeśli nie: ❌ i przypomnij o decyzji,
- `git log --oneline`: historia czytelna, prefiksy `etap-N:`, brak commitów
  typu "wip"/"fix2"/"asdf"; jeśli są → zaproponuj (nie wykonuj) plan sprzątania.

## 3. Spójność dokumentacji ze stanem faktycznym

- DoD z `docs/ZADANIE.md`: każdy punkt ma pokrycie w README i w działaniu,
- PLAN.md ↔ README ↔ rzeczywistość: statusy etapów zgodne (szczególnie
  notka o zakresie Etapu 5 zrealizowanym w ramach Etapu 6),
- liczby w README (wynik evala, czasy startu, liczba testów) zgodne
  z `docs/eval/latest.json` i ostatnim smoke — nieaktualne liczby to ⚠️,
- linki w README działają (w tym badge CI — sprawdź, że wskazuje na main
  i jest zielony),
- każde polecenie z bloków kodu README da się wykonać dosłownie
  (skopiuj-wklej, bez domyślania się).

## 4. Weryfikacja działania z klonu

- w świeżym klonie: `docker compose up -d` i skrócona ścieżka DoD
  (jeden cURL + mail w MailHog + Swagger). Pełny smoke jest w `/smoke` —
  tu wystarczy potwierdzenie, że klon != kopia robocza niczego nie psuje.

## 5. Raport końcowy

Tabela punktów z werdyktami + lista działań do wykonania przed wysyłką,
posortowana od blokujących. Na końcu jedno zdanie: gotowe do wysyłki TAK/NIE.
