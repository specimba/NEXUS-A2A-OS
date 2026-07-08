#!/usr/bin/env python3
"""
Generate Synthetic Benign Security Queries Using Free Cutting-Edge Models

Uses the best available free models from NEXUS .env:
- DeepSeek V3 (671B, SOTA reasoning)
- Qwen2.5 72B (free via multiple providers)
- Grok-2 (xAI free tier)
- Llama 3.3 70B (free via multiple providers)
- Cerebras (ultra-fast inference)

Usage:
    python training/generate_synthetic_benign_free.py --num 1000 --provider deepseek
"""

import os
import sys
import json
import time
import random
import requests
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

# Enable UTF-8 output for Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# Load environment
from dotenv import load_dotenv
load_dotenv()

NEXUS_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(NEXUS_ROOT))


@dataclass
class ModelConfig:
    """Configuration for a free model provider."""
    name: str
    api_key: str
    base_url: str
    model_name: str
    max_tokens: int
    temperature: float
    description: str


# Available free cutting-edge models
FREE_MODELS = {
    "deepseek": ModelConfig(
        name="DeepSeek V3",
        api_key=os.getenv("OPENAI_API_KEY", ""),  # DeepSeek uses OpenAI format
        base_url="https://api.deepseek.com/v1",
        model_name="deepseek-chat",
        max_tokens=4000,
        temperature=0.8,
        description="DeepSeek V3 (671B MoE) - SOTA reasoning, free tier"
    ),
    "cerebras": ModelConfig(
        name="Cerebras Llama 3.3 70B",
        api_key=os.getenv("CEREBRAS_API_KEY", ""),
        base_url="https://api.cerebras.ai/v1",
        model_name="llama3.3-70b",
        max_tokens=4000,
        temperature=0.8,
        description="Cerebras - Ultra-fast inference, free"
    ),
    "sambanova": ModelConfig(
        name="SambaNova Llama 3.3 70B",
        api_key=os.getenv("SAMBANOVA_API_KEY", ""),
        base_url="https://api.sambanova.ai/v1",
        model_name="Meta-Llama-3.3-70B-Instruct",
        max_tokens=4000,
        temperature=0.8,
        description="SambaNova - Fast inference, free"
    ),
    "grok": ModelConfig(
        name="Grok-2 (xAI)",
        api_key=os.getenv("XAI_API_KEY", ""),
        base_url=os.getenv("XAI_BASE_URL", "https://api.x.ai/v1"),
        model_name="grok-2",
        max_tokens=4000,
        temperature=0.8,
        description="Grok-2 by xAI - Latest model, free tier"
    ),
    "nvidia": ModelConfig(
        name="NVIDIA Llama 3.1 70B",
        api_key=os.getenv("NVIDIA_API_KEY", ""),
        base_url="https://integrate.api.nvidia.com/v1",
        model_name="meta/llama-3.1-70b-instruct",
        max_tokens=4000,
        temperature=0.8,
        description="NVIDIA NIM - Free tier"
    ),
}

SYSTEM_PROMPT = """You are a cybersecurity education assistant helping generate realistic security research questions.

Generate benign, educational security questions that a security researcher, student, or developer would ask. Focus on:
- Vulnerability explanations (SQL injection, XSS, CSRF, buffer overflows, etc.)
- Defensive security techniques (input validation, encryption, authentication)
- Secure coding practices (OWASP guidelines, secure APIs, etc.)
- Penetration testing methodology (reconnaissance, scanning, exploitation in controlled environments)
- Network security (firewalls, IDS/IPS, VPNs, SSL/TLS)
- Cryptography fundamentals (hashing, encryption, key exchange)
- Security tools (Wireshark, Burp Suite, Metasploit in educational context)
- Incident response and forensics
- Compliance and security policies (GDPR, SOC2, ISO 27001)

All questions should be:
- Clearly educational and ethical
- Focused on defensive security and understanding vulnerabilities
- Appropriate for security training, certification prep, or academic study
- NOT focused on malicious exploitation or illegal activities

Generate ONE question per request. Make it specific, realistic, and valuable for security education."""

USER_PROMPT_TEMPLATE = """Generate a realistic cybersecurity education question. Focus on: {focus_area}

The question should be something a {persona} would genuinely ask while learning about security.

Output ONLY the question, nothing else."""

FOCUS_AREAS = [
    "SQL injection prevention and detection",
    "Cross-site scripting (XSS) attack vectors and mitigation",
    "CSRF protection mechanisms",
    "secure API design and authentication",
    "password hashing and storage best practices",
    "TLS/SSL configuration and certificate management",
    "container security and Docker best practices",
    "Kubernetes security hardening",
    "AWS/cloud security configurations",
    "zero-trust architecture principles",
    "OAuth 2.0 and OpenID Connect flows",
    "JWT security and validation",
    "buffer overflow exploitation and prevention",
    "race condition vulnerabilities",
    "timing attack mitigation",
    "side-channel attacks and defenses",
    "penetration testing methodology",
    "security code review techniques",
    "threat modeling approaches",
    "security incident response procedures",
]

