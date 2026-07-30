import providers


def test_uses_openai_first_when_its_key_is_configured(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER_ORDER", "openai,gemini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    calls = []

    def fake_provider(name, question, source_text):
        calls.append(name)
        return '{"excerpt": "Hạn nộp spec là 23:59 ngày 1."}'

    excerpt, provider = providers.model_excerpt(
        "Hạn nộp spec là khi nào?",
        "Hạn nộp spec là 23:59 ngày 1.",
        call=fake_provider,
    )

    assert (excerpt, provider) == ("Hạn nộp spec là 23:59 ngày 1.", "openai")
    assert calls == ["openai"]


def test_openai_adapter_requests_a_structured_nonstored_response(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    seen = {}

    def fake_request(url, headers, body):
        seen.update(url=url, headers=headers, body=body)
        return {"output": [{"content": [{"type": "output_text", "text": '{"excerpt":"official"}'}]}]}

    monkeypatch.setattr(providers, "_json_content", fake_request)

    assert providers._ask_provider("openai", "When?", "official") == '{"excerpt":"official"}'
    assert seen["url"] == "https://api.openai.com/v1/responses"
    assert seen["body"]["store"] is False
    assert seen["body"]["text"]["format"]["type"] == "json_schema"


def test_uses_the_next_configured_provider_and_accepts_only_a_source_excerpt(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER_ORDER", "gemini,openrouter,cerebras")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-router")
    monkeypatch.setenv("CEREBRAS_API_KEY", "test-cerebras")
    calls = []

    def fake_provider(name, question, source_text):
        calls.append(name)
        if name == "gemini":
            raise RuntimeError("unavailable")
        if name == "openrouter":
            return '{"excerpt": "Hạn nộp spec là 23:59 ngày 1."}'
        raise AssertionError("the third provider should not be called")

    excerpt, provider = providers.model_excerpt(
        "Hạn nộp spec là khi nào?",
        "Hạn nộp spec là 23:59 ngày 1.",
        call=fake_provider,
    )

    assert (excerpt, provider) == ("Hạn nộp spec là 23:59 ngày 1.", "openrouter")
    assert calls == ["gemini", "openrouter"]


def test_rejects_model_text_that_is_not_in_the_official_source(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER_ORDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")

    excerpt, provider = providers.model_excerpt(
        "Hạn nộp spec là khi nào?",
        "Hạn nộp spec là 23:59 ngày 1.",
        call=lambda *_: '{"excerpt": "Hạn nộp spec là ngày mai."}',
    )

    assert (excerpt, provider) == (None, None)
