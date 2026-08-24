#!/usr/bin/env python3
"""Etap 0 — sonda tool callingu qwen2.5:3b przez surowe API Ollamy (/api/chat).

Bez pydantic-ai: czysty httpx. Sprawdza, czy model niezawodnie wywołuje tool
send_email(department) po polsku i czy trafia we właściwy dział.

Uruchomienie:  uv run --with httpx python scripts/probe_tool_calling.py
Env:           OLLAMA_URL (domyślnie http://localhost:11434), MODEL (domyślnie qwen2.5:3b)
"""

import json
import os
import sys
import time

import httpx

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("MODEL", "qwen2.5:3b")

DEPARTMENTS = {
    "human-resources": "rekrutacja, benefity, onboarding",
    "kadry": "urlopy, L4, zaświadczenia, umowy",
    "help-desk": "wsparcie użytkownika, dostępy, hasła, logowanie",
    "it": "awarie sprzętu i systemów, infrastruktura, serwery",
    "other": "wszystko inne",
}

SYSTEM_PROMPT = (
    "Jesteś routerem zgłoszeń pracowniczych. Zawsze wywołaj narzędzie send_email, "
    "wybierając jeden dział:\n"
    + "\n".join(f"- {k}: {v}" for k, v in DEPARTMENTS.items())
    + "\nNigdy nie odpowiadaj tekstem."
)


def _tool_call_msg(department: str) -> dict:
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"function": {"name": "send_email", "arguments": {"department": department}}}
        ],
    }


# Few-shot: bez tych przykładów qwen2.5:3b w ~50% przypadków odpowiada tekstem
# albo emituje tool call, którego parser Ollamy odrzuca (pusta odpowiedź).
FEW_SHOT = [
    {"role": "user", "content": "Zepsuła mi się drukarka"},
    _tool_call_msg("it"),
    {"role": "user", "content": "Chcę wziąć L4"},
    _tool_call_msg("kadry"),
    {"role": "user", "content": "Zapomniałem hasła do poczty"},
    _tool_call_msg("help-desk"),
]

TOOL = {
    "type": "function",
    "function": {
        "name": "send_email",
        "description": "Przekaż zgłoszenie do wybranego działu.",
        "parameters": {
            "type": "object",
            "properties": {
                "department": {
                    "type": "string",
                    "enum": list(DEPARTMENTS.keys()),
                    "description": "Dział, do którego trafi zgłoszenie.",
                }
            },
            "required": ["department"],
        },
    },
}

CASES = [
    ("Nie działa mi komputer", "it"),
    ("Chciałbym zgłosić urlop na jutro", "kadry"),
    ("Potrzebuję zaświadczenie o zatrudnieniu", "kadry"),
    ("Nie mogę się zalogować do systemu", "help-desk"),
    ("Pytanie o proces rekrutacji na stanowisko developera", "human-resources"),
    ("Ile dni urlopu mi zostało?", "kadry"),
    ("Padł serwer produkcyjny!", "it"),
    ("Kupię tanio garaż", "other"),
]


def probe_one(client: httpx.Client, message: str):
    """Zwraca (department|None, elapsed_s, raw_content)."""
    t0 = time.perf_counter()
    resp = client.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": MODEL,
            "stream": False,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                *FEW_SHOT,
                {"role": "user", "content": message},
            ],
            "tools": [TOOL],
            "options": {"temperature": 0},
        },
    )
    elapsed = time.perf_counter() - t0
    resp.raise_for_status()
    msg = resp.json()["message"]
    calls = msg.get("tool_calls") or []
    for call in calls:
        fn = call.get("function", {})
        if fn.get("name") == "send_email":
            args = fn.get("arguments") or {}
            if isinstance(args, str):
                args = json.loads(args)
            return args.get("department"), elapsed, msg
    return None, elapsed, msg


def main() -> int:
    results = []
    with httpx.Client(timeout=120) as client:
        for message, expected in CASES:
            dept, elapsed, raw_msg = probe_one(client, message)
            ok_call = dept is not None
            ok_dept = dept == expected
            results.append(
                {
                    "message": message,
                    "expected": expected,
                    "got": dept,
                    "tool_call": ok_call,
                    "correct": ok_dept,
                    "time_s": round(elapsed, 2),
                    "raw_message": raw_msg,
                }
            )
            mark = "✓" if ok_dept else ("~" if ok_call else "✗")
            print(f"{mark} {message!r:55s} oczekiwano={expected:15s} otrzymano={dept} ({elapsed:.2f}s)")

    n = len(results)
    calls = sum(r["tool_call"] for r in results)
    correct = sum(r["correct"] for r in results)
    times = [r["time_s"] for r in results]
    print(f"\nTool calle: {calls}/{n} ({100 * calls // n}%)")
    print(f"Poprawny dział: {correct}/{n} ({100 * correct // n}%)")
    print(f"Czas odpowiedzi: min={min(times)}s max={max(times)}s avg={sum(times) / n:.2f}s")

    print(json.dumps({"model": MODEL, "results": results}, ensure_ascii=False, indent=2),
          file=open("scripts/probe_results.json", "w", encoding="utf-8"))

    ok = calls >= 7 and correct >= 6
    print("\nPRÓG:", "ZALICZONY (≥7/8 tool calli, ≥6/8 poprawnych)" if ok else "NIEZALICZONY")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
