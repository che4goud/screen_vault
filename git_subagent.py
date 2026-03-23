import subprocess
import os
import sys

def run_git_command(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command {' '.join(command)}: {e.stderr}")
        return None

def auto_commit_and_push(message):
    print(f"🚀 Subagent: Committing and pushing changes with message: '{message}'")
    
    # Check if there are changes
    status = run_git_command(["git", "status", "--porcelain"])
    if not status:
        print("✅ No changes to commit.")
        return

    # Add all changes
    run_git_command(["git", "add", "."])
    
    # Commit
    run_git_command(["git", "commit", "-m", message])
    
    # Push (assuming remote 'origin' and branch 'main' are set up)
    # Note: This might fail if remote is not set up, which is expected for a new repo
    print("📤 Attempting to push to origin main...")
    run_git_command(["git", "push", "origin", "main"])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python git_subagent.py 'your commit message'")
    else:
        msg = " ".join(sys.argv[1:])
        auto_commit_and_push(msg)
