"""GPIO button input for dashboard navigation.

Uses gpiozero and BCM GPIO numbering. Each configured button posts a navigation
command to a queue; the dashboard main loop processes commands and performs all
rendering/navigation changes in its own thread.
"""

from queue import Queue

from gpiozero import Button


class DashboardButtons:
    ACTION_PREVIOUS = "previous"
    ACTION_NEXT = "next"
    ACTION_OK = "ok"
    ACTION_BACK = "back"

    def __init__(self, cfg, logger):
        self.cfg = cfg
        self.logger = logger
        self.events = Queue()
        self.buttons = []

    def _pin(self, name):
        value = getattr(self.cfg, name, None)
        if value in (None, "", False):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            self.logger.warning("Invalid GPIO pin for %s: %r", name, value)
            return None

    def _enqueue(self, action):
        self.events.put(action)

    def start(self):
        pull_up = bool(getattr(self.cfg, "BUTTON_PULL_UP", True))
        bounce_time = float(getattr(self.cfg, "BUTTON_BOUNCE_TIME", 0.08))

        mapping = (
            ("GPIO_BUTTON_PREVIOUS", self.ACTION_PREVIOUS),
            ("GPIO_BUTTON_NEXT", self.ACTION_NEXT),
            ("GPIO_BUTTON_OK", self.ACTION_OK),
            ("GPIO_BUTTON_BACK", self.ACTION_BACK),
        )

        configured = []
        used_pins = set()

        for config_name, action in mapping:
            pin = self._pin(config_name)
            if pin is None:
                continue
            if pin in used_pins:
                self.logger.error("GPIO %d configured more than once; skipping %s", pin, config_name)
                continue

            used_pins.add(pin)
            try:
                button = Button(pin, pull_up=pull_up, bounce_time=bounce_time)
                button.when_pressed = lambda action=action: self._enqueue(action)
                self.buttons.append(button)
                configured.append(f"{action}=GPIO{pin}")
            except Exception:
                self.logger.exception("Failed to configure %s on GPIO %d", action, pin)

        if configured:
            wiring = "GPIO->GND" if pull_up else "GPIO->3.3V"
            self.logger.info(
                "GPIO buttons active (%s, BCM numbering): %s",
                wiring,
                ", ".join(configured),
            )
        else:
            self.logger.info("GPIO buttons disabled: no navigation pins configured")

        return bool(self.buttons)

    def get_pending(self):
        actions = []
        while not self.events.empty():
            actions.append(self.events.get_nowait())
        return actions

    def close(self):
        for button in self.buttons:
            try:
                button.close()
            except Exception:
                self.logger.exception("Failed to close GPIO button")
        self.buttons.clear()
