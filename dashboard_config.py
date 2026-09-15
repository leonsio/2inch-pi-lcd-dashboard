"""Load declarative YAML settings without importing user Python or GPIO drivers."""

import argparse
import math
from pathlib import Path
import re
from types import SimpleNamespace

import yaml

ROOT = Path(__file__).resolve().parent


class ConfigError(ValueError):
    """Invalid or missing dashboard configuration."""


class _UniqueSafeLoader(yaml.SafeLoader):
    pass


def _mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str):
            raise ConfigError("Configuration keys must be strings")
        if key in result:
            raise ConfigError(f"Duplicate key: {key}")
        result[key] = loader.construct_object(value_node)
    return result


_UniqueSafeLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def _read(path):
    try:
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueSafeLoader)
    except (OSError, yaml.YAMLError) as error:
        # Parser errors can contain source snippets with credentials.
        mark = getattr(error, "problem_mark", None)
        location = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
        raise ConfigError(f"Cannot read YAML configuration {path}{location}") from None
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: expected a YAML mapping (use {{}} for defaults)")
    return data


def _require(condition, message):
    if not condition:
        raise ConfigError(message)


def _validate(data, defaults):
    for key, value in data.items():
        _require(key in defaults, f"Unknown configuration option: {key}")
        default = defaults[key]
        if key in ("PAGES", "pre_shutdown", "OPENCCU_IP") or key.startswith("GPIO_BUTTON_"):
            continue
        if isinstance(default, bool):
            valid = type(value) is bool
        elif isinstance(default, (int, float)):
            valid = type(value) in (int, float) and math.isfinite(value)
            if isinstance(default, int) and key not in ("FAST_INTERVAL", "MEDIUM_INTERVAL", "SLOW_INTERVAL", "REQUEST_TIMEOUT"):
                valid = valid and float(value).is_integer()
        else:
            valid = isinstance(value, type(default))
        _require(valid, f"Invalid type for {key}; use the type shown in config.example.yaml")
        if type(default) in (int, float):
            _require(value >= 0, f"{key} must be non-negative")
        if key.startswith("C_") or key.startswith("RING_COLOR_") and key != "RING_COLOR_MIDPOINT" or key == "RING_TRACK_COLOR":
            _require(bool(re.fullmatch(r"#[0-9a-fA-F]{6}", value)), f"{key} must be a quoted #RRGGBB color")
    for key in ("GRID_ROWS", "GRID_COLS", "REQUEST_TIMEOUT", "FONT_SCALE_MIN", "FONT_SCALE_MAX"):
        _require(data[key] > 0, f"{key} must be greater than zero")
    _require(0 <= data["DISPLAY_BACKLIGHT"] <= 100, "DISPLAY_BACKLIGHT must be 0..100")
    _require(0 < data["RING_COLOR_MIDPOINT"] < 1, "RING_COLOR_MIDPOINT must be between 0 and 1")
    _require(data["TEMP_RING_MIN_C"] < data["TEMP_RING_MAX_C"], "TEMP_RING_MAX_C must exceed TEMP_RING_MIN_C")
    _require(data["FONT_SCALE_MIN"] <= data["FONT_SCALE_MAX"], "FONT_SCALE_MIN must not exceed FONT_SCALE_MAX")
    _require(data["LOG_LEVEL"].upper() in ("DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL", "FATAL", "NOTSET"), "Invalid LOG_LEVEL")
    from lcd.display_factory import normalize_device_name, supported_devices
    _require(normalize_device_name(data["LCD_DEVICE"]) in supported_devices(), "LCD_DEVICE must select 2inch or 1inch69")
    interfaces = data["NETWORK_INTERFACES"]
    _require(all(isinstance(item, str) and item for item in interfaces), "NETWORK_INTERFACES must contain interface names")
    _require(data["OPENCCU_IP"] is None or isinstance(data["OPENCCU_IP"], str), "OPENCCU_IP must be a string or null")
    command = data["pre_shutdown"]
    _require(command is None or command is False or isinstance(command, str) or
             isinstance(command, list) and all(isinstance(part, str) and part for part in command),
             "pre_shutdown must be null, false, a command string or a list of strings")
    pins = []
    for key, pin in data.items():
        if key.startswith("GPIO_BUTTON_"):
            _require(pin is None or type(pin) is int and 0 <= pin <= 27, f"{key} must be a BCM GPIO 0..27 or null")
            if pin is not None:
                pins.append(pin)
    if data["BUTTONS_ENABLED"]:
        _require(len(pins) == len(set(pins)), "GPIO button pins must be unique")
    _validate_pages(data)