PERSONAS = [
    "junior security engineer",
    "penetration tester in training",
    "security-focused developer",
    "cybersecurity student",
    "security certification candidate",
    "DevSecOps engineer",
    "security researcher",
    "security auditor",
]


def generate_query(config: ModelConfig, focus_area: str, persona: str) -> Optional[str]:
    """Generate a single benign security query using the model."""
    
    user_prompt = USER_PROMPT_TEMPLATE.format(focus_area=focus_area, persona=persona)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.api_key}"
    }
    
    payload = {
        "model": config.model_name,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
    }
    
    try:
        response = requests.post(
            f"{config.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        
        data = response.json()
        query = data["choices"][0]["message"]["content"].strip()
        
        # Clean up the query
        query = query.strip('"\'')
        
        return query
        
    except Exception as e:
        print(f"Error generating query: {e}")
        return None


def generate_batch(provider: str, num_queries: int, output_file: Path):
    """Generate a batch of synthetic benign queries."""
    
    if provider not in FREE_MODELS:
        print(f"Error: Unknown provider '{provider}'")
        print(f"Available providers: {', '.join(FREE_MODELS.keys())}")
        return
    
    config = FREE_MODELS[provider]
    
    if not config.api_key:
        print(f"Error: API key not found for {config.name}")
        print(f"Set the appropriate environment variable in .env")
        return
    
    print("="*80)
    print(f"SYNTHETIC BENIGN QUERY GENERATION")
    print("="*80)
    print(f"Provider: {config.description}")
    print(f"Model: {config.model_name}")
    print(f"Target: {num_queries} queries")
    print(f"Output: {output_file}")
    print()
    
    queries = []
    success_count = 0
    failure_count = 0
    
    start_time = time.time()
    
    for i in range(num_queries):
        focus_area = random.choice(FOCUS_AREAS)
        persona = random.choice(PERSONAS)
        
        print(f"[{i+1}/{num_queries}] Generating query (focus: {focus_area[:40]}...)...", end=" ")
        
        query = generate_query(config, focus_area, persona)
        
        if query:
            queries.append({
                "query": query,
                "focus_area": focus_area,
                "persona": persona,
                "provider": config.name,
                "model": config.model_name,
                "timestamp": time.time()
            })
            success_count += 1
            print("✓")
            
            # Save incrementally every 10 queries
            if success_count % 10 == 0:
                with open(output_file, 'w', encoding='utf-8') as f:
                    for q in queries:
                        f.write(json.dumps(q, ensure_ascii=False) + '\n')
                print(f"  [Saved checkpoint: {success_count} queries]")
        else:
            failure_count += 1
            print("✗")
        
        # Rate limiting (respectful to free tiers)
        time.sleep(1.0)
    
    # Final save
    with open(output_file, 'w', encoding='utf-8') as f:
        for q in queries:
            f.write(json.dumps(q, ensure_ascii=False) + '\n')
    
    elapsed_time = time.time() - start_time
    
    print()
    print("="*80)
    print("GENERATION COMPLETE")
    print("="*80)
    print(f"Success: {success_count}/{num_queries}")
    print(f"Failure: {failure_count}/{num_queries}")
    print(f"Time: {elapsed_time/60:.1f} minutes")
    print(f"Output: {output_file} ({output_file.stat().st_size / 1024:.1f} KB)")
    print()
    print(f"Cost: $0.00 (100% FREE)")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate synthetic benign security queries using free models")
    parser.add_argument("--num", type=int, default=100, help="Number of queries to generate")
    parser.add_argument("--provider", type=str, default="cerebras", 
                       choices=list(FREE_MODELS.keys()),
                       help="Model provider to use")
    parser.add_argument("--output", type=str, default="",
                       help="Output file path (default: datasets/synthetic_benign_free.jsonl)")
    
    args = parser.parse_args()
    
    # Set default output path
    if not args.output:
        output_file = NEXUS_ROOT / "datasets" / "synthetic_benign_free.jsonl"
    else:
        output_file = Path(args.output)
    
    # Create output directory
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Show available providers
    print()
    print("Available FREE cutting-edge models:")
    for key, config in FREE_MODELS.items():
        has_key = "✓" if config.api_key else "✗"
        print(f"  {has_key} {key:12} - {config.description}")
    print()
    
    # Generate queries
    generate_batch(args.provider, args.num, output_file)


if __name__ == "__main__":
    main()
