import urllib.request
import json
import os

"""
CANARY_TOKEN: e54027d70492cb0b98fbe0f99c6593f2
"""
endpoints = [
    "http://127.0.0.1:11435/api/tags",
    "http://172.26.240.1:11435/api/tags"
]

for url in endpoints:
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"Success hitting {url}:")
            models = [m['name'] for m in data.get('models', [])]
            print(f"  Models: {models}")
    except Exception as e:
        print(f"Error hitting {url}: {e}")
