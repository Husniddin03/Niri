from .base import BasePlugin

class WindowOverviewPlugin(BasePlugin):
    name = "window_overview"
    description = "Toggles Niri overview when making a Closed Fist"

    def __init__(self, config=None):
        super().__init__(config)
        self.cooldown = float(self.config.get("cooldown", 1.2))
        self.trigger_gesture = self.config.get("trigger_gesture", "Closed_Fist")

    def on_event(self, event: dict):
        if not self.enabled:
            return

        gesture = event.get("gesture")
        confidence = event.get("confidence", 0.0)

        if gesture == self.trigger_gesture and confidence >= 0.70:
            if self.can_trigger():
                print(f"[window_overview] GESTURE {gesture} -> toggle-overview", flush=True)
                self.niri_action("toggle-overview")
