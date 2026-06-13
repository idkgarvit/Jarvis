"""Developer skills: git, shell commands, code tools."""

import os
import shlex
import subprocess
from pathlib import Path
from typing import Optional


def run_shell(command: str, workdir: str = "") -> str:
    cwd = os.path.expanduser(workdir) if workdir else os.getcwd()
    try:
        result = subprocess.run(
            ["bash", "-c", command],
            capture_output=True, text=True,
            timeout=60, cwd=cwd,
        )
        output = result.stdout
        if result.stderr:
            output += "\nSTDERR:\n" + result.stderr
        if len(output) > 3000:
            output = output[:3000] + "\n... (truncated)"
        if result.returncode != 0:
            return f"Exit code {result.returncode}\n{output}"
        return output or "Command completed (no output)"
    except subprocess.TimeoutExpired:
        return "Command timed out (60s)"
    except Exception as e:
        return f"Error: {e}"


def git_status(repo_path: str = "") -> str:
    path = repo_path or os.getcwd()
    return run_shell("git status", path)


def git_pull(repo_path: str = "") -> str:
    path = repo_path or os.getcwd()
    return run_shell("git pull --ff-only", path)


def git_push(repo_path: str = "", message: str = "") -> str:
    path = repo_path or os.getcwd()
    if message:
        run_shell("git add -A", path)
        result = run_shell(f'git commit -m {shlex.quote(message)}', path)
        if "nothing to commit" in result.lower():
            return "Nothing to commit"
    return run_shell("git push", path)


def git_log(repo_path: str = "", count: int = 10) -> str:
    path = repo_path or os.getcwd()
    return run_shell(f"git log --oneline -{count}", path)


def list_directory(path: str = ".") -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"Path not found: {path}"
    items = [f"  {item.name}{'/' if item.is_dir() else ''}" for item in sorted(p.iterdir())]
    return f"Contents of {p}:\n" + "\n".join(items)
