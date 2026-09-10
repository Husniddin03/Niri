from .base import BasePlugin

class WorkspaceNavPlugin(BasePlugin):
    name = "workspace_nav"
    description = "Switches Niri columns or workspaces via horizontal hand swipes"

    def __init__(self, config=None):
        super().__init__(config)
        self.cooldown = float(self.config.get("cooldown", 0.5))

    def on_event(self, event: dict):
        if not self.enabled:
            return

        dynamic_action = event.get("dynamic_action")
        if not dynamic_action:
            return

        if dynamic_action == "swipe_left" and self.can_trigger():
            print("[workspace_nav] SWIPE LEFT -> focus-column-right", flush=True)
            self.niri_action("focus-column-right")

        elif dynamic_action == "swipe_right" and self.can_trigger():
            print("[workspace_nav] SWIPE RIGHT -> focus-column-left", flush=True)
            self.niri_action("focus-column-left")
