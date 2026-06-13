"""
Plugin System for Jarvis
========================
Modular plugin architecture for extensibility.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
import importlib.util
import inspect

from .events import EventBus, Event, Events, get_event_bus
from .config import Config

logger = logging.getLogger(__name__)


@dataclass
class PluginMetadata:
    """Plugin metadata."""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)
    intents: List[str] = field(default_factory=list)


class Plugin(ABC):
    """Base class for all plugins."""

    def __init__(self, config: Config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.metadata = self._get_metadata()
        self._initialized = False

    @abstractmethod
    def _get_metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        pass

    @abstractmethod
    async def initialize(self):
        """Initialize the plugin."""
        pass

    @abstractmethod
    async def shutdown(self):
        """Shutdown the plugin."""
        pass

    @abstractmethod
    async def handle_command(self, command: str, context: Dict[str, Any]) -> Optional[str]:
        """Handle a voice command. Return response text or None."""
        pass

    def can_handle(self, command: str) -> bool:
        """Check if this plugin can handle the command."""
        command_lower = command.lower()
        return any(cmd in command_lower for cmd in self.metadata.commands)

    def get_intents(self) -> List[str]:
        """Get list of intents this plugin handles."""
        return self.metadata.intents


class PluginManager:
    """Manages plugin loading, initialization, and command routing."""

    def __init__(self, config: Config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.plugins: Dict[str, Plugin] = {}
        self.command_map: Dict[str, Plugin] = {}
        self.intent_map: Dict[str, Plugin] = {}

    async def load_plugins(self):
        """Load all enabled plugins."""
        # Load built-in plugins
        for plugin_name in self.config.plugins.builtin_plugins:
            await self._load_builtin_plugin(plugin_name)

        # Load external plugins from directories
        for plugin_dir in self.config.plugins.plugin_dirs:
            expanded_dir = Path(plugin_dir).expanduser()
            if expanded_dir.exists():
                await self._load_plugins_from_dir(expanded_dir)

        logger.info(f"Loaded {len(self.plugins)} plugins")

    async def _load_builtin_plugin(self, name: str):
        """Load a built-in plugin by name."""
        try:
            module = importlib.import_module(f"plugins.builtin.{name}")
            plugin_class = getattr(module, f"{name.title().replace('_', '')}Plugin")
            plugin = plugin_class(self.config, self.event_bus)
            await self.register_plugin(plugin)
        except Exception as e:
            logger.error(f"Failed to load built-in plugin {name}: {e}")

    async def _load_plugins_from_dir(self, plugin_dir: Path):
        """Load plugins from a directory."""
        for py_file in plugin_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Find Plugin subclasses
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, Plugin) and obj != Plugin:
                        plugin = obj(self.config, self.event_bus)
                        await self.register_plugin(plugin)
                        break
            except Exception as e:
                logger.error(f"Failed to load plugin from {py_file}: {e}")

    async def register_plugin(self, plugin: Plugin):
        """Register a plugin instance."""
        await plugin.initialize()
        self.plugins[plugin.metadata.name] = plugin

        # Map commands
        for cmd in plugin.metadata.commands:
            self.command_map[cmd.lower()] = plugin

        # Map intents
        for intent in plugin.metadata.intents:
            self.intent_map[intent.lower()] = plugin

        self._initialized = True
        logger.info(f"Registered plugin: {plugin.metadata.name} v{plugin.metadata.version}")

        # Emit event
        await self.event_bus.emit_async(Event(
            type=Events.PLUGIN_LOADED,
            data={"plugin": plugin.metadata.name, "version": plugin.metadata.version},
            source="plugin_manager"
        ))

    async def unregister_plugin(self, name: str):
        """Unregister a plugin."""
        if name in self.plugins:
            plugin = self.plugins[name]
            await plugin.shutdown()

            for cmd in plugin.metadata.commands:
                self.command_map.pop(cmd.lower(), None)
            for intent in plugin.metadata.intents:
                self.intent_map.pop(intent.lower(), None)

            del self.plugins[name]
            logger.info(f"Unregistered plugin: {name}")

            await self.event_bus.emit_async(Event(
                type=Events.PLUGIN_UNLOADED,
                data={"plugin": name},
                source="plugin_manager"
            ))

    async def handle_command(self, command: str, context: Dict[str, Any] = None) -> Optional[str]:
        """Route command to appropriate plugin."""
        context = context or {}
        command_lower = command.lower().strip()

        # Try exact command match first
        for cmd, plugin in self.command_map.items():
            if command_lower.startswith(cmd):
                try:
                    return await plugin.handle_command(command, context)
                except Exception as e:
                    logger.error(f"Plugin {plugin.metadata.name} error: {e}")
                    await self.event_bus.emit_async(Event(
                        type=Events.PLUGIN_ERROR,
                        data={"plugin": plugin.metadata.name, "error": str(e)},
                        source="plugin_manager"
                    ))
                    return f"Error in {plugin.metadata.name}: {e}"

        # Try intent-based matching
        for intent, plugin in self.intent_map.items():
            if intent in command_lower:
                try:
                    return await plugin.handle_command(command, context)
                except Exception as e:
                    logger.error(f"Plugin {plugin.metadata.name} error: {e}")
                    return f"Error in {plugin.metadata.name}: {e}"

        return None

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get plugin by name."""
        return self.plugins.get(name)

    def list_plugins(self) -> List[PluginMetadata]:
        """List all loaded plugins."""
        return [p.metadata for p in self.plugins.values()]

    async def shutdown_all(self):
        """Shutdown all plugins."""
        for plugin in self.plugins.values():
            try:
                await plugin.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down {plugin.metadata.name}: {e}")
        self.plugins.clear()
        self.command_map.clear()
        self.intent_map.clear()