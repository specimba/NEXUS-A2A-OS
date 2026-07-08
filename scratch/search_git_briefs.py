import subprocess

print("Searching git history for files matching 'brief'...")
try:
    res = subprocess.run(
        ["git", "log", "--all", "--name-only", "--pretty=format:"],
        capture_output=True, text=True, check=True
    )
    files = set(res.stdout.splitlines())
    for f in sorted(files):
        if "brief" in f:
            print(f"  {f}")
except Exception as e:
    print(f"Error: {e}")
