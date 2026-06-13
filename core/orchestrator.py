"""LLM tool-use orchestrator — the brain that routes queries to skills."""

import logging
from typing import Any, Callable, Dict, List

from .llm import LLMResponse, create_llm_engine
from .memory import MemoryManager
from .personality import Personality
from .safety import SafetyManager, RiskLevel

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, config, llm, tts, memory, personality, safety):
        self.config = config
        self.llm = llm
        self.tts = tts
        self.memory = memory
        self.personality = personality
        self.safety = safety
        self._tools = []
        self._tool_map = {}

    @classmethod
    def from_config(cls, config) -> "Orchestrator":
        llm = create_llm_engine(config.llm)
        llm.initialize()

        from voice.tts import create_tts_engine
        tts = create_tts_engine(config.tts)
        tts.initialize()

        memory = MemoryManager(
            db_path=config.general.data_dir + "/memory.db",
        )

        personality = Personality({"persona": {"name": config.general.name}})
        safety = SafetyManager()

        instance = cls(config, llm, tts, memory, personality, safety)
        instance._tools = instance._build_tools_schema()
        instance._tool_map = instance._build_tool_map()
        instance.llm.register_tools(instance._tools, instance._tool_map)
        return instance

    def _build_tools_schema(self) -> List[Dict]:
        def tool(name, desc, props=None, required=None):
            fn = {"name": name, "description": desc, "parameters": {"type": "object", "properties": props or {}}}
            if required:
                fn["parameters"]["required"] = required
            return {"type": "function", "function": fn}

        return [
            tool("open_app", "Open application by name", {"app_name": {"type": "string"}}, ["app_name"]),
            tool("list_processes", "List running processes"),
            tool("kill_process", "Kill a process by PID or name", {"pid": {"type": "integer"}, "name": {"type": "string"}}),
            tool("list_dir", "List directory contents", {"path": {"type": "string"}}),
            tool("read_file", "Read a file", {"path": {"type": "string"}}, ["path"]),
            tool("write_file", "Write content to a file", {"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
            tool("delete_file", "Delete a file or directory", {"path": {"type": "string"}}, ["path"]),
            tool("move_file", "Move or rename a file", {"src": {"type": "string"}, "dst": {"type": "string"}}, ["src", "dst"]),
            tool("search_files", "Search files by glob pattern", {"pattern": {"type": "string"}, "path": {"type": "string"}}, ["pattern"]),
            tool("search_web", "Search the web", {"query": {"type": "string"}}, ["query"]),
            tool("get_weather", "Get weather for a location", {"location": {"type": "string"}}),
            tool("get_news", "Get top headlines", {"topic": {"type": "string"}}),
            tool("summarize_page", "Summarize a webpage", {"url": {"type": "string"}}, ["url"]),
            tool("get_time", "Get current date and time"),
            tool("take_note", "Save a note", {"content": {"type": "string"}, "title": {"type": "string"}}, ["content"]),
            tool("get_notes", "Get recent notes", {"limit": {"type": "integer"}}),
            tool("set_reminder", "Set a reminder", {"content": {"type": "string"}, "due_at": {"type": "string"}}, ["content"]),
            tool("get_reminders", "List pending reminders"),
            tool("run_shell", "Run a shell command", {"command": {"type": "string"}, "workdir": {"type": "string"}}, ["command"]),
            tool("git_status", "Show git status", {"repo_path": {"type": "string"}}),
            tool("git_pull", "Git pull", {"repo_path": {"type": "string"}}),
            tool("git_log", "Show recent commits", {"repo_path": {"type": "string"}, "count": {"type": "integer"}}),
            tool("get_system_info", "Get system information"),
            tool("screenshot", "Take a screenshot", {"path": {"type": "string"}}),
            tool("lock_screen", "Lock the screen"),
            tool("morning_briefing", "Morning briefing with weather, news, reminders"),
        ]

    def _build_tool_map(self) -> Dict[str, Callable]:
        import skills.system_control as sys_sk
        import skills.web_info as web_sk
        import skills.productivity as prod_sk
        import skills.dev_tools as dev_sk

        return {
            "open_app": sys_sk.open_app, "list_processes": sys_sk.list_processes,
            "kill_process": sys_sk.kill_process, "list_dir": sys_sk.list_dir,
            "read_file": sys_sk.read_file, "write_file": sys_sk.write_file,
            "delete_file": sys_sk.delete_file, "move_file": sys_sk.move_file,
            "search_files": sys_sk.search_files, "get_system_info": sys_sk.get_system_info,
            "screenshot": sys_sk.screenshot, "lock_screen": sys_sk.lock_screen,
            "search_web": web_sk.search_web, "get_weather": web_sk.get_weather,
            "get_news": web_sk.get_news, "summarize_page": web_sk.summarize_page,
            "get_time": web_sk.get_time,
            "take_note": prod_sk.take_note, "get_notes": prod_sk.get_notes,
            "set_reminder": prod_sk.set_reminder, "get_reminders": prod_sk.get_reminders,
            "morning_briefing": prod_sk.morning_briefing,
            "run_shell": dev_sk.run_shell, "git_status": dev_sk.git_status,
            "git_pull": dev_sk.git_pull, "git_log": dev_sk.git_log,
        }

    async def process(self, text: str) -> str:
        logger.info(f"Processing: {text}")
        self.memory.store_conversation("user", text)

        response = await self._process_llm(text)
        if response and "encountered an error" not in response:
            return response

        return self._route_directly(text)

    async def _process_llm(self, text: str) -> str:
        history = self.memory.get_recent_conversations(8)
        messages = [{"role": "system", "content": self.personality.system_prompt}]
        for h in history:
            messages.append({"role": "assistant" if h["role"] == "assistant" else "user", "content": h["content"]})
        messages.append({"role": "user", "content": text})

        for _ in range(5):
            response = await self.llm.chat(messages)
            if not response.has_tool_calls:
                self.memory.store_conversation("assistant", response.text)
                return response.text

            for tc in response.tool_calls:
                result = self._exec_tool(tc.name, tc.arguments)
                messages.append({"role": "tool", "content": result, "tool_call_id": tc.id})

        final = messages[-1]["content"] if messages else ""
        self.memory.store_conversation("assistant", final)
        return final

    def _route_directly(self, text: str) -> str:
        text_lower = text.lower().strip()
        routes = [
            ("time", "get_time", {}),
            ("weather", "get_weather", {"location": ""}),
            ("news", "get_news", {}),
            ("screenshot", "screenshot", {}),
            ("note", "take_note", {"content": text}),
            ("remind", "set_reminder", {"content": text}),
            ("open ", "open_app", {"app_name": text_lower.replace("open ", "", 1)}),
            ("launch ", "open_app", {"app_name": text_lower.replace("launch ", "", 1)}),
            ("lock", "lock_screen", {}),
            ("process", "list_processes", {}),
            ("files in ", "list_dir", {"path": text_lower.replace("files in ", "", 1)}),
            ("list ", "list_dir", {"path": text_lower.replace("list ", "", 1)}),
            ("dir ", "list_dir", {"path": text_lower.replace("dir ", "", 1)}),
            ("briefing", "morning_briefing", {}),
            ("read ", "read_file", {"path": text_lower.replace("read ", "", 1)}),
            ("search ", "search_web", {"query": text_lower.replace("search ", "", 1)}),
            ("system", "get_system_info", {}),
            ("kill ", "kill_process", {"name": text_lower.replace("kill ", "", 1)}),
            ("git status", "git_status", {}),
            ("git pull", "git_pull", {}),
        ]

        for keyword, tool_name, default_args in routes:
            if keyword in text_lower:
                fn = self._tool_map.get(tool_name)
                if fn:
                    try:
                        args = {}
                        for k, v in default_args.items():
                            if isinstance(v, str) and v == text:
                                args[k] = text
                            else:
                                args[k] = v
                        result = fn(**args)
                    except Exception as e:
                        result = f"Error: {e}"
                    self.memory.store_conversation("assistant", result)
                    return result

        if any(cmd in text_lower for cmd in ["hi", "hello", "hey", "what's up"]):
            reply = "Hey. What can I do for you?"
        else:
            reply = f"I heard: '{text}' — but I need the AI model running (ollama) to understand complex requests. Try: 'time', 'weather', 'open browser', 'take a note', or use --text mode with ollama running."

        self.memory.store_conversation("assistant", reply)
        return reply

    def _exec_tool(self, name: str, args: dict) -> str:
        risk = self.safety.classify(name, args)
        if risk == RiskLevel.BLOCKED:
            return f"[BLOCKED] {name} is not permitted."
        if risk == RiskLevel.CONFIRM:
            return f"[CONFIRMATION REQUIRED] {name} needs approval."
        fn = self._tool_map.get(name)
        if not fn:
            return f"Unknown tool: {name}"
        try:
            result = fn(**args)
            self.safety.record(name, args)
            return str(result)
        except Exception as e:
            logger.exception(f"Tool {name} failed")
            return f"Error: {e}"

    async def speak(self, text: str):
        await self.tts.speak(text)

    async def shutdown(self):
        await self.llm.shutdown()
        self.tts.shutdown()
        self.memory.shutdown()
