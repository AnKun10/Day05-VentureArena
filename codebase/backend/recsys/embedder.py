def embed_texts(texts, cfg, client=None):
    if client is None:
        from openai import OpenAI
        client = OpenAI(api_key=cfg.openai_api_key)
    resp = client.embeddings.create(model=cfg.embed_model, input=texts)
    return [d.embedding for d in resp.data]


def news_text(row: dict) -> str:
    return f"{row['title']}\n{row.get('summary') or ''}\nTags: {', '.join(row.get('tags') or [])}"
