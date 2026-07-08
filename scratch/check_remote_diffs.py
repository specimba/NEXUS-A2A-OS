import subprocess
import os

repo_dir = r"c:\Users\speci.000\Documents\NEXUS"

def run_git(args):
    try:
        out = subprocess.check_output(["git"] + args, cwd=repo_dir, stderr=subprocess.STDOUT)
        return out.decode("utf-8", errors="ignore").strip()
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e.output.decode('utf-8', errors='ignore').strip()}"

remote_branches = [
    "alpha/main",
    "alpha/DASHBOARD-GLM51",
    "alpha/codex/specimba/1805mainSpeci",
    "alpha/devin/1779538676-short-term-actions",
    "alpha/devin/1780270571.18507-fix-netlify-deploy-v2"
]

print("="*80)
print("COMPARING REMOTE ALPHA BRANCHES AGAINST LOCAL MAIN")
print("="*80)

for rb in remote_branches:
    commits_ahead = run_git(["log", "main.." + rb, "--oneline"])
    commits_behind = run_git(["log", rb + "..main", "--oneline"])
    
    ahead_count = len(commits_ahead.splitlines()) if commits_ahead and not commits_ahead.startswith("ERROR") else 0
    behind_count = len(commits_behind.splitlines()) if commits_behind and not commits_behind.startswith("ERROR") else 0
    
    print(f"\nRemote Branch: {rb}")
    print(f"  -> Commits ahead of local main: {ahead_count}")
    print(f"  -> Commits behind local main: {behind_count}")
    
    if ahead_count > 0:
        print("  -> Top 10 files changed vs main:")
        files_changed = run_git(["diff", "main.." + rb, "--name-status"])
        if files_changed and not files_changed.startswith("ERROR"):
            lines = files_changed.splitlines()
            for line in lines[:10]:
                print(f"     {line}")
            if len(lines) > 10:
                print(f"     ... and {len(lines) - 10} more files")
        
        print("  -> Sample commits (up to 5):")
        commit_lines = commits_ahead.splitlines()
        for line in commit_lines[:5]:
            print(f"     {line}")
            
print("="*80)