def _validate_pages(data):
    pages = data["PAGES"]
    _require(isinstance(pages, list) and bool(pages), "PAGES must be a non-empty list")
    names, targets = set(), []
    for page in pages:
        _require(isinstance(page, dict), "Each page must be a mapping")
        _require(set(page) <= {"name", "navigation", "layout"}, "Unknown page option")
        name = page.get("name")
        _require(isinstance(name, str) and bool(name), "Each page needs a name")
        _require(name not in names, f"Duplicate page name: {name}")
        names.add(name)
        _require(page.get("navigation", "browse") in ("browse", "detail"), f"{name}: invalid navigation")
        layout = page.get("layout")
        _require(isinstance(layout, dict), f"{name}: layout must be a mapping")
        occupied = set()
        for anchor, raw in layout.items():
            match = re.fullmatch(r"row([1-9][0-9]*)cell([1-9][0-9]*)", anchor)
            _require(match is not None, f"{name}: invalid cell name {anchor}")
            slot = {"module": raw} if isinstance(raw, str) else raw
            _require(isinstance(slot, dict), f"{name}/{anchor}: invalid block")
            _require(set(slot) <= {"module", "colspan", "rowspan", "selectable", "target_page"}, f"{name}/{anchor}: unknown block option")
            _require(isinstance(slot.get("module"), str) and bool(slot["module"]), f"{name}/{anchor}: module required")
            _require(type(slot.get("selectable", True)) is bool, f"{name}/{anchor}: selectable must be true or false")
            if "target_page" in slot:
                _require(isinstance(slot["target_page"], str), f"{name}/{anchor}: target_page must be a name")
                targets.append(slot["target_page"])
            rows, cols = slot.get("rowspan", 1), slot.get("colspan", 1)
            _require(type(rows) is int and rows > 0 and type(cols) is int and cols > 0, f"{name}/{anchor}: spans must be positive integers")
            row, col = map(int, match.groups())
            _require(row + rows - 1 <= data["GRID_ROWS"] and col + cols - 1 <= data["GRID_COLS"], f"{name}/{anchor}: block exceeds grid")
            cells = {(r, c) for r in range(row, row + rows) for c in range(col, col + cols)}
            _require(not occupied & cells, f"{name}/{anchor}: overlapping blocks")
            occupied.update(cells)
    _require(any(page.get("navigation", "browse") == "browse" for page in pages), "At least one browse page is required")
    _require(all(target in names for target in targets), "target_page refers to an unknown page")


def load_config(path=None):
    """Merge top-level overrides with shipped defaults; lists replace defaults."""
    path = Path(path) if path is not None else ROOT / "config.yaml"
    if not path.is_file():
        raise ConfigError(f"Configuration missing: {path}. Copy config.example.yaml to config.yaml.")
    defaults = _read(ROOT / "config.example.yaml")
    data = {**defaults, **_read(path)}
    _validate(data, defaults)
    font = Path(data["FONT_PATH"])
    if not font.is_absolute():
        data["FONT_PATH"] = str(ROOT / font)
    return SimpleNamespace(**data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate YAML configuration without accessing hardware or services")
    parser.add_argument("path", nargs="?", help="YAML file (default: config.yaml next to the application)")
    args = parser.parse_args()
    try:
        load_config(args.path)
    except ConfigError as error:
        parser.exit(2, f"Configuration error: {error}\n")
    print("Configuration valid")
