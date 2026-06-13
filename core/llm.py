import json
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolCall:
    def __init__(self, name: str, arguments: Dict[str, Any], id: str = ""):
        self.name = name
        self.arguments = arguments
        self.id = id

    @classmethod
    def from_dict(cls, d: dict) -> "ToolCall":
        args = d.get("arguments", {})
        if isinstance(args, str):
            args = json.loads(args)
        return cls(name=d.get("name", ""), arguments=args, id=d.get("id", ""))


class LLMResponse:
    def __init__(self, text: str = "", tool_calls: List[ToolCall] = None):
        self.text = text
        self.tool_calls = tool_calls or []

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class OllamaLLM:
    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "qwen2.5:7b-instruct-q4_K_M",
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 2048,
        system_prompt: str = "",
    ):
        self.host = host.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self._tools: List[Dict[str, Any]] = []
        self._tool_map: Dict[str, Callable] = {}
        self._client = None

    def initialize(self):
        import httpx
        self._client = httpx.AsyncClient(timeout=120)
        try:
            import httpx
            r = httpx.get(f"{self.host}/api/tags", timeout=5)
            models = [m["name"] for m in r.json().get("models", [])]
            if self.model not in models:
                logger.warning(f"Model {self.model} not found in Ollama. Available: {models[:3]}...")
            else:
                logger.info(f"Ollama connected: {self.model}")
        except Exception as e:
            logger.warning(f"Ollama not reachable at {self.host}: {e}")

    def register_tools(self, tools: List[Dict[str, Any]], tool_map: Dict[str, Callable]):
        self._tools = tools
        self._tool_map = tool_map

    async def generate(self, messages: List[Dict[str, str]], tools: List[Dict] = None) -> str:
        response = await self._chat(messages, tools or self._tools)
        return response.text

    async def chat(self, messages: List[Dict[str, str]]) -> LLMResponse:
        return await self._chat(messages, self._tools)

    async def _chat(self, messages: List[Dict[str, str]], tools: List[Dict]) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        try:
            r = await self._client.post(f"{self.host}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()

            text = data.get("message", {}).get("content", "")
            raw_tool_calls = data.get("message", {}).get("tool_calls", [])

            tool_calls = []
            for tc in raw_tool_calls:
                func = tc.get("function", {})
                tool_calls.append(ToolCall(
                    name=func.get("name", ""),
                    arguments=func.get("arguments", {}),
                    id=tc.get("id", ""),
                ))
            return LLMResponse(text=text, tool_calls=tool_calls)

        except Exception as e:
            logger.error(f"LLM error: {e}")
            return LLMResponse(text="I encountered an error processing that.")

    async def shutdown(self):
        if self._client:
            await self._client.aclose()


class OpenAILLM:
    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_prompt: str = "",
        fallback_models: list = None,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.fallback_models = fallback_models or []
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self._tools: List[Dict] = []
        self._tool_map: Dict[str, Callable] = {}
        self._client = None

    def initialize(self):
        if not self.api_key:
            logger.warning("OpenAI: no API key configured")
        logger.info(f"OpenAI LLM configured: {self.model} @ {self.base_url}")

    def register_tools(self, tools: List[Dict], tool_map: Dict[str, Callable]):
        self._tools = tools
        self._tool_map = tool_map

    async def generate(self, messages: List[Dict[str, str]], tools: List[Dict] = None) -> str:
        response = await self._chat(messages, tools or self._tools)
        return response.text

    async def chat(self, messages: List[Dict[str, str]]) -> LLMResponse:
        return await self._chat(messages, self._tools)

    async def _chat(self, messages: List[Dict[str, str]], tools: List[Dict]) -> LLMResponse:
        from openai import AsyncOpenAI

        models_to_try = [self.model] + self.fallback_models
        last_error = ""

        for model in models_to_try:
            client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url, timeout=120)
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }
            if tools:
                kwargs["tools"] = tools

            try:
                r = await client.chat.completions.create(**kwargs)
                choice = r.choices[0]
                text = choice.message.content or ""

                tool_calls = []
                if choice.message.tool_calls:
                    for tc in choice.message.tool_calls:
                        args = tc.function.arguments
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except json.JSONDecodeError:
                                args = {}
                        tool_calls.append(ToolCall(
                            name=tc.function.name,
                            arguments=args,
                            id=tc.id,
                        ))

                if model != self.model:
                    logger.info(f"Fell back to model: {model}")
                return LLMResponse(text=text, tool_calls=tool_calls)

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Model {model} failed: {last_error}")
                continue

        logger.error(f"All models failed. Last error: {last_error}")
        return LLMResponse(text="I encountered an error processing that.")

    async def shutdown(self):
        pass


def create_llm_engine(config):
    engine = getattr(config, "engine", "ollama")
    if engine == "openai":
        return OpenAILLM(
            api_key=getattr(config, "api_key", ""),
            base_url=getattr(config, "base_url", "https://api.openai.com/v1"),
            model=getattr(config, "model", "gpt-4o-mini"),
            temperature=getattr(config, "temperature", 0.7),
            max_tokens=getattr(config, "max_tokens", 2048),
            system_prompt=getattr(config, "system_prompt", ""),
            fallback_models=getattr(config, "fallback_models", []),
        )
    return OllamaLLM(
        host=getattr(config, "ollama_host", "http://localhost:11434"),
        model=getattr(config, "model", "qwen2.5:7b-instruct-q4_K_M"),
        temperature=getattr(config, "temperature", 0.7),
        top_p=getattr(config, "top_p", 0.9),
        max_tokens=getattr(config, "max_tokens", 2048),
        system_prompt=getattr(config, "system_prompt", ""),
    )
