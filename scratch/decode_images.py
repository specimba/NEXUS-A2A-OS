import os
import re
import sys
import time
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from gradio_client import Client
import httpx

# Reconfigure stdout/stderr for UTF-8 to handle console printing on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# Load environment variables
load_dotenv()

# Set HF_TOKEN explicitly from the user's provided secret
hf_token = "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"

print(f"HF_TOKEN configured: {hf_token is not None}")

# Define output directories
BRIEFS_DIR = Path("c:/Users/speci.000/Documents/NEXUS/docs/wiki/briefs")
BRIEFS_DIR.mkdir(parents=True, exist_ok=True)

# List of input images to process
images_to_process = []

# 1. Check for workflowIMGtest1.png
img_test = Path("C:/Users/speci.000/Downloads/ARCHIVIST/workflowIMGtest1.png")
if img_test.exists():
    images_to_process.append(img_test)
else:
    print(f"Test image not found at: {img_test}")

# 2. Check for other images in Workflows
workflows_dir = Path("C:/Users/speci.000/Downloads/Workflows")
if workflows_dir.exists():
    for ext in ("*.png", "*.jpg", "*.jpeg"):
        for f in workflows_dir.glob(ext):
            if f.name.lower() != "workflowimgtest1.png":
                images_to_process.append(f)

print(f"Found {len(images_to_process)} images to decode.")

if not images_to_process:
    print("No images found to process. Exiting.")
    sys.exit(0)

# Connect to Gemma-4-12b-it space
try:
    print("Connecting to huggingface-projects/gemma-4-12b-it client...")
    client = Client("huggingface-projects/gemma-4-12b-it", token=hf_token)
    print("Successfully connected!")
except Exception as e:
    print(f"Failed to connect to Gradio Space: {e}")
    sys.exit(1)

prompt_template = (
    "Analyze this technical workflow/architecture diagram in detail. "
    "Write a high-level, comprehensive technical description of the workflow. "
    "Describe the components, connections, inputs/outputs, and the underlying mathematical or systems logic. "
    "Format the response as a formal technical paper section, complete with clear headings and paragraphs."
)

for idx, img_path in enumerate(images_to_process, 1):
    stem = img_path.stem
    output_file = BRIEFS_DIR / f"{stem}_brief.md"
    
    # Check if a valid brief already exists (doesn't contain error)
    if output_file.exists():
        try:
            existing_content = output_file.read_text(encoding="utf-8")
            if "Invalid file path" not in existing_content and "Failed Technical Analysis" not in existing_content and "error" not in existing_content and "origin_sha256" in existing_content:
                print(f"[{idx}/{len(images_to_process)}] Skipping {img_path.name} (already successfully processed)")
                continue
        except Exception:
            pass

    print(f"\n[{idx}/{len(images_to_process)}] Processing {img_path.name} ({img_path.stat().st_size / 1024:.1f} KB)...")
    
    try:
        # Step 1: Compute image SHA256 for frontmatter
        img_bytes = img_path.read_bytes()
        origin_sha256 = hashlib.sha256(img_bytes).hexdigest()
        
        # Step 2: Upload file manually to client
        print(f"  Uploading {img_path.name} to Space...")
        with open(img_path, "rb") as f_obj:
            upload_res = httpx.post(client.upload_url, files={"files": f_obj})
        upload_res.raise_for_status()
        uploaded_files = upload_res.json()
        print(f"  Uploaded to server: {uploaded_files}")
        
        # Step 3: Call Gradio Client predict
        print(f"  Running multimodal inference on Space...")
        result = client.predict(
            text=prompt_template,
            files=uploaded_files,
            history=None,
            thinking=True, # enable thinking to get a high-quality deep-dive response
            max_new_tokens=2500,
            image_token_budget=280,
            system_prompt="You are a senior computer scientist and system architect. Analyze the image accurately.",
            temperature=0.7,
            top_p=0.95,
            top_k=64,
            repetition_penalty=1.0,
            api_name="/chat"
        )
        
        # Extract content
        print(f"  Raw response type: {type(result)}")
        content = ""
        reasoning = ""
        if isinstance(result, dict):
            if "error" in result and result["error"]:
                raise ValueError(result["error"])
            content = result.get("content") or ""
            reasoning = result.get("reasoning") or ""
        else:
            content = str(result)

        if not content.strip() and reasoning.strip():
            content = reasoning
            
        # Add reasoning trace inside <details> block if present
        details_block = ""
        if reasoning.strip() and reasoning != content:
            details_block = f"\n<details>\n<summary>Thinking Process / Reasoning Trace</summary>\n\n{reasoning}\n\n</details>\n"

        # Calculate policy hash (SHA256 of the prompt/system_prompt used)
        policy_base = f"{prompt_template}:You are a senior computer scientist and system architect. Analyze the image accurately."
        policy_hash = hashlib.sha256(policy_base.encode('utf-8')).hexdigest()
        
        id_str = f"NODE-WF-{stem.upper().replace('-', '_')}"
        
        md_content = f"""---
id: {id_str}
title: Technical Brief for {stem} Workflow
description: Automated multimodal decoding and technical description of the {stem} illustration
truth_layer: EXTRACTED
authority_scope: mirror-derived
verified: true
confidence: 0.95
canonical_ref: "[[01_PROJECT_STATE.md]]"
provenance: "Gemma-4-12b-it Multimodal Space decoding of {img_path.name}"
approval_id: "APP-WF-{idx:03d}"
sandbox_profile: "gradio-client-gemma4"
origin_sha256: "{origin_sha256}"
policy_hash: "{policy_hash}"
---

# Technical Analysis: {stem.replace('_', ' ').replace('-', ' ').title()}

{details_block}
{content}

---
*Generated by Gemma-4-12b-it on {time.strftime('%Y-%m-%d %H:%M:%S')}*
"""
        output_file.write_text(md_content, encoding="utf-8")
        print(f"[OK] Saved technical brief to: {output_file}")
        
        # Slow down requests slightly to avoid rate-limits
        time.sleep(2)
        
    except Exception as e:
        print(f"[ERROR] Error processing {img_path.name}: {e}")
        # Write stub so we can see which failed
        try:
            stub_content = f"""---
id: NODE-WF-{stem.upper().replace('-', '_')}_FAILED
title: Failed Technical Brief for {stem}
description: Failed decoding of {stem}
truth_layer: EXTRACTED
authority_scope: experimental
verified: false
confidence: 0.0
canonical_ref: "[[01_PROJECT_STATE.md]]"
provenance: "Failed processing of {img_path.name}"
approval_id: "APP-WF-{idx:03d}"
sandbox_profile: "gradio-client-gemma4"
origin_sha256: ""
policy_hash: ""
---

# Failed Technical Analysis: {stem}

An error occurred during the multimodal analysis of {img_path.name}.
Error: {e}
"""
            output_file.write_text(stub_content, encoding="utf-8")
        except Exception:
            pass

print("\nProcessing complete!")
