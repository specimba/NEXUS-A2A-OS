import httpx

try:
    res = httpx.get("http://127.0.0.1:11435/api/tags")
    res.raise_for_status()
    models = res.json().get("models", [])
    print(f"Ollama has {len(models)} models:")
    for m in models:
        print(f"  {m.get('name')} (size: {m.get('size') / (1024**3):.2f} GB)")
except Exception as e:
    print(f"Failed to query Ollama: {e}")
