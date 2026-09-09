# Copy this file to config.py and enter your local values.
# config.py is intentionally excluded from Git.

# Dashboard behavior
SHOW_PER_CORE = False
REQUEST_TIMEOUT = 5
DISPLAY_BACKLIGHT = 100

# piVCCU / CCU XML API
PIVCCU_FALLBACK_IP = '192.168.2.155'
XML_RPC_TOKEN = 'YOUR_CCU_XML_API_TOKEN'

# Home Assistant REST API
# Example for Home Assistant OS 2026.8+: 'http://192.168.2.10'
# Example for port 8123: 'http://192.168.2.10:8123'
HOME_ASSISTANT_URL = 'http://homeassistant.local:8123'
HOME_ASSISTANT_TOKEN = 'YOUR_HOME_ASSISTANT_LONG_LIVED_ACCESS_TOKEN'

# AdGuard Home entities exposed by the Home Assistant AdGuard integration.
# Check Settings -> Devices & services -> AdGuard Home -> Entities for your exact IDs.
ADGUARD_PROTECTION_ENTITY = 'switch.adguard_home_protection'
ADGUARD_BLOCKED_RATIO_ENTITY = 'sensor.adguard_home_dns_queries_blocked_ratio'

# Display colors
C_BG = '#00129A'
C_T1 = '#000000'
C_T2 = '#c9c9c9'
C_T3 = '#c9c9c9'
C_OK = '#008000'
C_ERROR = '#FF0000'
