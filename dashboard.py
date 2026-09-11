"""Modular Raspberry Pi LCD dashboard controller.

Scheduling, rendering, data collection, navigation, GPIO input, and LCD driver
selection are separated. GPIO navigation is enabled explicitly through config.py.
"""

import logging
import signal
import sys
import time

import config as cfg
from dashboard_buttons import DashboardButtons
from dashboard_modules import CARD_BUILDERS, COLLECTORS
from dashboard_navigation import DashboardNavigator
from dashboard_renderer import DashboardRenderer
from lcd.display_factory import create_display


disp = None
running = True
state = {}
navigator = None
buttons = None
render_requested = True
buttons_enabled = False


def setup_logging():
    level_name = str(getattr(cfg, "LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(handler)

    return logging.getLogger("dashboard")


def clear_screen():
    global disp
    if disp is None:
        return
    try:
        from PIL import Image
        image = Image.new("RGB", (disp.width, disp.height), color=(0, 0, 0))
        disp.ShowImage(image)
        disp.bl_DutyCycle(0)
        disp.module_exit()
    except Exception:
        logging.getLogger("dashboard").exception("Failed to clear display")


def shutdown_handler(signum, frame):
    global running
    logging.getLogger("dashboard").info("Shutdown signal received: %s", signum)
    running = False


def run_collectors(group, logger):
    started = time.monotonic()
    for collector in COLLECTORS[group]:
        try:
            collector(state, cfg, logger)
        except Exception:
            logger.exception("%s collector failed: %s", group.upper(), collector.__module__)
    elapsed_ms = (time.monotonic() - started) * 1000
    if getattr(cfg, "LOG_LOOP_TIMINGS", True):
        logger.debug("%s collectors finished in %.1f ms", group.upper(), elapsed_ms)


def pages():
    configured = getattr(cfg, "PAGES", None)
    if not configured:
        return [{
            "name": "default",
            "navigation": "browse",
            "layout": {
                "row1cell1": "cpu",
                "row1cell2": "ram",
                "row1cell3": "hdd",
                "row2cell1": "pivccu",
                "row2cell2": "home_assistant",
                "row2cell3": "adguard",
                "row3cell1": "uptime",
                "row3cell2": {"module": "network", "colspan": 2},
            },
        }]
    return configured


def _request_render():
    global render_requested
    render_requested = True


def navigate_previous():
    if buttons_enabled and navigator and navigator.move_previous():
        _request_render()
        return True
    return False


def navigate_next():
    if buttons_enabled and navigator and navigator.move_next():
        _request_render()
        return True
    return False


def open_selected():
    if buttons_enabled and navigator and navigator.open_selected():
        _request_render()
        return True
    return False


def navigate_back():
    if buttons_enabled and navigator and navigator.back():
        _request_render()
        return True
    return False


def _process_button_actions(logger):
    if not buttons_enabled or not buttons:
        return

    action_handlers = {
        DashboardButtons.ACTION_PREVIOUS: navigate_previous,
        DashboardButtons.ACTION_NEXT: navigate_next,
        DashboardButtons.ACTION_OK: open_selected,
        DashboardButtons.ACTION_BACK: navigate_back,
    }

    for action in buttons.get_pending():
        handler = action_handlers.get(action)
        if not handler:
            continue
        changed = handler()
        if getattr(cfg, "LOG_BUTTON_EVENTS", True):
            logger.info("BUTTON action=%s changed=%s", action, changed)


def next_page(logger=None):
    return navigate_next()


def previous_page(logger=None):
    return navigate_previous()


def main():
    global disp, navigator, buttons, render_requested, buttons_enabled

    logger = setup_logging()
    logger.info("Starting modular dashboard")

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    fast_interval = max(0.5, float(getattr(cfg, "FAST_INTERVAL", 1)))
    medium_interval = max(fast_interval, float(getattr(cfg, "MEDIUM_INTERVAL", 60)))
    slow_interval = max(medium_interval, float(getattr(cfg, "SLOW_INTERVAL", 600)))

    logger.info(
        "Scheduler intervals fast=%.1fs medium=%.1fs slow=%.1fs",
        fast_interval,
        medium_interval,
        slow_interval,
    )

    configured_lcd = getattr(cfg, "LCD_DEVICE", "2inch")
    disp, lcd_device = create_display(configured_lcd)
    state["lcd_device"] = lcd_device
    state["lcd_native_width"] = int(disp.width)
    state["lcd_native_height"] = int(disp.height)
    state["lcd_render_width"] = int(disp.height)
    state["lcd_render_height"] = int(disp.width)

    logger.info(
        "LCD device=%s native=%dx%d landscape=%dx%d",
        lcd_device,
        disp.width,
        disp.height,
        disp.height,
        disp.width,
    )

    disp.Init()
    disp.clear()
    disp.bl_DutyCycle(int(getattr(cfg, "DISPLAY_BACKLIGHT", 100)))

    renderer = DashboardRenderer(disp, cfg, CARD_BUILDERS, logger)
    navigator = DashboardNavigator(pages(), logger)

    buttons_enabled = bool(getattr(cfg, "BUTTONS_ENABLED", False))
    if buttons_enabled:
        buttons = DashboardButtons(cfg, logger)
        active = buttons.start()
        if active:
            logger.info("Button navigation enabled")
        else:
            logger.warning("Button navigation enabled, but no GPIO buttons could be initialized")
    else:
        logger.info("Button navigation disabled")

    run_collectors("slow", logger)
    run_collectors("medium", logger)
    run_collectors("fast", logger)

    all_pages = pages()
    logger.info(
        "Configured pages: %s",
        ", ".join(page.get("name", f"page-{i + 1}") for i, page in enumerate(all_pages)),
    )
    if buttons_enabled:
        logger.info("Navigation: PREVIOUS=previous NEXT=next OK=open BACK=return")

    next_fast = time.monotonic()
    next_medium = time.monotonic() + medium_interval
    next_slow = time.monotonic() + slow_interval
    render_requested = True

    try:
        while running:
            now = time.monotonic()
            data_changed = False

            _process_button_actions(logger)

            if now >= next_fast:
                run_collectors("fast", logger)
                next_fast = now + fast_interval
                data_changed = True

            if now >= next_medium:
                run_collectors("medium", logger)
                next_medium = now + medium_interval
                data_changed = True

            if now >= next_slow:
                run_collectors("slow", logger)
                next_slow = now + slow_interval
                data_changed = True

            if data_changed or render_requested:
                try:
                    selected_key = (
                        navigator.selected_key
                        if buttons_enabled
                        and navigator.mode == "browse"
                        and getattr(cfg, "SHOW_SELECTION_FRAME", True)
                        else None
                    )
                    renderer.render_page(
                        navigator.current_page,
                        state,
                        selected_key=selected_key,
                    )
                    render_requested = False
                except Exception:
                    logger.exception("Display rendering failed")

            sleep_for = max(0.01, min(0.05, next_fast - time.monotonic()))
            time.sleep(sleep_for)

    finally:
        if buttons:
            buttons.close()
        logger.info("Dashboard stopped")
        clear_screen()


if __name__ == "__main__":
    main()
