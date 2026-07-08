import subprocess
import re

print("Searching git commits for HF tokens...")
try:
    # Run git log -p to get all diffs in history
    res = subprocess.run(
        ["git", "log", "--all", "-p"],
        capture_output=True, text=True, check=True
    )
    tokens = set(re.findall(r'hf_[a-zA-Z0-9]{34}', res.stdout))
    print(f"Found {len(tokens)} token candidates:")
    for t in tokens:
        print(f"  {t}")
except Exception as e:
    print(f"Error: {e}")
