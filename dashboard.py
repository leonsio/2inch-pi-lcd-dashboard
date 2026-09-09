"""Modular Raspberry Pi LCD dashboard controller.

Scheduling, rendering, and data collection are separated. The page layout is
configured in config.py and can later be switched by GPIO buttons without
changing the collectors or card renderers.
"""

import logging
import signal
import sys
import time

from lcd import LCD_2inch

import config as cfg
from dashboard_modules import CARD_BUILDERS, COLLECTORS
from dashboard_renderer import DashboardRenderer


disp = None
running = True
current_page = 0
state = {}


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


def set_page(index, logger=None):
    """Prepared navigation hook for future GPIO buttons."""
    global current_page
    all_pages = pages()
    if not all_pages:
        current_page = 0
        return
    current_page = index % len(all_pages)
    if logger:
        logger.info(
            "Page changed to %s (%d/%d)",
            all_pages[current_page].get("name", f"page-{current_page + 1}"),
            current_page + 1,
            len(all_pages),
        )


def next_page(logger=None):
    set_page(current_page + 1, logger)


def previous_page(logger=None):
    set_page(current_page - 1, logger)


def main():
    global disp

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

    disp = LCD_2inch.LCD_2inch()
    disp.Init()
    disp.clear()
    disp.bl_DutyCycle(int(getattr(cfg, "DISPLAY_BACKLIGHT", 100)))

    renderer = DashboardRenderer(disp, cfg, CARD_BUILDERS, logger)

    # Populate every data class immediately at startup.
    run_collectors("slow", logger)
    run_collectors("medium", logger)
    run_collectors("fast", logger)

    all_pages = pages()
    logger.info(
        "Configured pages: %s",
        ", ".join(page.get("name", f"page-{i + 1}") for i, page in enumerate(all_pages)),
    )

    next_fast = time.monotonic()
    next_medium = time.monotonic() + medium_interval
    next_slow = time.monotonic() + slow_interval

    try:
        while running:
            now = time.monotonic()
            rendered = False

            if now >= next_fast:
                run_collectors("fast", logger)
                next_fast = now + fast_interval
                rendered = True

            if now >= next_medium:
                run_collectors("medium", logger)
                next_medium = now + medium_interval
                rendered = True

            if now >= next_slow:
                run_collectors("slow", logger)
                next_slow = now + slow_interval
                rendered = True

            if rendered:
                page_list = pages()
                page = page_list[current_page % len(page_list)]
                try:
                    renderer.render_page(page, state)
                except Exception:
                    logger.exception("Display rendering failed")

            # Sleep only until the next fast tick. GPIO callbacks can later coexist
            # with this loop without a blocking ten-minute sleep.
            sleep_for = max(0.01, min(0.1, next_fast - time.monotonic()))
            time.sleep(sleep_for)

    finally:
        logger.info("Dashboard stopped")
        clear_screen()


if __name__ == "__main__":
    main()
