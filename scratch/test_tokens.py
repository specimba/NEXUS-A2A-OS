import os
from gradio_client import Client

tokens = [
    "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",
    "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"
]

for i, t in enumerate(tokens):
    print(f"Testing Token {i+1}: {t[:10]}...")
    try:
        client = Client("huggingface-projects/gemma-4-12b-it", token=t)
        print("  Connected successfully!")
        
        # Try a tiny inference
        print("  Running test inference...")
        res = client.predict(
            text="Hello, quick response please.",
            files=None,
            history=None,
            thinking=False,
            max_new_tokens=200,
            image_token_budget=100,
            system_prompt="Be concise.",
            temperature=0.7,
            top_p=0.95,
            top_k=64,
            repetition_penalty=1.0,
            api_name="/chat"
        )
        print(f"  Result: {res}")
    except Exception as e:
        print(f"  Error: {e}")
