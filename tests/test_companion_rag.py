import json

from companion_rag import Source, answer, load_sources, log_trace


def test_answers_from_the_best_matching_official_source():
    result = answer(
        "Hạn nộp spec là khi nào?",
        [Source("schedule.yaml", "Hạn nộp spec là 23:59 ngày 1.")],
    )

    assert result.action == "answer"
    assert result.citations == ["schedule.yaml"]
    assert "23:59" in result.answer


def test_refuses_when_no_official_source_supports_the_question():
    result = answer(
        "Có được gia hạn deadline không?",
        [Source("schedule.yaml", "Hạn nộp spec là 23:59 ngày 1.")],
    )

    assert result.action == "refuse"
    assert result.citations == []


def test_clarifies_an_ambiguous_session_question():
    result = answer("Buổi lab tuần này học gì?", [Source("schedule.yaml", "Lab-3 học RAG.")])

    assert result.action == "clarify"
    assert result.citations == []


def test_loads_curated_yaml_as_a_citable_source(tmp_path):
    (tmp_path / "schedule.yaml").write_text("sessions:\n  - code: Lab-3\n    deadline: 23:59 ngày 1\n", encoding="utf-8")

    sources = load_sources(tmp_path)

    assert sources[0].citation == "schedule.yaml"
    assert "Lab-3" in sources[0].text


def test_writes_a_json_trace_for_each_decision(tmp_path):
    result = answer("Hạn nộp spec?", [Source("schedule.yaml", "Hạn nộp spec là 23:59 ngày 1.")])

    log_trace(tmp_path, "Hạn nộp spec?", result)

    trace = json.loads(next(tmp_path.iterdir()).read_text(encoding="utf-8"))
    assert trace["action"] == "answer"
    assert trace["citations"] == ["schedule.yaml"]
