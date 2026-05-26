#!/usr/bin/env python3
"""redaction_filter.py — strip secrets from logs / status output before sharing.

Usage:
  cat raw_output.txt | python3 redaction_filter.py > redacted.txt
  python3 redaction_filter.py --selftest   # run the built-in test cases

Design notes:
  - Patterns are deliberately broad. False positives are acceptable; missed
    secrets are not.
  - Add new patterns at the top of SECRETS, not at the bottom — earlier
    patterns short-circuit later ones, which is the safer failure mode.
  - The selftest must pass before this filter is trusted on a new
    secret class.

Status: DRAFT. Not committed. Not yet wired into a scheduled job.
"""
from __future__ import annotations
import re, sys, argparse

# (pattern, replacement, label)  — ordered, most-specific first
SECRETS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r'sk-or-v[0-9]+-[A-Za-z0-9]+'),                 'sk-or-vX-[REDACTED]',          'openrouter'),
    (re.compile(r'sk-[A-Za-z0-9]{20,}'),                        'sk-[REDACTED]',                'generic_sk'),
    (re.compile(r'nvapi-[A-Za-z0-9_-]{20,}'),                   'nvapi-[REDACTED]',             'nvidia'),
    (re.compile(r'xoxb-[0-9A-Za-z-]+'),                         'xoxb-[REDACTED]',              'slack'),
    (re.compile(r'\b[0-9]{8,}:AA[A-Za-z0-9_-]{30,}\b'),         '[TELEGRAM_TOKEN_REDACTED]',    'telegram'),
    (re.compile(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+'),
                                                                 '[JWT_REDACTED]',               'jwt'),
    (re.compile(r'\bghp_[A-Za-z0-9]{30,}\b'),                   'ghp_[REDACTED]',               'github'),
    (re.compile(r'\bAKIA[0-9A-Z]{16}\b'),                       'AKIA[REDACTED]',               'aws_key'),
    (re.compile(r'Bearer\s+[A-Za-z0-9._-]+'),                   'Bearer [REDACTED]',            'bearer'),
    (re.compile(r'\b[0-9a-f]{40,}\b'),                          '[HEX_TOKEN_REDACTED]',         'hex_long'),
    (re.compile(r'\b[0-9a-f]{32}\b'),                           '[HEX32_REDACTED]',             'hex32'),
    (re.compile(r'"api_key"\s*:\s*"[^"]+"'),                    '"api_key":"[REDACTED]"',       'json_api_key'),
    (re.compile(r'"token"\s*:\s*"[^"]+"'),                      '"token":"[REDACTED]"',         'json_token'),
    (re.compile(r'"password"\s*:\s*"[^"]+"'),                   '"password":"[REDACTED]"',      'json_password'),
]

def redact(text: str) -> str:
    for pat, rep, _label in SECRETS:
        text = pat.sub(rep, text)
    return text

def selftest() -> int:
    cases = [
        ("sk-or-v1-abc123def456",                         "sk-or-vX-[REDACTED]"),
        ("nvapi-FAKEABCDEFGHIJKLMNOPQRSTUVWX",            "nvapi-[REDACTED]"),
        ("xoxb-FAKE111-FAKE222-FAKEABCdefGHIjklMNO",      "xoxb-[REDACTED]"),
        ("1234567890:AAFAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKE", "[TELEGRAM_TOKEN_REDACTED]"),
        ("ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890",      "ghp_[REDACTED]"),
        ('{"api_key":"secret-value-here"}',               '{"api_key":"[REDACTED]"}'),
        ("Authorization: Bearer hunter2hunter2hunter2",   "Authorization: Bearer [REDACTED]"),
        ("feedfacefeedfacefeedfacefeedfacefeedfacefeedface", "[HEX_TOKEN_REDACTED]"),
        ("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ4In0.aBcDeF",   "[JWT_REDACTED]"),
        # negative: ordinary text should pass through
        ("ping pong status ok",                            "ping pong status ok"),
    ]
    fail = 0
    for raw, expect_contains in cases:
        out = redact(raw)
        ok = expect_contains in out
        print(f"  [{'OK' if ok else 'FAIL'}] {raw[:40]!r} -> {out[:60]!r}")
        if not ok: fail += 1
    print(f"\n{len(cases) - fail}/{len(cases)} passed")
    return 0 if fail == 0 else 1

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    sys.stdout.write(redact(sys.stdin.read()))
    return 0

if __name__ == "__main__":
    sys.exit(main())
