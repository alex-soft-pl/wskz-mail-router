"""Czysta logika evala: agregacja wyników, macierz pomyłek, render raportu.

Bez I/O i bez modelu — w całości pokryta testami jednostkowymi.
"""

import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from app.eval.dataset import ALL_DEPARTMENTS, CASES, EXPECTED_COUNTS


@dataclass
class CaseResult:
    id: str
    category: str
    message: str
    expected: str
    got: str
    time_s: float
    run: int = 1

    @property
    def ok(self) -> bool:
        return self.got == self.expected


@dataclass
class Summary:
    total: int
    correct: int
    accuracy: float
    per_category: dict[str, tuple[int, int]]  # kategoria -> (poprawne, wszystkie)
    confusion: dict[str, Counter]  # expected -> Counter(got)
    p50_s: float
    p95_s: float
    unstable_ids: list[str] = field(default_factory=list)  # różne wyniki między runami


def validate_dataset(cases: list[dict] = CASES) -> list[str]:
    """Zwraca listę problemów z datasetem (pusta = OK)."""
    problems = []
    ids = [c["id"] for c in cases]
    if len(ids) != len(set(ids)):
        problems.append("zduplikowane id przypadków")
    counts = Counter(c["category"] for c in cases)
    for cat, expected_n in EXPECTED_COUNTS.items():
        if counts.get(cat, 0) != expected_n:
            problems.append(
                f"kategoria {cat}: {counts.get(cat, 0)} przypadków, oczekiwano {expected_n}"
            )
    for c in cases:
        if c["expected"] not in ALL_DEPARTMENTS:
            problems.append(f"{c['id']}: expected '{c['expected']}' spoza enum działów")
        if not c["message"].strip():
            problems.append(f"{c['id']}: pusta wiadomość")
    return problems


def check_few_shot_contamination(cases: list[dict], few_shot_messages: list[str]) -> list[str]:
    """Przykłady few-shot z promptu nie mogą występować w datasecie."""
    normalized = {m.strip().lower() for m in few_shot_messages}
    return [c["id"] for c in cases if c["message"].strip().lower() in normalized]


def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round(pct / 100 * (len(ordered) - 1))))
    return ordered[idx]


def summarize(results: list[CaseResult]) -> Summary:
    per_cat: dict[str, list[CaseResult]] = defaultdict(list)
    confusion: dict[str, Counter] = defaultdict(Counter)
    by_id: dict[str, set[str]] = defaultdict(set)
    for r in results:
        per_cat[r.category].append(r)
        confusion[r.expected][r.got] += 1
        by_id[r.id].add(r.got)
    times = [r.time_s for r in results]
    correct = sum(r.ok for r in results)
    return Summary(
        total=len(results),
        correct=correct,
        accuracy=correct / len(results) if results else 0.0,
        per_category={cat: (sum(r.ok for r in rs), len(rs)) for cat, rs in sorted(per_cat.items())},
        confusion=dict(confusion),
        p50_s=statistics.median(times) if times else 0.0,
        p95_s=percentile(times, 95) if times else 0.0,
        unstable_ids=sorted(cid for cid, gots in by_id.items() if len(gots) > 1),
    )


def render_confusion_markdown(confusion: dict[str, Counter]) -> str:
    header = "| oczekiwany \\ otrzymany | " + " | ".join(ALL_DEPARTMENTS) + " |"
    sep = "|---" * (len(ALL_DEPARTMENTS) + 1) + "|"
    rows = []
    for expected in ALL_DEPARTMENTS:
        got_counts = confusion.get(expected, Counter())
        cells = []
        for got in ALL_DEPARTMENTS:
            n = got_counts.get(got, 0)
            cells.append(f"**{n}**" if got == expected and n else str(n))
        rows.append(f"| **{expected}** | " + " | ".join(cells) + " |")
    return "\n".join([header, sep, *rows])


def render_report_markdown(summary: Summary, results: list[CaseResult], meta: dict) -> str:
    lines = [
        f"# Raport ewaluacji — {meta['timestamp']}",
        "",
        f"Model/endpoint: `{meta['target']}` · przypadków: {summary.total}"
        f" (runs={meta['runs']}) · próg: {meta['threshold']}",
        "",
        f"## Wynik łączny: {summary.correct}/{summary.total}"
        f" (accuracy {summary.accuracy:.2%}) — "
        + ("✅ próg osiągnięty" if summary.accuracy >= meta["threshold"] else "❌ poniżej progu"),
        "",
        "## Accuracy per kategoria",
        "",
        "| kategoria | poprawne | accuracy |",
        "|---|---|---|",
    ]
    for cat, (ok, n) in summary.per_category.items():
        lines.append(f"| {cat} | {ok}/{n} | {ok / n:.0%} |")
    lines += [
        "",
        f"Czas odpowiedzi: p50={summary.p50_s:.1f}s p95={summary.p95_s:.1f}s",
        "",
        "## Macierz pomyłek (wiersz = oczekiwany, kolumna = otrzymany)",
        "",
        render_confusion_markdown(summary.confusion),
        "",
    ]
    if summary.unstable_ids:
        lines += [
            f"Niestabilne między runami: {', '.join(summary.unstable_ids)}",
            "",
        ]
    lines += ["## Przypadki błędne", ""]
    failures = [r for r in results if not r.ok]
    if failures:
        lines += [
            "| id | kategoria | wiadomość | oczekiwano | otrzymano |",
            "|---|---|---|---|---|",
        ]
        for r in failures:
            msg = r.message[:60].replace("|", "\\|")
            lines.append(f"| {r.id} | {r.category} | {msg} | {r.expected} | {r.got} |")
    else:
        lines.append("brak 🎉")
    lines.append("")
    return "\n".join(lines)
