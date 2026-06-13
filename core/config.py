"""
Configuration Management for Jarvis
===================================
Handles loading, validation, and access to configuration.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATHS = [
    Path("config.yaml"),
    Path.home() / ".config" / "jarvis" / "config.yaml",
    Path("/etc/jarvis/config.yaml"),
]


@dataclass
class GeneralConfig:
    name: str = "Jarvis"
    version: str = "2.0.0"
    language: str = "en"
    log_level: str = "INFO"
    data_dir: str = "~/.local/share/jarvis"
    config_dir: str = "~/.config/jarvis"
    cache_dir: str = "~/.cache/jarvis"


@dataclass
class WakeWordConfig:
    enabled: bool = True
    engine: str = "porcupine"
    keywords: list = field(default_factory=lambda: ["jarvis", "hey jarvis"])
    sensitivity: float = 0.7
    model_path: str = ""


@dataclass
class STTConfig:
    engine: str = "whisper"
    model: str = "base.en"
    device: str = "auto"
    compute_type: str = "int8"
    language: str = "en"
    beam_size: int = 5
    vad_filter: bool = True
    vosk_model_path: str = "~/.cache/jarvis/vosk-model"
    whisper_cpp_path: str = "~/.cache/jarvis/whisper.cpp"


@dataclass
class TTSConfig:
    engine: str = "piper"
    voice: str = "en_US-lessac-medium"
    speed: float = 1.0
    piper_model_dir: str = "~/.cache/jarvis/piper"
    kokoro_model: str = "kokoro-v1.0.onnx"
    kokoro_voice: str = "af_heart"
    fallback_engine: str = "pyttsx3"


@dataclass
class LLMConfig:
    engine: str = "ollama"
    model: str = "qwen2.5:7b-instruct-q4_K_M"
    base_url: str = "https://integrate.api.nvidia.com/v1"
    api_key: str = ""
    fallback_models: list = field(default_factory=list)
    ollama_host: str = "http://localhost:11434"
    ollama_auto_pull: bool = True
    llama_cpp_model_path: str = "~/.cache/jarvis/models"
    llama_cpp_n_ctx: int = 8192
    llama_cpp_n_gpu_layers: int = -1
    llama_cpp_threads: int = 4
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 4096
    system_prompt: str = "You are JARVIS, a highly capable AI assistant."


@dataclass
class BrowserConfig:
    engine: str = "playwright"
    headless: bool = False
    persistent_context: bool = True
    user_data_dir: str = "~/.config/jarvis/browser"
    timeout: int = 30000
    stealth: bool = True
    block_resources: list = field(default_factory=lambda: ["image", "font", "media"])


@dataclass
class GmailConfig:
    enabled: bool = False
    credentials_path: str = "~/.config/jarvis/gmail_credentials.json"
    token_path: str = "~/.config/jarvis/gmail_token.json"
    scopes: list = field(default_factory=lambda: [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.modify",
    ])


@dataclass
class WhatsAppConfig:
    enabled: bool = False
    engine: str = "whatsapp-web.js"
    session_path: str = "~/.config/jarvis/whatsapp_session"
    headless: bool = True


@dataclass
class CalendarConfig:
    enabled: bool = False
    provider: str = "google"
    credentials_path: str = "~/.config/jarvis/calendar_credentials.json"


@dataclass
class IntegrationsConfig:
    gmail: GmailConfig = field(default_factory=GmailConfig)
    whatsapp: WhatsAppConfig = field(default_factory=WhatsAppConfig)
    calendar: CalendarConfig = field(default_factory=CalendarConfig)


@dataclass
class PluginConfig:
    enabled: bool = True
    auto_load: bool = True
    plugin_dirs: list = field(default_factory=lambda: [
        "~/.config/jarvis/plugins",
        "./plugins",
    ])
    builtin_plugins: list = field(default_factory=lambda: [
        "system_control",
        "file_operations",
        "web_search",
        "code_execution",
        "weather",
        "calculator",
        "timer_alarm",
    ])


@dataclass
class DaemonConfig:
    enabled: bool = True
    pid_file: str = "~/.local/share/jarvis/jarvis.pid"
    log_file: str = "~/.local/share/jarvis/jarvis.log"
    restart_on_failure: bool = True
    max_restarts: int = 3
    health_check_interval: int = 30


@dataclass
class VectorDBConfig:
    enabled: bool = True
    type: str = "chromadb"
    path: str = "~/.local/share/jarvis/vector_db"
    collection: str = "jarvis_memory"
    embedding_model: str = "all-MiniLM-L6-v2"


@dataclass
class CacheConfig:
    enabled: bool = True
    ttl: int = 3600
    max_size: int = 1000


@dataclass
class PerformanceConfig:
    vector_db: VectorDBConfig = field(default_factory=VectorDBConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    workers: int = 4
    async_io: bool = True


@dataclass
class SecurityConfig:
    require_confirmation: bool = True
    dangerous_commands_need_approval: bool = True
    allowed_domains: list = field(default_factory=list)
    blocked_domains: list = field(default_factory=list)
    api_key_rotation_days: int = 90


@dataclass
class InstallationConfig:
    auto_install_local_ai: bool = True
    preferred_llm_backend: str = "ollama"
    preferred_stt_backend: str = "whisper"
    preferred_tts_backend: str = "piper"
    download_models_on_first_run: bool = True
    skip_model_download: bool = False
    model_download_timeout: int = 300


@dataclass
class Config:
    general: GeneralConfig = field(default_factory=GeneralConfig)
    wake_word: WakeWordConfig = field(default_factory=WakeWordConfig)
    stt: STTConfig = field(default_factory=STTConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    integrations: IntegrationsConfig = field(default_factory=IntegrationsConfig)
    plugins: PluginConfig = field(default_factory=PluginConfig)
    daemon: DaemonConfig = field(default_factory=DaemonConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    installation: InstallationConfig = field(default_factory=InstallationConfig)

    def expand_paths(self):
        """Expand ~ in all path fields."""
        for field_name in dir(self):
            if not field_name.startswith('_'):
                value = getattr(self, field_name)
                if isinstance(value, str) and value.startswith('~'):
                    setattr(self, field_name, os.path.expanduser(value))
                elif hasattr(value, '__dataclass_fields__'):
                    # Nested dataclass
                    for nested_field in dir(value):
                        if not nested_field.startswith('_'):
                            nested_value = getattr(value, nested_field)
                            if isinstance(nested_value, str) and nested_value.startswith('~'):
                                setattr(value, nested_field, os.path.expanduser(nested_value))
                            elif isinstance(nested_value, list):
                                expanded = [os.path.expanduser(v) if isinstance(v, str) and v.startswith('~') else v for v in nested_value]
                                setattr(value, nested_field, expanded)

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by dot-notation key (e.g., 'llm.model')."""
        keys = key.split('.')
        value = self
        for k in keys:
            if hasattr(value, k):
                value = getattr(value, k)
            else:
                return default
        return value

    def set(self, key: str, value: Any):
        """Set config value by dot-notation key."""
        keys = key.split('.')
        obj = self
        for k in keys[:-1]:
            obj = getattr(obj, k)
        setattr(obj, keys[-1], value)


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from YAML file."""
    config = Config()

    # Try default paths
    paths = [Path(config_path)] if config_path else DEFAULT_CONFIG_PATHS

    for path in paths:
        if path and path.exists():
            try:
                with open(path, 'r') as f:
                    data = yaml.safe_load(f)
                if data:
                    _apply_config_dict(config, data)
                logger.info(f"Loaded config from {path}")
                break
            except Exception as e:
                logger.warning(f"Failed to load config from {path}: {e}")

    config.expand_paths()

    # Override API key from env var if set
    import os
    nv_key = os.environ.get("NVIDIA_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if nv_key:
        config.set("llm.api_key", nv_key)

    return config


def _apply_config_dict(config: Config, data: Dict[str, Any], prefix: str = ""):
    """Recursively apply config dictionary to config object."""
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if hasattr(config, key):
            attr = getattr(config, key)
            if hasattr(attr, '__dataclass_fields__'):
                # Nested dataclass
                if isinstance(value, dict):
                    _apply_config_dict(attr, value, full_key)
            elif isinstance(value, dict):
                # Try to set nested attributes
                for sub_key, sub_value in value.items():
                    if hasattr(attr, sub_key):
                        setattr(attr, sub_key, sub_value)
            else:
                setattr(config, key, value)