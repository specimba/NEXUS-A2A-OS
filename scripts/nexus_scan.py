import argparse
import hashlib
import json
import os
import re

# Simple patterns for demonstration/dry-run purposes
PATTERNS = {
    "api_key": re.compile(r"(?i)(api[_-]?key|secret|token|password)[\s:=]+(['\"]?)[A-Za-z0-9_-]{16,}(['\"]?)"),
    "private_key": re.compile(r"-----BEGIN (RSA|OPENSSH|DSA|EC|PGP) PRIVATE KEY-----"),
}

def scan_file(filepath):
    findings = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            for finding_type, pattern in PATTERNS.items():
                for match in pattern.finditer(content):
                    matched_string = match.group(0)
                    
                    # Redact the sample
                    if finding_type == "api_key":
                        # Attempt to redact the value part
                        # Find the first '=' or ':' and redact after it
                        sep_idx = max(matched_string.find('='), matched_string.find(':'))
                        if sep_idx != -1:
                            key_part = matched_string[:sep_idx+1]
                            val_part = matched_string[sep_idx+1:].strip()
                            if len(val_part) > 8:
                                redacted_val = val_part[:4] + "*" * (len(val_part) - 8) + val_part[-4:]
                            else:
                                redacted_val = "*" * len(val_part)
                            redacted_sample = f"{key_part} {redacted_val}"
                        else:
                            redacted_sample = matched_string[:4] + "*" * (len(matched_string) - 8) + matched_string[-4:]
                    else:
                        redacted_sample = "-----BEGIN [REDACTED] PRIVATE KEY-----"
                    
                    findings.append({
                        "file": filepath,
                        "finding_type": finding_type,
                        "redacted_sample": redacted_sample,
                        "recommendation": f"Verify if {finding_type} is a real secret. If false positive, add to allowlist."
                    })
    except Exception as e:
        print(f"Error scanning {filepath}: {e}")
    return findings

def get_file_sha256(filepath):
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception:
        return None

def main():
    parser = argparse.ArgumentParser(description="Nexus Dry-Run Scanner")
    parser.add_argument("--target", required=True, help="Explicit target directory or file to scan (Must be supplied)")
    parser.add_argument("--output", required=True, help="Path to write the JSON report")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.target):
        print(f"Target path does not exist: {args.target}")
        return

    all_findings = []
    
    if os.path.isfile(args.target):
        files_to_scan = [args.target]
    else:
        files_to_scan = []
        for root, _, files in os.walk(args.target):
            # Skip only actual hidden dirs (not paths containing "." like speci.000)
            # Check for .git, .kiro, .kilo, etc. as actual directory names
            basename = os.path.basename(root)
            if basename.startswith('.'):
                continue  # Skip .git, .kilo, .kiro, .pi, etc.
            for file in files:
                if not file.startswith('.'):
                    files_to_scan.append(os.path.join(root, file))

    for filepath in files_to_scan:
        file_findings = scan_file(filepath)
        if file_findings:
            file_hash = get_file_sha256(filepath)
            for finding in file_findings:
                finding["sha256"] = file_hash
            all_findings.extend(file_findings)

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(all_findings, f, indent=2)
        
    print(f"Scan complete. Found {len(all_findings)} potential issues. Report written to {args.output}")

if __name__ == "__main__":
    main()
