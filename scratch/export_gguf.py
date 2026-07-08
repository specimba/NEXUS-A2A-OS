import os
import torch
from unsloth import FastLanguageModel

# CANARY: b6c2d4bdb4763ce10ecad7842b660e01
MODEL_NAME = "unsloth/Qwen2.5-1.5B-Instruct-bnb-4bit"
LORA_PATH = r"c:\Users\speci.000\Documents\NEXUS\models\qwen2.5-1.5b-guard-lora"
GGUF_PATH = r"c:\Users\speci.000\Documents\NEXUS\models\qwen2.5-1.5b-guard.Q4_K_M.gguf"

def main():
    print("Loading base model and LoRA adapter...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=1024,
        load_in_4bit=True,
        dtype=None,
        device_map="auto",
    )
    
    print(f"Loading LoRA adapter from {LORA_PATH}...")
    model.load_adapter(LORA_PATH)
    
    print("Switching model to inference mode...")
    model = FastLanguageModel.for_inference(model)
    
    print(f"Exporting model to GGUF in {os.path.dirname(GGUF_PATH)}...")
    model.save_pretrained_gguf(
        os.path.dirname(GGUF_PATH),
        tokenizer,
        quantization_method="q4_k_m",
    )
    print("GGUF Export complete!")

if __name__ == "__main__":
    main()
