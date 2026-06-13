#!/usr/bin/env python3
"""Comprehensive import and smoke test for Jarvis — no LLM required."""

import subprocess
import sys
import os
import traceback

PYTHONPATH = "/home/garvit/jarvis"
PASS = "PASS"
FAIL = "FAIL"
results = []

def test(label, fn):
    try:
        fn()
        results.append((label, PASS, ""))
    except Exception as e:
        tb = traceback.format_exc()
        results.append((label, FAIL, f"{type(e).__name__}: {e}\n{tb}"))

def report():
    print("=" * 72)
    print("  JARVIS MODULE IMPORT & SMOKE TEST REPORT")
    print("=" * 72)
    passed = 0
    failed = 0
    for label, status, msg in results:
        mark = "✓" if status == PASS else "✗"
        print(f"\n  [{mark}] {label}  —  {status}")
        if msg:
            print(f"       {msg.strip()}")
        if status == PASS:
            passed += 1
        else:
            failed += 1
    print()
    print("=" * 72)
    total = passed + failed
    print(f"  TOTAL: {total}  |  PASSED: {passed}  |  FAILED: {failed}")
    print("=" * 72)
    return failed == 0

os.environ["PYTHONPATH"] = PYTHONPATH
if PYTHONPATH not in sys.path:
    sys.path.insert(0, PYTHONPATH)

# ---------- 1. Individual module imports ----------

def try_import(modname):
    __import__(modname, fromlist=[""])

for mod in [
    "core.config",
    "core.events",
    "core.plugin",
    "core.personality",
    "core.safety",
    "core.memory",
    "voice.audio",
    "voice.stt",
    "voice.tts",
    "voice.wake_word",
    "skills.system_control",
    "skills.web_info",
    "skills.productivity",
    "skills.dev_tools",
    "core.llm",
    "core.orchestrator",
    "core.assistant",
    "main",
]:
    test(f"import {mod}", lambda m=mod: try_import(m))

# ---------- 2. main.py --once "hello" ----------

def test_main_once():
    result = subprocess.run(
        [sys.executable, "main.py", "--once", "hello"],
        capture_output=True, text=True, timeout=30,
        cwd=PYTHONPATH,
        env={**os.environ, "PYTHONPATH": PYTHONPATH},
    )
    # Should fail gracefully (no LLM running), not crash with import error
    assert "ImportError" not in result.stderr, f"ImportError in stderr: {result.stderr}"
    # Also shouldn't crash with ModuleNotFoundError
    assert "ModuleNotFoundError" not in result.stderr, f"ModuleNotFoundError in stderr: {result.stderr}"

test("main.py --once 'hello' (no crash)", test_main_once)

# ---------- 3. MemoryManager test ----------

def test_memory_manager():
    import tempfile
    from core.memory import MemoryManager
    import os

    db_dir = tempfile.mkdtemp(prefix="jarvis_test_mem_")
    db_path = os.path.join(db_dir, "test_memory.db")
    mm = MemoryManager(db_path=db_path)

    # Store a fact
    mm.store_fact("user_name", "Garvit")
    mm.store_fact("user_language", "Python")

    # Retrieve facts
    name = mm.get_fact("user_name")
    assert name == "Garvit", f"Expected 'Garvit', got '{name}'"

    lang = mm.get_fact("user_language")
    assert lang == "Python", f"Expected 'Python', got '{lang}'"

    # Get all facts
    all_facts = mm.get_all_facts()
    assert "user_name" in all_facts
    assert all_facts["user_name"] == "Garvit"
    assert all_facts["user_language"] == "Python"

    # Search facts
    results_found = mm.search_facts("Garvit")
    assert len(results_found) > 0, "search_facts should find 'Garvit'"

    # Non-existent fact
    missing = mm.get_fact("does_not_exist_xyz")
    assert missing is None, f"Expected None for missing fact, got '{missing}'"

    # Notes & reminders (side functionality)
    mm.add_note("Test note content", title="TestTitle")
    notes = mm.get_recent_notes(limit=5)
    assert len(notes) >= 1, "Should have at least 1 note"

    mm.add_reminder("Test reminder")
    reminders = mm.get_pending_reminders()
    assert len(reminders) >= 1, "Should have at least 1 reminder"

    mm.shutdown()
    import shutil
    shutil.rmtree(db_dir, ignore_errors=True)

test("MemoryManager (create, store fact, retrieve fact)", test_memory_manager)

# ---------- Print report ----------
success = report()
sys.exit(0 if success else 1)

