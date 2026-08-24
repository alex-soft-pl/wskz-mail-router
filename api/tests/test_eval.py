"""Testy narzędzia ewaluacyjnego — czysta logika, bez modelu i bez HTTP."""

from collections import Counter

from app.agent import FEW_SHOT
from app.departments import Department
from app.eval.core import (
    CaseResult,
    check_few_shot_contamination,
    percentile,
    render_confusion_markdown,
    render_report_markdown,
    summarize,
    validate_dataset,
)
from app.eval.dataset import ALL_DEPARTMENTS, CASES, EXPECTED_COUNTS


def _result(id_, category, expected, got, time_s=1.0, run=1):
    return CaseResult(
        id=id_, category=category, message="msg", expected=expected, got=got, time_s=time_s, run=run
    )


# --- dataset ---


def test_dataset_is_valid():
    assert validate_dataset() == []


def test_dataset_counts():
    assert len(CASES) == sum(EXPECTED_COUNTS.values()) == 44


def test_dataset_expected_within_enum():
    assert {c["expected"] for c in CASES} <= {d.value for d in Department}


def test_dataset_not_contaminated_by_few_shot_prompt_examples():
    few_shot_messages = [
        part.content for msg in FEW_SHOT for part in msg.parts if part.part_kind == "user-prompt"
    ]
    assert few_shot_messages, "few-shot agenta powinien zawierać przykłady user"
    assert check_few_shot_contamination(CASES, few_shot_messages) == []


def test_validate_dataset_detects_problems():
    bad = [
        {"id": "x1", "category": "basic", "message": "a", "expected": "marketing"},
        {"id": "x1", "category": "basic", "message": " ", "expected": "it"},
    ]
    problems = validate_dataset(bad)
    assert any("zduplikowane" in p for p in problems)
    assert any("spoza enum" in p for p in problems)
    assert any("pusta" in p for p in problems)
    assert any("kategoria" in p for p in problems)


# --- agregacja / macierz ---


def test_summarize_accuracy_and_categories():
    results = [
        _result("a", "basic", "it", "it"),
        _result("b", "basic", "kadry", "it"),
        _result("c", "edge", "other", "other"),
        _result("d", "edge", "other", "kadry"),
    ]
    s = summarize(results)
    assert (s.total, s.correct) == (4, 2)
    assert s.accuracy == 0.5
    assert s.per_category == {"basic": (1, 2), "edge": (1, 2)}


def test_summarize_confusion_matrix():
    results = [
        _result("a", "basic", "it", "it"),
        _result("b", "basic", "it", "help-desk"),
        _result("c", "basic", "kadry", "human-resources"),
    ]
    s = summarize(results)
    assert s.confusion["it"] == Counter({"it": 1, "help-desk": 1})
    assert s.confusion["kadry"] == Counter({"human-resources": 1})


def test_summarize_detects_instability_between_runs():
    results = [
        _result("a", "basic", "it", "it", run=1),
        _result("a", "basic", "it", "help-desk", run=2),
        _result("b", "basic", "kadry", "kadry", run=1),
        _result("b", "basic", "kadry", "kadry", run=2),
    ]
    assert summarize(results).unstable_ids == ["a"]


def test_percentile():
    values = [float(v) for v in range(0, 101)]  # 101 próbek: 0..100
    assert percentile(values, 50) == 50.0
    assert percentile(values, 95) == 95.0
    assert percentile([3.0], 95) == 3.0


# --- render ---


def test_render_confusion_has_all_departments():
    s = summarize([_result("a", "basic", "it", "it")])
    md = render_confusion_markdown(s.confusion)
    for dept in ALL_DEPARTMENTS:
        assert dept in md
    assert "**1**" in md  # trafienie na diagonali wyróżnione


def test_render_report_lists_failures_and_threshold():
    results = [
        _result("a", "basic", "it", "it"),
        _result("b", "basic", "kadry", "it"),
    ]
    meta = {"timestamp": "2026-08-24 12:00", "target": "http://x", "runs": 1, "threshold": 0.85}
    md = render_report_markdown(summarize(results), results, meta)
    assert "1/2" in md and "50.00%" in md
    assert "❌ poniżej progu" in md
    assert "| b | basic |" in md  # tabela błędów
