import subprocess
import os
import sys
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- CONFIGURATION ---
# Exclude git directory and the subagent script itself to avoid infinite loops
EXCLUDE_DIRS = {'.git', '__pycache__', '.pytest_cache', '.venv', 'venv', 'node_modules'}
EXCLUDE_FILES = {'git_subagent.py', '.DS_Store'}
COMMIT_COOLDOWN = 10 # Seconds to wait after a change before committing (to bundle changes)

class GitAutomationHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_modified_time = 0
        self.pending_changes = False

    def on_modified(self, event):
        if event.is_directory:
            return
        
        filename = os.path.basename(event.src_path)
        parts = event.src_path.split(os.sep)
        
        # Check if the file or its parent directories should be ignored
        if any(d in parts for d in EXCLUDE_DIRS) or filename in EXCLUDE_FILES:
            return

        print(f"📝 Change detected: {filename}")
        self.last_modified_time = time.time()
        self.pending_changes = True

def run_git_command(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running {' '.join(command)}: {e.stderr}")
        return None

def auto_commit_and_push(message="Automated commit by subagent"):
    status = run_git_command(["git", "status", "--porcelain"])
    if not status:
        return

    print(f"🚀 Subagent: Syncing changes...")
    run_git_command(["git", "add", "."])
    run_git_command(["git", "commit", "-m", message])
    
    # Check if remote exists before pushing
    remote = run_git_command(["git", "remote"])
    if remote:
        print("📤 Pushing to main...")
        run_git_command(["git", "push", "origin", "main"])
    else:
        print("ℹ️ No remote 'origin' found. Changes committed locally.")

if __name__ == "__main__":
    print("🤖 Git Subagent started. Monitoring for changes...")
    event_handler = GitAutomationHandler()
    observer = Observer()
    observer.schedule(event_handler, path=".", recursive=True)
    observer.start()

    try:
        while True:
            # If changes were detected and cooldown has passed
            if event_handler.pending_changes and (time.time() - event_handler.last_modified_time > COMMIT_COOLDOWN):
                auto_commit_and_push(f"Auto-sync: updates detected at {time.strftime('%H:%M:%S')}")
                event_handler.pending_changes = False
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
