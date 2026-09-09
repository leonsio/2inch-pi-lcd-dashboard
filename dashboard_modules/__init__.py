"""Data collectors and card builders for TFT2 dashboard modules."""

from . import network, services, system

COLLECTORS = {
    "fast": [system.collect_fast],
    "medium": [system.collect_medium, network.collect_medium, services.collect_medium],
    "slow": [system.collect_slow, network.collect_slow, services.collect_slow],
}

CARD_BUILDERS = {}
CARD_BUILDERS.update(system.CARD_BUILDERS)
CARD_BUILDERS.update(network.CARD_BUILDERS)
CARD_BUILDERS.update(services.CARD_BUILDERS)
