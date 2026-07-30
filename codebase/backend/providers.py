"""Small, server-side model fallback chain for official-source excerpts."""

import json
import os
from urllib.request import Request, urlopen


_DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "gemini": "gemini-3.5-flash",
    "openrouter": "~google/gemini-flash-latest",
    "cerebras": "gpt-oss-120b",
}
_KEYS = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
}


def _prompt(question: str, source_text: str) -> str:
    return (
        "Answer the student only from SOURCE. Return JSON exactly as "
        '{"excerpt":"..."}. excerpt must be an exact, smallest relevant substring of SOURCE; '
        "do not add, translate, or infer anything.\n\n"
        f"QUESTION:\n{question}\n\nSOURCE:\n{source_text}"
    )


def _json_content(url: str, headers: dict[str, str], body: dict) -> dict:
    request = Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _chat_completion(url: str, key: str, model: str, prompt: str, *, cerebras: bool = False) -> str:
    body = {
        "model": model,
        "messages": [{"role": "system", "content": "Return valid JSON only."}, {"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }
    body["max_completion_tokens" if cerebras else "max_tokens"] = 250
    data = _json_content(url, {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, body)
    return data["choices"][0]["message"]["content"]


def _openai_response(key: str, model: str, prompt: str) -> str:
    data = _json_content(
        "https://api.openai.com/v1/responses",
        {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        {
            "model": model,
            "input": prompt,
            "store": False,
            "max_output_tokens": 250,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "source_excerpt",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {"excerpt": {"type": "string"}},
                        "required": ["excerpt"],
                        "additionalProperties": False,
                    },
                }
            },
        },
    )
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                return content["text"]
    raise ValueError("OpenAI response contained no text output")


def _ask_provider(name: str, question: str, source_text: str) -> str:
    key = os.environ[_KEYS[name]]
    model = os.environ.get(f"{name.upper()}_MODEL", _DEFAULT_MODELS[name])
    prompt = _prompt(question, source_text)
    if name == "openai":
        return _openai_response(key, model, prompt)
    if name == "gemini":
        from google import genai

        response = genai.Client(api_key=key).interactions.create(
            model=model,
            input=prompt,
            store=False,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": {
                    "type": "object",
                    "properties": {"excerpt": {"type": "string"}},
                    "required": ["excerpt"],
                    "additionalProperties": False,
                },
            },
        )
        return response.output_text
    if name == "openrouter":
        return _chat_completion("https://openrouter.ai/api/v1/chat/completions", key, model, prompt)
    return _chat_completion("https://api.cerebras.ai/v1/chat/completions", key, model, prompt, cerebras=True)


def model_excerpt(question: str, source_text: str, call=_ask_provider) -> tuple[str | None, str | None]:
    configured = [
        name for name in os.environ.get("AI_PROVIDER_ORDER", "openai,gemini,openrouter,cerebras").split(",")
        if name in _KEYS and os.environ.get(_KEYS[name])
    ]
    for name in configured:
        try:
            excerpt = json.loads(call(name, question, source_text)).get("excerpt")
            if isinstance(excerpt, str) and excerpt and excerpt in source_text:
                return excerpt, name
        except Exception:
            continue
    return None, None
