"""System control skills: apps, files, processes, clipboard, volume, screenshot."""

import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import psutil


def _is_linux(): return sys.platform.startswith("linux")
def _is_macos(): return sys.platform == "darwin"
def _is_windows(): return sys.platform == "win32"


APP_MAP = {
    "terminal": ["gnome-terminal", "xterm", "konsole", "alacritty", "wt", "Terminal"],
    "browser": ["xdg-open", "firefox", "google-chrome", "chromium", "brave"],
    "vscode": ["code"], "code": ["code"],
    "calculator": ["gnome-calculator", "kcalc", "calc"],
    "files": ["nautilus", "dolphin", "thunar", "pcmanfm", "explorer"],
    "settings": ["gnome-control-center", "systemsettings", "ms-settings:"],
    "chrome": ["google-chrome", "chromium"],
    "firefox": ["firefox"], "discord": ["discord"],
    "spotify": ["spotify"], "obsidian": ["obsidian"],
}


def open_app(app_name: str) -> str:
    key = app_name.lower().strip()
    candidates = APP_MAP.get(key, [app_name])
    for cmd in candidates:
        try:
            subprocess.Popen([cmd], start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Opened {app_name}"
        except FileNotFoundError:
            continue
    return f"Could not find {app_name}"


def list_processes() -> str:
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            procs.append(f"  {p.info['pid']:>6}  {p.info['name'][:30]:<30}  CPU:{p.info['cpu_percent']:>3}%  MEM:{p.info['memory_percent'] or 0:.1f}%")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    total = len(procs)
    return "Processes:\n" + "\n".join(procs[:50]) + (f"\n  ... ({total - 50} more)" if total > 50 else "")


def kill_process(pid: int = None, name: str = None) -> str:
    if pid:
        for p in psutil.process_iter(["pid", "name"]):
            if p.info["pid"] == pid:
                p.terminate()
                return f"Killed PID {pid} ({p.info['name']})"
        return f"No process with PID {pid}"
    if name:
        killed = [p for p in psutil.process_iter(["pid", "name"]) if name.lower() in (p.info["name"] or "").lower()]
        for p in killed:
            p.terminate()
        return f"Killed {len(killed)} process(es) matching '{name}'"
    return "Specify a PID or name"


def list_dir(path: str = ".") -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"Path not found: {path}"
    items = []
    for item in sorted(p.iterdir()):
        suffix = "/" if item.is_dir() else ""
        try:
            size = item.stat().st_size if item.is_file() else 0
        except OSError:
            size = 0
        items.append(f"  {item.name}{suffix:<30}  {_fmt_size(size)}")
    return f"Contents of {p}:\n" + "\n".join(items)


def _fmt_size(b: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"


def read_file(path: str) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"File not found: {path}"
    if p.is_dir():
        return f"{path} is a directory"
    try:
        content = p.read_text(errors="replace")
        if len(content) > 3000:
            content = content[:3000] + "\n\n... (truncated)"
        return content
    except Exception as e:
        return f"Error reading {path}: {e}"


def write_file(path: str, content: str) -> str:
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"Written to {path}"


def delete_file(path: str) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"Not found: {path}"
    if p.is_file():
        size = p.stat().st_size
        p.unlink()
        return f"Deleted {path} ({_fmt_size(size)})"
    shutil.rmtree(str(p))
    return f"Deleted directory {path}"


def move_file(src: str, dst: str) -> str:
    s = Path(src).expanduser()
    d = Path(dst).expanduser()
    if not s.exists():
        return f"Source not found: {src}"
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(s), str(d))
    return f"Moved {src} \u2192 {dst}"


def search_files(pattern: str, path: str = ".") -> str:
    root = Path(path).expanduser()
    if not root.exists():
        return f"Path not found: {path}"
    matches = list(root.rglob(pattern))
    if not matches:
        return f"No files matching '{pattern}' in {path}"
    results = [str(m.relative_to(root)) for m in matches[:30]]
    return f"Found {len(matches)} files matching '{pattern}' in {path}:\n" + "\n".join(f"  {r}" for r in results)


def get_clipboard() -> str:
    import pyperclip
    return pyperclip.paste()


def set_clipboard(text: str) -> str:
    import pyperclip
    pyperclip.copy(text)
    return "Copied to clipboard"


def screenshot(path: str = None) -> str:
    import pyautogui
    save_path = path or os.path.expanduser(f"~/Pictures/screenshot_{int(time.time())}.png")
    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    pyautogui.screenshot(save_path)
    return f"Screenshot saved to {save_path}"


def get_system_info() -> str:
    import platform
    cpu_count = psutil.cpu_count()
    cpu_percent = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    boot_time = datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")

    if _is_windows():
        from platform import uname
        sys_name = uname().system
        release = uname().release
        machine = uname().machine
        disk_path = "C:\\"
    else:
        sys_name = platform.system()
        release = platform.release()
        machine = platform.machine()
        disk_path = "/"

    disk = psutil.disk_usage(disk_path)
    return f"""System: {sys_name} {release} ({machine})
Uptime since: {boot_time}
CPU: {cpu_count} cores ({cpu_percent}% used)
Memory: {_fmt_size(mem.used)} / {_fmt_size(mem.total)} ({mem.percent}% used)
Disk: {_fmt_size(disk.used)} / {_fmt_size(disk.total)} ({disk.percent}% used)"""


def get_volume() -> str:
    if _is_linux():
        try:
            r = subprocess.run(["amixer", "get", "Master"], capture_output=True, text=True)
            if "[" in r.stdout:
                return f"Volume: {r.stdout.split('[')[1].split(']')[0]}"
        except FileNotFoundError:
            pass
    return "Volume query not supported on this OS"


def set_volume(level: int) -> str:
    if _is_linux():
        try:
            subprocess.run(["amixer", "set", "Master", f"{level}%"], check=True)
            return f"Volume set to {level}%"
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
    return "Volume control not supported on this OS"


def lock_screen() -> str:
    if _is_linux():
        for cmd in [["gnome-screensaver-command", "-l"], ["loginctl", "lock-session"]]:
            try:
                subprocess.run(cmd, check=True)
                return "Screen locked"
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue
    return "Screen lock not supported on this OS"
