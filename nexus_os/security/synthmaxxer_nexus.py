"""
SynthMaxxer NEXUS Integration - Generate Benign Security Research Queries

Uses SynthMaxxer to generate synthetic benign security research conversations
for training guard models to reduce false positives.

Supports multiple LLM APIs:
- Anthropic Claude
- OpenAI
- DeepSeek
- OpenRouter
- Grok (xAI)
- Gemini (Google)
"""

import json
import os
import sys
import threading
import queue
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

# Add vendor path
VENDOR_PATH = str(Path(__file__).parent.parent.parent / "vendor" / "ShareGPT-Formaxxing")
if VENDOR_PATH not in sys.path:
    sys.path.insert(0, VENDOR_PATH)

from App.SynthMaxxer.worker import worker


@dataclass
class NexusSynthConfig:
    """NEXUS-specific configuration for SynthMaxxer."""
    
    # API settings
    api_type: str = "OpenAI Official"  # Anthropic Claude, OpenAI Official, DeepSeek, etc.
    api_key: str = ""
    endpoint: str = "https://api.openai.com/v1/chat/completions"
    model: str = "gpt-4"
    
    # Output
    output_dir: str = ""
    
    # Generation settings
    system_message: str = ""
    user_first_message: str = ""
    assistant_first_message: str = ""
    
    # Conversation settings
    min_turns: int = 3
    stop_percentage: float = 0.25
    is_instruct: bool = False
    
    # Tags (for ShareGPT format)
    user_start_tag: str = "<|user|>"
    user_end_tag: str = "</|user|>"
    assistant_start_tag: str = "<|assistant|>"
    assistant_end_tag: str = "</|assistant|>"
    
    # Delay between generations
    min_delay: float = 1.0
    max_delay: float = 3.0
    
    # Refusal detection
    refusal_phrases: List[str] = None
    force_retry_phrases: List[str] = None


class NexusSynthMaxxer:
    """
    NEXUS wrapper for SynthMaxxer.
    
    Generates synthetic benign security research conversations using LLM APIs.
    """
    
    def __init__(self, config: Optional[NexusSynthConfig] = None):
        """
        Initialize NexusSynthMaxxer.
        
        Args:
            config: Configuration for generation
        """
        self.config = config or NexusSynthConfig()
        self.stop_flag = threading.Event()
        self.message_queue = queue.Queue()
        self.worker_thread = None
        
        # Default refusal phrases
        if self.config.refusal_phrases is None:
            self.config.refusal_phrases = [
                "I cannot",
                "I can't",
                "I won't",
                "I'm unable",
                "I am unable",
                "I apologize, but",
                "I'm sorry, but",
                "I cannot assist",
                "I can't help",
                "I'm not able",
                "against my guidelines",
                "violates my guidelines",
            ]
        
        if self.config.force_retry_phrases is None:
            self.config.force_retry_phrases = []
    
    def log(self, message: str):
        """Log a message."""
        print(f"[NexusSynthMaxxer] {message}")
    
    def generate(self, num_conversations: int = 10) -> bool:
        """
        Generate synthetic conversations.
        
        Args:
            num_conversations: Number of conversations to generate
            
        Returns:
            True if successful, False otherwise
        """
        self.log(f"Starting generation of {num_conversations} conversations...")
        
        # Validate config
        if not self.config.api_key:
            self.log("Error: API key not provided")
            return False
        
        if not self.config.output_dir:
            self.log("Error: Output directory not provided")
            return False
        
        # Create output directory
        os.makedirs(self.config.output_dir, exist_ok=True)
        
        # Start worker thread
        self.stop_flag.clear()
        self.worker_thread = threading.Thread(
            target=worker,
            args=(
                self.config.api_key,
                self.config.endpoint,
                self.config.model,
                self.config.output_dir,
                self.config.system_message,
                self.config.user_first_message,
                self.config.assistant_first_message,
                self.config.user_start_tag,
                self.config.user_end_tag,
                self.config.assistant_start_tag,
                self.config.assistant_end_tag,
                self.config.is_instruct,
                self.config.min_delay,
                self.config.max_delay,
                self.config.stop_percentage,
                self.config.min_turns,
                self.config.refusal_phrases,
                self.config.force_retry_phrases,
                self.config.api_type,
                self.stop_flag,
                self.message_queue,
            )
        )
        self.worker_thread.start()
        
        # Monitor messages
        conversations_generated = 0
        while conversations_generated < num_conversations:
            try:
                msg_type, msg_data = self.message_queue.get(timeout=1.0)
                
                if msg_type == "log":
                    self.log(msg_data)
                elif msg_type == "conversation_complete":
                    conversations_generated += 1
                    self.log(f"Progress: {conversations_generated}/{num_conversations}")
                elif msg_type == "error":
                    self.log(f"Error: {msg_data}")
                    return False
                
            except queue.Empty:
                # Check if worker is still alive
                if not self.worker_thread.is_alive():
                    self.log("Worker thread stopped unexpectedly")
                    return False
        
        # Stop worker
        self.stop_flag.set()
        self.worker_thread.join(timeout=5.0)
        
        self.log("Generation complete!")
        return True
    
    def stop(self):
        """Stop generation."""
        self.log("Stopping generation...")
        self.stop_flag.set()
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)


