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


if __name__ == "__main__":
    success, msg = deploy()
    print(f"  {'[OK]' if success else '[FAIL]'} {msg}")
