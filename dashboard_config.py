"""Load declarative YAML settings without importing user Python or GPIO drivers."""

import argparse
import math
from pathlib import Path
import re
from types import SimpleNamespace

import yaml
from api.registry import MODULES, available_cards

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
        if key in MODULES:
            continue
        _require(key in defaults, f"Unknown configuration option: {key}")
        default = defaults[key]
        if key in ("PAGES", "pre_shutdown") or key.startswith("GPIO_BUTTON_"):
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


def _validate_modules(data):
    for name, (_, defaults, _) in MODULES.items():
        if name not in data:
            continue
        block = data[name]
        _require(isinstance(block, dict), f"{name} must be a mapping; remove the block to disable it")
        _require(set(block) <= set(defaults), f"{name}: unknown option")
        block = {**defaults, **block}
        for key, value in block.items():
            _require(isinstance(value, type(defaults[key])), f"{name}.{key}: invalid type")
        for key in ("url", "token", "ip", "api_token_id", "api_token_secret"):
            if key in block:
                _require(bool(block[key].strip()), f"{name}.{key} is required")
        if "url" in block:
            from urllib.parse import urlsplit
            try:
                url = urlsplit(block["url"])
                valid = url.scheme in ("http", "https") and bool(url.hostname) and not url.query and not url.fragment and not url.username
            except ValueError:
                valid = False
            _require(valid, f"{name}.url must be an HTTP(S) base URL without credentials, query or fragment")
        data[name] = block
    _require("adguard" not in data or "home_assistant" in data, "adguard requires a home_assistant block")
    for name, item in data.get("home_assistant", {}).get("entities", {}).items():
        _require(bool(re.fullmatch(r"[a-z0-9_]+", name)), "Home Assistant card names must use lowercase letters, digits and underscores")
        _require(isinstance(item, dict), f"home_assistant.entities.{name} must be a mapping")
        _require(set(item) <= {"entity_id", "title", "attribute", "precision", "unit", "state_labels", "detail"}, f"home_assistant.entities.{name}: unknown option")
        _require(isinstance(item.get("entity_id"), str) and bool(re.fullmatch(r"[a-z0-9_]+\.[a-z0-9_]+", item["entity_id"])), f"home_assistant.entities.{name}: entity_id required")
        for key in ("title", "attribute", "unit", "detail"):
            if key in item:
                _require(isinstance(item[key], str), f"home_assistant.entities.{name}.{key} must be a string")
        if "precision" in item:
            _require(type(item["precision"]) is int and 0 <= item["precision"] <= 10, f"home_assistant.entities.{name}.precision must be 0..10")
        labels = item.get("state_labels", {})
        _require(isinstance(labels, dict) and all(isinstance(v, str) for v in labels.values()), f"home_assistant.entities.{name}.state_labels must map quoted strings to strings")
    for key, value in data.get("adguard", {}).items():
        _require(bool(re.fullmatch(r"[a-z0-9_]+\.[a-z0-9_]+", value)), f"adguard.{key} must be an entity ID")


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
            _require(slot["module"].lower() in available_cards(data), f"{name}/{anchor}: unknown card or missing module configuration block: {slot['module']}")
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
    """Merge global defaults; module blocks are enabled only when present."""
    path = Path(path) if path is not None else ROOT / "config.yaml"
    if not path.is_file():
        raise ConfigError(f"Configuration missing: {path}. Copy config.example.yaml to config.yaml.")
    defaults = _read(ROOT / "config.example.yaml")
    overrides = _read(path)
    data = {**{k: v for k, v in defaults.items() if k not in MODULES}, **overrides}
    _validate_modules(data)
    if "PAGES" not in overrides:
        # Shipped pages adapt to enabled modules. Explicit layouts are validated.
        cards = available_cards(data)
        for page in data["PAGES"]:
            page["layout"] = {key: slot for key, slot in page["layout"].items()
                              if (slot if isinstance(slot, str) else slot["module"]).lower() in cards}
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
