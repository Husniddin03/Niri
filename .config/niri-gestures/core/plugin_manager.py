import os
import sys
import importlib
import json

class PluginManager:
    def __init__(self, plugins_dir: str, config_file: str):
        self.plugins_dir = plugins_dir
        self.config_file = config_file
        self.plugins = []
        self.config = self.load_config()

        if self.plugins_dir not in sys.path:
            sys.path.insert(0, os.path.dirname(self.plugins_dir))

    def load_config(self) -> dict:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[PluginManager] Error loading config: {e}")
        return {}

    def discover_and_load(self):
        self.plugins = []
        plugins_config = self.config.get("plugins", {})

        for fname in os.listdir(self.plugins_dir):
            if fname.endswith(".py") and not fname.startswith("__") and fname != "base.py":
                module_name = f"plugins.{fname[:-3]}"
                try:
                    module = importlib.import_module(module_name)
                    # Find plugin class inside module
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type)
                            and hasattr(attr, "name")
                            and attr.name != "base"
                            and attr_name.endswith("Plugin")
                        ):
                            p_cfg = plugins_config.get(attr.name, {})
                            instance = attr(p_cfg)
                            self.plugins.append(instance)
                            print(f"[PluginManager] Loaded plugin: '{attr.name}' (enabled={instance.enabled})")
                except Exception as e:
                    print(f"[PluginManager] Failed to load {module_name}: {e}")

    def dispatch(self, event: dict):
        if not event:
            return
        for plugin in self.plugins:
            if plugin.enabled:
                try:
                    plugin.on_event(event)
                except Exception as e:
                    print(f"[PluginManager] Error in plugin {plugin.name}: {e}")
