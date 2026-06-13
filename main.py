#!/usr/bin/env python3
"""Jarvis — Cross-platform voice AI assistant.

Usage:
  python main.py                  # Full voice mode (wake word + STT + TTS)
  python main.py --text           # Text-only interactive mode
  python main.py --once "query"   # Single query, text response
  python main.py --install-deps   # Install required model files
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Load .env if it exists
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


async def run_voice_mode():
    from core.config import load_config
    from core.assistant import JarvisAssistant
    from ui.jarvis_tui import JarvisTUI

    config = load_config()
    app = JarvisTUI(assistant_cls=JarvisAssistant, config=config)
    await app.run_async()


async def run_text_mode():
    from ui.jarvis_tui import JarvisTUI
    app = JarvisTUI()
    await app.run_async()


async def run_single_query(query: str):
    from core.config import load_config
    from core.orchestrator import Orchestrator

    config = load_config()
    orch = Orchestrator.from_config(config)
    response = await orch.process(query)
    print(response)
    await orch.shutdown()


def install_deps():
    """Download whisper model for STT."""
    print("Downloading faster-whisper base.en model...")
    try:
        from faster_whisper import WhisperModel
        WhisperModel("base.en", device="cpu", compute_type="int8")
        print("Model downloaded successfully.")
    except Exception as e:
        print(f"Model download failed: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Jarvis Voice Assistant")
    parser.add_argument("--text", action="store_true", help="Text-only interactive mode")
    parser.add_argument("--once", type=str, help="Single query mode")
    parser.add_argument("--install-deps", action="store_true", help="Download model files")
    parser.add_argument("--log-level", default="INFO", help="Log level (DEBUG, INFO, WARNING)")

    args = parser.parse_args()

    setup_logging(args.log_level)

    if args.install_deps:
        install_deps()
        return

    if args.once:
        asyncio.run(run_single_query(args.once))
    elif args.text:
        asyncio.run(run_text_mode())
    else:
        asyncio.run(run_voice_mode())


if __name__ == "__main__":
    main()
