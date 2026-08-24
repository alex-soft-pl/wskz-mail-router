"""CLI evala.

Domyślnie bije w prawdziwy endpoint API (cały tor: agent + retry + SMTP):
    uv run python -m app.eval --url http://localhost:8000

Flagi:
    --direct        z pominięciem API/SMTP (route_and_send w procesie, mail no-op)
                    — do szybkiej iteracji promptu na natywnej Ollamie
    --category X    tylko jedna kategoria (można podać kilka razy)
    --runs N        ile pełnych przebiegów (domyślnie 1; N=3 wykrywa niestabilność)
    --out-dir DIR   katalog raportów (domyślnie <repo>/docs/eval)

Kod wyjścia != 0, gdy accuracy łączne < progu (env EVAL_THRESHOLD, domyślnie 0.85).
"""

import argparse
import asyncio
import json
import os
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from app.eval.core import CaseResult, render_report_markdown, summarize, validate_dataset
from app.eval.dataset import CASES

DEFAULT_OUT_DIR = Path(__file__).resolve().parents[3] / "docs" / "eval"


def classify_via_api(url: str, message: str) -> str:
    body = json.dumps({"email": "eval@example.com", "message": message}).encode()
    req = urllib.request.Request(f"{url}/api/v1/route", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=400) as resp:
        return json.load(resp)["department"]


def make_direct_classifier():
    """route_and_send w procesie, z wysyłką maili zastąpioną no-opem."""
    from app import agent as agent_mod
    from app.config import get_settings

    agent_mod.mailer.send_email = lambda **kwargs: None  # tylko proces evala
    settings = get_settings()

    def classify(message: str) -> str:
        result = asyncio.run(agent_mod.route_and_send(settings, "eval@example.com", message))
        return result.department.value

    return classify


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app.eval")
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--direct", action="store_true")
    parser.add_argument("--category", action="append", default=None)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    problems = validate_dataset()
    if problems:
        print("BŁĄD datasetu:", *problems, sep="\n  - ")
        return 2

    cases = CASES if not args.category else [c for c in CASES if c["category"] in args.category]
    if not cases:
        print(f"brak przypadków dla kategorii {args.category}")
        return 2

    classify = (
        make_direct_classifier()
        if args.direct
        else (lambda message: classify_via_api(args.url, message))
    )
    target = "direct (route_and_send w procesie)" if args.direct else args.url
    threshold = float(os.environ.get("EVAL_THRESHOLD", "0.85"))

    results: list[CaseResult] = []
    for run in range(1, args.runs + 1):
        for case in cases:
            t0 = time.perf_counter()
            got = classify(case["message"])
            elapsed = time.perf_counter() - t0
            r = CaseResult(
                id=case["id"],
                category=case["category"],
                message=case["message"],
                expected=case["expected"],
                got=got,
                time_s=round(elapsed, 2),
                run=run,
            )
            results.append(r)
            mark = "✓" if r.ok else "✗"
            print(
                f"{mark} [{r.id:4s}] {r.message[:52]:54s} "
                f"oczekiwano={r.expected:16s} otrzymano={r.got} ({r.time_s}s)"
            )

    summary = summarize(results)
    meta = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "target": target,
        "runs": args.runs,
        "threshold": threshold,
    }
    print(f"\nŁącznie: {summary.correct}/{summary.total} (accuracy {summary.accuracy:.2%})")
    for cat, (ok, n) in summary.per_category.items():
        print(f"  {cat:15s} {ok}/{n}")
    print(f"czas: p50={summary.p50_s:.1f}s p95={summary.p95_s:.1f}s")
    if summary.unstable_ids:
        print(f"niestabilne między runami: {', '.join(summary.unstable_ids)}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    report_path = args.out_dir / f"{stamp}.md"
    report_path.write_text(render_report_markdown(summary, results, meta), encoding="utf-8")
    (args.out_dir / "latest.json").write_text(
        json.dumps(
            {
                "meta": meta,
                "accuracy": summary.accuracy,
                "per_category": {
                    c: {"ok": ok, "n": n} for c, (ok, n) in summary.per_category.items()
                },
                "results": [vars(r) for r in results],
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"raport: {report_path}")

    if summary.accuracy < threshold:
        print(f"PONIŻEJ PROGU {threshold:.2f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
