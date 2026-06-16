#!/usr/bin/env python3
"""
NEXUS OS — Vault Encryption Tool (AES-256-GCM)
Encrypts all files in vault/secrets/ with AES-256-GCM.
Requires NEXUS_VAULT_KEY environment variable (32-byte hex string).

Usage:
  python vault_encrypt.py --encrypt    # Encrypt all files in vault/secrets/
  python vault_encrypt.py --decrypt    # Decrypt all files
  python vault_encrypt.py --status     # Show vault status
  python vault_encrypt.py --generate-key  # Generate new master key

Based on: SecurityBASEandCRYPTknowledge.txt (Libgcrypt principles)
Algorithm: AES-256-GCM (authenticated encryption)
Key derivation: HKDF-SHA256 (HMAC-based Extract-and-Expand)
"""

import os
import sys
import json
import argparse
import base64
import hashlib
from pathlib import Path
from datetime import datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

# --- Configuration ---
VAULT_DIR = Path(__file__).parent.parent.parent / "vault" / "secrets"
VAULT_INDEX = VAULT_DIR / ".vault_index.json"
KEY_ENV_VAR = "NEXUS_VAULT_KEY"


def derive_key(master_key: bytes, salt: bytes) -> bytes:
    """Derive encryption key from master key using HKDF-SHA256."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"nexus-vault-v1"
    )
    return hkdf.derive(master_key)


def encrypt_file(filepath: Path, master_key: bytes) -> dict:
    """Encrypt a single file with AES-256-GCM."""
    plaintext = filepath.read_bytes()
    salt = os.urandom(16)
    key = derive_key(master_key, salt)
    nonce = os.urandom(12)
    
    aesgcm = AESGCM(key)
    associated_data = filepath.name.encode()  # Bind ciphertext to filename
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
    
    # Write encrypted file
    encrypted_path = filepath.with_suffix(filepath.suffix + ".enc")
    encrypted_path.write_bytes(salt + nonce + ciphertext)
    
    # Remove plaintext (if encrypted successfully)
    filepath.unlink()
    
    return {
        "original": filepath.name,
        "encrypted": encrypted_path.name,
        "salt": base64.b64encode(salt).decode(),
        "nonce": base64.b64encode(nonce).decode(),
        "size_original": len(plaintext),
        "size_encrypted": len(ciphertext) + 28,  # salt + nonce + overhead
        "timestamp": datetime.now().isoformat(),
    }


def decrypt_file(encrypted_path: Path, master_key: bytes, original_name: str) -> bool:
    """Decrypt a single file."""
    data = encrypted_path.read_bytes()
    salt = data[:16]
    nonce = data[16:28]
    ciphertext = data[28:]
    
    key = derive_key(master_key, salt)
    aesgcm = AESGCM(key)
    
    associated_data = original_name.encode()
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data)
        original_path = encrypted_path.with_suffix(encrypted_path.suffix.replace(".enc", ""))
        original_path.write_bytes(plaintext)
        encrypted_path.unlink()
        return True
    except Exception:
        return False


def get_master_key() -> bytes:
    """Get master key from environment."""
    key_hex = os.environ.get(KEY_ENV_VAR)
    if not key_hex:
        print(f"ERROR: Set {KEY_ENV_VAR} environment variable")
        print(f"Example: $env:{KEY_ENV_VAR} = (python -c \"import secrets; print(secrets.token_hex(32))\")")
        sys.exit(1)
    return bytes.fromhex(key_hex)


def generate_key():
    """Generate a new random master key."""
    key = os.urandom(32)
    print(f"Generated new master key (hex): {key.hex()}")
    print(f"\nAdd to your environment:")
    print(f"  $env:{KEY_ENV_VAR} = \"{key.hex()}\"")
    print(f"\nWARNING: Store this securely. If lost, encrypted files cannot be recovered.")


def encrypt_vault():
    """Encrypt all files in vault/secrets/."""
    master_key = get_master_key()
    
    if not VAULT_DIR.exists():
        print(f"ERROR: Vault directory not found: {VAULT_DIR}")
        sys.exit(1)
    
    index = {}
    for filepath in VAULT_DIR.iterdir():
        if filepath.is_file() and not filepath.suffix == ".enc" and not filepath.name.startswith("."):
            print(f"Encrypting: {filepath.name}...")
            entry = encrypt_file(filepath, master_key)
            index[entry["encrypted"]] = entry
    
    # Save index
    VAULT_INDEX.write_text(json.dumps(index, indent=2))
    print(f"\nVault encrypted: {len(index)} files")
    print(f"Index saved: {VAULT_INDEX}")


def decrypt_vault():
    """Decrypt all files in vault/secrets/."""
    master_key = get_master_key()
    
    if not VAULT_INDEX.exists():
        print(f"ERROR: Vault index not found: {VAULT_INDEX}")
        sys.exit(1)
    
    index = json.loads(VAULT_INDEX.read_text())
    decrypted = 0
    
    for encrypted_name, entry in index.items():
        encrypted_path = VAULT_DIR / encrypted_name
        if encrypted_path.exists():
            print(f"Decrypting: {entry['original']}...")
            if decrypt_file(encrypted_path, master_key, entry['original']):
                decrypted += 1
            else:
                print(f"  FAILED: {entry['original']}")
    
    print(f"\nVault decrypted: {decrypted}/{len(index)} files")


def vault_status():
    """Show vault status."""
    print(f"Vault directory: {VAULT_DIR}")
    print(f"Vault index: {VAULT_INDEX}")
    print(f"Master key set: {KEY_ENV_VAR in os.environ}")
    
    if VAULT_DIR.exists():
        files = list(VAULT_DIR.iterdir())
        encrypted = [f for f in files if f.suffix == ".enc"]
        plaintext = [f for f in files if not f.suffix == ".enc" and not f.name.startswith(".")]
        print(f"\nFiles: {len(files)} total")
        print(f"  Encrypted (.enc): {len(encrypted)}")
        print(f"  Plaintext: {len(plaintext)}")
        
        if plaintext:
            print(f"\nWARNING: {len(plaintext)} plaintext files detected:")
            for f in plaintext:
                print(f"  - {f.name}")


def main():
    parser = argparse.ArgumentParser(description="NEXUS Vault Encryption Tool")
    parser.add_argument("--encrypt", action="store_true", help="Encrypt all files in vault")
    parser.add_argument("--decrypt", action="store_true", help="Decrypt all files in vault")
    parser.add_argument("--status", action="store_true", help="Show vault status")
    parser.add_argument("--generate-key", action="store_true", help="Generate new master key")
    args = parser.parse_args()
    
    if args.generate_key:
        generate_key()
    elif args.encrypt:
        encrypt_vault()
    elif args.decrypt:
        decrypt_vault()
    elif args.status:
        vault_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
