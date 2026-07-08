import urllib.request
import json
import time

# CANARY: 291388066e1b5f41d35faa9949a94929
OLLAMA_API = "http://127.0.0.1:11435/api/generate"
payload = json.dumps({
    "model": "special-virus",
    "prompt": "Hello",
    "stream": False,
    "options": {"num_predict": 10}
}).encode()

t0 = time.time()
try:
    req = urllib.request.Request(OLLAMA_API, data=payload, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read())
    print(f"Ollama responds: {data.get('response')}")
    print(f"Time taken: {time.time() - t0:.2f}s")
except Exception as e:
    print(f"Error calling Ollama: {e}")
