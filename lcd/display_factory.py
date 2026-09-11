"""LCD driver selection for the dashboard.

All display drivers use the shared lcdconfig.RaspberryPi implementation, so SPI
and GPIO pin assignments stay identical across devices. Only the controller
initialization and native resolution differ per display.
"""

from importlib import import_module


DISPLAY_DRIVERS = {
    "2inch": ("lcd.LCD_2inch", "LCD_2inch"),
    "1inch69": ("lcd.LCD_1inch69", "LCD_1inch69"),
}

DISPLAY_ALIASES = {
    "2": "2inch",
    "2.0": "2inch",
    "2in": "2inch",
    "2inch": "2inch",
    "lcd_2inch": "2inch",
    "1.69": "1inch69",
    "1.69inch": "1inch69",
    "1in69": "1inch69",
    "1inch69": "1inch69",
    "lcd_1inch69": "1inch69",
}


def normalize_device_name(device_name):
    name = str(device_name or "2inch").strip().lower()
    return DISPLAY_ALIASES.get(name, name)


def supported_devices():
    return tuple(DISPLAY_DRIVERS.keys())


def create_display(device_name="2inch"):
    """Create the configured LCD driver instance.

    The returned driver exposes native ``width``/``height``. The dashboard uses
    landscape mode and therefore renders to ``height x width`` pixels.
    """
    normalized = normalize_device_name(device_name)
    driver = DISPLAY_DRIVERS.get(normalized)
    if driver is None:
        supported = ", ".join(supported_devices())
        raise ValueError(
            f"Unsupported LCD_DEVICE {device_name!r}. Supported devices: {supported}"
        )

    module_name, class_name = driver
    module = import_module(module_name)
    display_class = getattr(module, class_name)
    return display_class(), normalized
