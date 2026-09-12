"""Power action dashboard cards and execution helpers."""

import subprocess


POWER_ACTIONS = {
    "shutdown": "poweroff",
    "reboot": "reboot",
}


def card_shutdown(state):
    return {
        "title": "SYSTEM",
        "value": "OFF",
        "detail": "OK: poweroff",
        "status": "warn",
    }


def card_reboot(state):
    return {
        "title": "SYSTEM",
        "value": "REBOOT",
        "detail": "OK: reboot",
        "status": "warn",
    }


def _run_pre_shutdown(cfg, logger, action):
    command = getattr(cfg, "pre_shutdown", None)
    if command in (None, "", False):
        return True

    logger.info("Running pre_shutdown before %s: %r", action, command)
    try:
        if isinstance(command, (list, tuple)):
            if not command:
                return True
            subprocess.run([str(part) for part in command], check=True)
        else:
            subprocess.run(str(command), shell=True, check=True)
    except Exception:
        logger.exception("pre_shutdown failed; aborting %s", action)
        return False
    return True


def execute_power_action(module_name, cfg, logger):
    """Run the configured pre-shutdown hook and then power off or reboot."""
    action = POWER_ACTIONS.get(str(module_name or "").lower())
    if not action:
        return False

    if not _run_pre_shutdown(cfg, logger, action):
        return False

    logger.warning("Executing system power action: %s", action)
    try:
        subprocess.run(["systemctl", action], check=True)
    except Exception:
        logger.exception("System power action failed: %s", action)
        return False
    return True


CARD_BUILDERS = {
    "shutdown": card_shutdown,
    "reboot": card_reboot,
}