def create_benign_security_research_config() -> NexusSynthConfig:
    """
    Create default configuration for generating benign security research queries.
    
    Returns:
        Default configuration for benign queries
    """
    nexus_root = Path(__file__).parent.parent.parent
    output_dir = nexus_root / "datasets" / "synthetic_benign"
    
    system_message = """You are a helpful AI assistant specializing in cybersecurity education.
You provide clear, educational explanations about security concepts, vulnerabilities, and defensive techniques.
You answer questions about security research, penetration testing, secure coding, and defensive security.
You maintain a professional, educational tone and focus on defensive security applications."""
    
    user_first_message = """Generate a conversation where a security researcher or student asks educational questions about cybersecurity topics.
Focus on:
- Security vulnerability explanations (SQL injection, XSS, CSRF, etc.)
- Defensive security techniques
- Secure coding practices
- Penetration testing methodology
- Network security concepts
- Cryptography fundamentals
- Security tool usage (Wireshark, Burp Suite, etc.)
- Incident response procedures

The questions should be clearly educational and focus on defensive security.
Generate realistic, professional questions that a security researcher or student would ask."""
    
    assistant_first_message = """I'll generate a realistic cybersecurity education conversation between a student/researcher and an AI assistant."""
    
    return NexusSynthConfig(
        api_type="OpenAI Official",
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        endpoint="https://api.openai.com/v1/chat/completions",
        model="gpt-4",
        output_dir=str(output_dir),
        system_message=system_message,
        user_first_message=user_first_message,
        assistant_first_message=assistant_first_message,
        min_turns=3,
        stop_percentage=0.25,
        is_instruct=False,
        min_delay=1.0,
        max_delay=3.0,
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate synthetic benign security research conversations")
    parser.add_argument("--num", type=int, default=100, help="Number of conversations to generate")
    parser.add_argument("--api-key", type=str, default="", help="API key (or set OPENAI_API_KEY env var)")
    parser.add_argument("--model", type=str, default="gpt-4", help="Model to use")
    parser.add_argument("--output-dir", type=str, default="", help="Output directory")
    
    args = parser.parse_args()
    
    # Create config
    config = create_benign_security_research_config()
    
    if args.api_key:
        config.api_key = args.api_key
    
    if args.model:
        config.model = args.model
    
    if args.output_dir:
        config.output_dir = args.output_dir
    
    # Validate API key
    if not config.api_key:
        print("Error: API key required. Set OPENAI_API_KEY environment variable or use --api-key")
        sys.exit(1)
    
    # Generate
    synth = NexusSynthMaxxer(config)
    success = synth.generate(num_conversations=args.num)
    
    if success:
        print(f"Successfully generated {args.num} conversations!")
        print(f"Output: {config.output_dir}")
    else:
        print("Generation failed!")
        sys.exit(1)
