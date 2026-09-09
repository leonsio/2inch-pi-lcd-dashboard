# Copy this file to config.py and enter your local values.
# config.py is intentionally excluded from Git.

# -----------------------------------------------------------------------------
# Dashboard scheduler / behavior
# -----------------------------------------------------------------------------
SHOW_PER_CORE = False
REQUEST_TIMEOUT = 5
DISPLAY_BACKLIGHT = 100

FAST_INTERVAL = 1
MEDIUM_INTERVAL = 60
SLOW_INTERVAL = 600

LOG_LEVEL = 'INFO'
LOG_FAST_VALUES = False
LOG_MEDIUM_VALUES = True
LOG_SLOW_VALUES = True
LOG_LOOP_TIMINGS = True
LOG_BUTTON_EVENTS = True

NETWORK_INTERFACES = ['eth0', 'wlan0']

# -----------------------------------------------------------------------------
# GPIO navigation buttons
# -----------------------------------------------------------------------------
# Master switch. When False:
#   - GPIO buttons are not initialized
#   - navigation input is disabled
#   - no selection frame is displayed
# When True, configured GPIO buttons enable block navigation.
BUTTONS_ENABLED = False

# BCM GPIO numbering, not physical header pin numbers.
# With BUTTON_PULL_UP=True each button is wired: BCM GPIO -> button -> GND.
GPIO_BUTTON_PREVIOUS = None   # e.g. 5
GPIO_BUTTON_NEXT = None       # e.g. 6
GPIO_BUTTON_OK = None         # e.g. 16
GPIO_BUTTON_BACK = None       # e.g. 20

BUTTON_PULL_UP = True
BUTTON_BOUNCE_TIME = 0.08

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

ADGUARD_PROTECTION_ENTITY = 'switch.adguard_home_protection'
ADGUARD_BLOCKED_RATIO_ENTITY = 'sensor.adguard_home_dns_queries_blocked_ratio'

# -----------------------------------------------------------------------------
# Grid / pages / navigation
# -----------------------------------------------------------------------------
GRID_ROWS = 3
GRID_COLS = 3

# Selection styling is only used while BUTTONS_ENABLED=True.
SHOW_SELECTION_FRAME = True
C_SELECTED = '#0066FF'
SELECTED_BORDER_WIDTH = 4
SELECTED_INSET = 3

# Available modules:
# cpu, ram, hdd, uptime, load, ip, hostname, network,
# pivccu, home_assistant (or ha), adguard
#
# Browse order is row-major. Spanning cards count once and their complete area
# is selected. target_page defines the detail page opened with OK.
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
