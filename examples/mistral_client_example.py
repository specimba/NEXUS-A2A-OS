"""
Mistral API Client Example for Nexus OS

Demonstrates usage of Mistral Studio API keys and Codestral endpoints
configured in .env

Requires: pip install mistralai
"""
import os
from mistralai.client import Mistral

# Initialize client with Mistral API key from environment
client = Mistral(api_key=os.environ.get("MISTRAL_API_KEY"))

# Example 1: Start a conversation with a Mistral agent
# Agent ID from Mistral Studio
def start_agent_conversation():
    inputs = [
        {"role": "user", "content": "Hello!"}
    ]
    
    response = client.beta.conversations.start(
        agent_id="ag_019e381ebeac77b4b6999be0e6643218",
        agent_version=1,
        inputs=inputs,
    )
    
    print("Agent conversation response:")
    print(response)
    return response


# Example 2: Use Codestral completion endpoint
# Endpoint configured in .env as CODESTRAL_COMPLETION_ENDPOINT
# Requires CODESTRAK_KEY or CODESTRAL_API_KEY
import requests
import json

def codestral_completion(prompt: str, max_tokens: int = 100):
    endpoint = os.environ.get("CODESTRAL_COMPLETION_ENDPOINT", 
                             "https://codestral.mistral.ai/v1/fim/completions")
    api_key = os.environ.get("CODESTRAK_KEY") or os.environ.get("CODESTRAL_API_KEY")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "prompt": prompt,
        "max_tokens": max_tokens,
    }
    
    response = requests.post(endpoint, headers=headers, json=payload)
    return response.json()


# Example 3: Use Codestral chat completion endpoint
def codestral_chat(messages: list, temperature: float = 0.7):
    endpoint = os.environ.get("CODESTRAL_CHAT_ENDPOINT",
                             "https://codestral.mistral.ai/v1/chat/completions")
    api_key = os.environ.get("CODESTRAK_KEY") or os.environ.get("CODESTRAL_API_KEY")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "messages": messages,
        "temperature": temperature,
    }
    
    response = requests.post(endpoint, headers=headers, json=payload)
    return response.json()


if __name__ == "__main__":
    print("Mistral Client Example for Nexus OS")
    print("=" * 40)
    
    # Check required environment variables
    required = ["MISTRAL_API_KEY", "CODESTRAK_KEY", "CODESTRAL_COMPLETION_ENDPOINT", 
                "CODESTRAL_CHAT_ENDPOINT"]
    missing = [var for var in required if not os.environ.get(var)]
    
    if missing:
        print(f"Warning: Missing environment variables: {missing}")
        print("Set them in .env file or export before running.")
    else:
        print("All required environment variables are set.")
    
    # Example usage (uncomment to run)
    # start_agent_conversation()
    # result = codestral_completion("def hello():")
    # print(result)
