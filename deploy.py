#!/usr/bin/env python3
"""
Auto-deploy updated dashboards to GitHub Pages.
Called after each bot cycle when --deploy flag is used.
Commits and pushes arena_dashboard.html and bot data to the repo.
"""

import subprocess
import datetime
from pathlib import Path

PLATFORM_DIR = Path(__file__).parent


def deploy():
    """Git add, commit, and push the latest dashboard files."""
    try:
        # Files to push (dashboards + portfolio state for transparency)
        files_to_add = [
            "arena_dashboard.html",
            "dashboard.html",
        ]

        # Also add bot portfolio snapshots (so people can see raw data)
        for bot_dir in (PLATFORM_DIR / "bots").iterdir():
            if bot_dir.is_dir():
                for fname in ["portfolio.json", "value_history.json"]:
                    fpath = bot_dir / fname
                    if fpath.exists():
                        files_to_add.append(str(fpath.relative_to(PLATFORM_DIR)))

        # Stage files
        for f in files_to_add:
            subprocess.run(
                ["git", "add", f],
                cwd=str(PLATFORM_DIR),
                capture_output=True,
                timeout=30,
            )

        # Check if there are changes to commit
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=str(PLATFORM_DIR),
            capture_output=True,
        )

        if result.returncode == 0:
            # No changes to commit
            return True, "No changes to deploy"

        # Commit
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        commit_msg = f"Bot update {now}"

        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=str(PLATFORM_DIR),
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return False, f"Commit failed: {result.stderr[:100]}"

        # Push
        result = subprocess.run(
            ["git", "push"],
            cwd=str(PLATFORM_DIR),
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            return False, f"Push failed: {result.stderr[:100]}"

        return True, f"Deployed at {now}"

    except subprocess.TimeoutExpired:
        return False, "Deploy timed out"
    except FileNotFoundError:
        return False, "Git not found — install git first"
    except Exception as e:
        return False, f"Deploy error: {str(e)[:100]}"


def deploy_verbose():
    """Same as deploy() but prints git output so you can see what's happening."""
    try:
        # Stage ALL changed files (dashboards + bot data)
        print("        git add -A ...")
        result = subprocess.run(
            ["git", "add", "-A"],
            cwd=str(PLATFORM_DIR),
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            print(f"        git add stderr: {result.stderr}")
            return False, f"git add failed: {result.stderr[:100]}"

        # Check for changes
        result = subprocess.run(
            ["git", "diff", "--cached", "--stat"],
            cwd=str(PLATFORM_DIR),
            capture_output=True, text=True,
        )
        if not result.stdout.strip():
            return True, "No changes to deploy"
        print(f"        Changes: {result.stdout.strip().split(chr(10))[-1]}")

        # Commit
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        commit_msg = f"Bot update {now}"
        print(f"        git commit -m '{commit_msg}' ...")
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=str(PLATFORM_DIR),
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            print(f"        Commit stderr: {result.stderr}")
            return False, f"Commit failed: {result.stderr[:100]}"
        print(f"        Committed OK")

        # Push
        print(f"        git push ...")
        result = subprocess.run(
            ["git", "push"],
            cwd=str(PLATFORM_DIR),
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            print(f"        Push stderr: {result.stderr}")
            return False, f"Push failed: {result.stderr[:100]}"
        print(f"        Push OK: {result.stderr.strip().split(chr(10))[-1] if result.stderr else 'done'}")

        return True, f"Deployed at {now}"

    except subprocess.TimeoutExpired:
        return False, "Deploy timed out"
    except Exception as e:
        import traceback; traceback.print_exc()
        return False, f"Deploy error: {str(e)[:100]}"


if __name__ == "__main__":
    success, msg = deploy_verbose()
    print(f"  {'[OK]' if success else '[FAIL]'} {msg}")
