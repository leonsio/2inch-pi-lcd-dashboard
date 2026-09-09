# Copy this file to config.py and enter your local values.
# config.py is intentionally excluded from Git.

# -----------------------------------------------------------------------------
# Dashboard scheduler / behavior
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
HOME_ASSISTANT_URL = 'http://homeassistant.local:8123'
HOME_ASSISTANT_TOKEN = 'YOUR_HOME_ASSISTANT_LONG_LIVED_ACCESS_TOKEN'

# AdGuard Home is read through Home Assistant entities, not through a direct API.
ADGUARD_PROTECTION_ENTITY = 'switch.adguard_home_protection'
ADGUARD_BLOCKED_RATIO_ENTITY = 'sensor.adguard_home_dns_queries_blocked_ratio'

# -----------------------------------------------------------------------------
# Grid / pages / navigation
# -----------------------------------------------------------------------------
GRID_ROWS = 3
GRID_COLS = 3

# When GPIO buttons are added, bind them to these dashboard.py functions:
#   LEFT  -> navigate_previous()
#   RIGHT -> navigate_next()
#   OK    -> open_selected()
#   BACK  -> navigate_back()
#
# Browsing order is always row-major:
# row1cell1 -> row1cell2 -> row1cell3 -> row2cell1 -> ... -> row3cell3.
# Spanning cards (colspan/rowspan) count as one selectable block and the selection
# frame covers their complete area.
#
# A page with navigation='browse' participates in LEFT/RIGHT scrolling.
# A page with navigation='detail' is opened through target_page and is skipped
# while scrolling through normal pages.
#
# Set selectable=False on a block if it should be visible but skipped.
# Set target_page='page_name' to define what OK opens for a selected block.

SHOW_SELECTION_FRAME = True
C_SELECTED = '#0066FF'
SELECTED_BORDER_WIDTH = 4
SELECTED_INSET = 3

# Available modules:
#   cpu, ram, hdd, uptime, load
#   ip, hostname, network
#   pivccu, home_assistant (or ha), adguard

PAGES = [
    {
        'name': 'overview',
        'navigation': 'browse',
        'layout': {
            'row1cell1': {'module': 'cpu', 'target_page': 'system_detail'},
            'row1cell2': {'module': 'ram', 'target_page': 'system_detail'},
            'row1cell3': {'module': 'hdd', 'target_page': 'storage_detail'},
            'row2cell1': {'module': 'pivccu', 'target_page': 'services_detail'},
            'row2cell2': {'module': 'home_assistant', 'target_page': 'services_detail'},
            'row2cell3': {'module': 'adguard', 'target_page': 'services_detail'},
            'row3cell1': {'module': 'uptime', 'target_page': 'system_detail'},
            'row3cell2': {
                'module': 'network',
                'colspan': 2,
                'target_page': 'network_detail',
            },
        },
    },

    # A second normal page. Reaching the last block on overview and pressing
    # RIGHT again moves here and selects its first block. LEFT does the reverse.
    {
        'name': 'status',
        'navigation': 'browse',
        'layout': {
            'row1cell1': {'module': 'load', 'target_page': 'system_detail'},
            'row1cell2': {'module': 'ip', 'target_page': 'network_detail'},
            'row1cell3': {'module': 'hostname', 'target_page': 'network_detail'},
            'row2cell1': {'module': 'home_assistant', 'target_page': 'services_detail'},
            'row2cell2': {'module': 'adguard', 'target_page': 'services_detail'},
            'row2cell3': {'module': 'pivccu', 'target_page': 'services_detail'},
        },
    },

    # Detail pages are not part of normal LEFT/RIGHT scrolling. OK opens them;
    # BACK returns exactly to the page and block that opened the detail page.
    {
        'name': 'system_detail',
        'navigation': 'detail',
        'layout': {
            'row1cell1': 'cpu',
            'row1cell2': 'ram',
            'row1cell3': 'load',
            'row2cell1': 'uptime',
            'row2cell2': {'module': 'hostname', 'colspan': 2},
        },
    },
    {
        'name': 'storage_detail',
        'navigation': 'detail',
        'layout': {
            'row1cell1': {'module': 'hdd', 'colspan': 3},
            'row2cell1': 'uptime',
            'row2cell2': {'module': 'hostname', 'colspan': 2},
        },
    },
    {
        'name': 'network_detail',
        'navigation': 'detail',
        'layout': {
            'row1cell1': {'module': 'network', 'colspan': 3},
            'row2cell1': {'module': 'ip', 'colspan': 2},
            'row2cell3': 'hostname',
        },
    },
    {
        'name': 'services_detail',
        'navigation': 'detail',
        'layout': {
            'row1cell1': 'home_assistant',
            'row1cell2': 'adguard',
            'row1cell3': 'pivccu',
            'row2cell1': {'module': 'network', 'colspan': 2},
            'row2cell3': 'uptime',
        },
    },
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
