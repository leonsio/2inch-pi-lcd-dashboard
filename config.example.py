# Copy this file to config.py and enter your local values.
# config.py is intentionally excluded from Git.

# -----------------------------------------------------------------------------
# TFT2 scheduler / behavior
# -----------------------------------------------------------------------------
SHOW_PER_CORE = False
REQUEST_TIMEOUT = 5
DISPLAY_BACKLIGHT = 100

# Three refresh classes. Collectors are executed once immediately at startup.
FAST_INTERVAL = 1       # CPU, RAM, CPU temperature
MEDIUM_INTERVAL = 60    # disk, uptime/load, IP, Home Assistant, AdGuard, piVCCU status
SLOW_INTERVAL = 600     # hostname and mostly static service metadata

# Logging to STDOUT
LOG_LEVEL = 'INFO'      # DEBUG, INFO, WARNING, ERROR
LOG_FAST_VALUES = False
LOG_MEDIUM_VALUES = True
LOG_SLOW_VALUES = True
LOG_LOOP_TIMINGS = True

# Network interfaces are checked from left to right.
NETWORK_INTERFACES = ['eth0', 'wlan0']

# -----------------------------------------------------------------------------
# piVCCU / CCU XML API
# -----------------------------------------------------------------------------
PIVCCU_FALLBACK_IP = '192.168.2.155'
XML_RPC_TOKEN = 'YOUR_CCU_XML_API_TOKEN'

# -----------------------------------------------------------------------------
# Home Assistant REST API
# -----------------------------------------------------------------------------
# Example: 'http://192.168.2.10:8123'
HOME_ASSISTANT_URL = 'http://homeassistant.local:8123'
HOME_ASSISTANT_TOKEN = 'YOUR_HOME_ASSISTANT_LONG_LIVED_ACCESS_TOKEN'

# AdGuard Home is read through Home Assistant entities, not through a direct API.
# Check Settings -> Devices & services -> AdGuard Home -> Entities for exact IDs.
ADGUARD_PROTECTION_ENTITY = 'switch.adguard_home_protection'
ADGUARD_BLOCKED_RATIO_ENTITY = 'sensor.adguard_home_dns_queries_blocked_ratio'

# -----------------------------------------------------------------------------
# TFT2 grid / pages
# -----------------------------------------------------------------------------
GRID_ROWS = 3
GRID_COLS = 3

# Available modules:
#   cpu, ram, hdd, uptime, load
#   ip, hostname, network
#   pivccu, home_assistant (or ha), adguard
#
# Simple placement:
#   'row1cell1': 'cpu'
#
# Optional horizontal/vertical spanning:
#   'row3cell2': {'module': 'network', 'colspan': 2}
#
# Future buttons only need to call next_page()/previous_page() in TFT2.py.
PAGES = [
    {
        'name': 'overview',
        'layout': {
            'row1cell1': 'cpu',
            'row1cell2': 'ram',
            'row1cell3': 'hdd',
            'row2cell1': 'pivccu',
            'row2cell2': 'home_assistant',
            'row2cell3': 'adguard',
            'row3cell1': 'uptime',
            'row3cell2': {'module': 'network', 'colspan': 2},
        },
    },

    # Example second page. Enable/change this whenever you want multiple pages.
    # {
    #     'name': 'system',
    #     'layout': {
    #         'row1cell1': 'cpu',
    #         'row1cell2': 'load',
    #         'row1cell3': 'ram',
    #         'row2cell1': 'hdd',
    #         'row2cell2': 'ip',
    #         'row2cell3': 'hostname',
    #         'row3cell1': 'home_assistant',
    #         'row3cell2': 'adguard',
    #         'row3cell3': 'pivccu',
    #     },
    # },
]

# -----------------------------------------------------------------------------
# Display styling
# -----------------------------------------------------------------------------
FONT_PATH = './font/JetBrainsMono-Medium.ttf'
FONT_TITLE = 15
FONT_VALUE = 24
FONT_DETAIL = 13

C_SCREEN_BG = '#FFFFFF'
C_CELL_BG = '#FFFFFF'
C_GRID = '#000000'
C_BG = '#00129A'
C_T1 = '#000000'
C_T2 = '#666666'
C_T3 = '#666666'
C_OK = '#008000'
C_WARN = '#D08000'
C_ERROR = '#FF0000'
