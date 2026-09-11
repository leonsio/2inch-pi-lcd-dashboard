# Copy this file to config.py and enter your local values.
# config.py is intentionally excluded from Git.

# -----------------------------------------------------------------------------
# Dashboard scheduler / behavior
# -----------------------------------------------------------------------------
SHOW_PER_CORE = False
REQUEST_TIMEOUT = 5
DISPLAY_BACKLIGHT = 100

# -----------------------------------------------------------------------------
# LCD device
# -----------------------------------------------------------------------------
# Select the physical LCD driver. The default keeps existing installations on
# the current 2-inch display.
#
# Supported values:
#   '2inch'   = LCD_2inch, native 240x320, dashboard landscape 320x240
#   '1inch69' = LCD_1inch69, native 240x280, dashboard landscape 280x240
#
# Aliases such as '2.0', 'lcd_2inch', '1.69' and 'lcd_1inch69' are accepted,
# but the canonical names above are recommended.
#
# IMPORTANT: display GPIO/SPI pins are NOT configured here. All supported LCDs
# use the same shared lcd/lcdconfig.py pin assignments. Selecting another LCD
# changes only the display controller driver and resolution.
LCD_DEVICE = '2inch'

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
# Current example wiring:
#   PREVIOUS -> BCM GPIO19 -> physical pin 35
#   NEXT     -> BCM GPIO26 -> physical pin 37
#   OK       -> BCM GPIO20 -> physical pin 38
#   BACK     -> BCM GPIO21 -> physical pin 40
# All buttons use physical pin 39 (GND) as their common ground.
GPIO_BUTTON_PREVIOUS = 19
GPIO_BUTTON_NEXT = 26
GPIO_BUTTON_OK = 20
GPIO_BUTTON_BACK = 21

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
# GRID_ROWS and GRID_COLS describe the logical matrix, not fixed pixel sizes.
# The renderer reads the selected LCD driver's native resolution and calculates
# the cell dimensions automatically.
#
# Examples with the default 3x3 matrix in landscape mode:
#   LCD_DEVICE='2inch'   -> 320x240 -> cells approx. 106.7x80 px
#   LCD_DEVICE='1inch69' -> 280x240 -> cells approx.  93.3x80 px
#
# Therefore the same PAGES/layout configuration can be used on both displays.
GRID_ROWS = 3
GRID_COLS = 3

# Selection styling is only used while BUTTONS_ENABLED=True.
SHOW_SELECTION_FRAME = True
C_SELECTED = '#0066FF'
SELECTED_BORDER_WIDTH = 4
SELECTED_INSET = 3

# -----------------------------------------------------------------------------
# PAGE NAVIGATION - QUICK GUIDE
# -----------------------------------------------------------------------------
# Every entry in PAGES is one screen/page and needs a unique 'name'.
#
# navigation='browse'
#   Normal dashboard page. PREVIOUS/NEXT moves through its selectable blocks.
#   At the last block NEXT continues on the next browse page. At the first block
#   PREVIOUS continues on the previous browse page. Detail pages are skipped.
#
# navigation='detail'
#   Sub-page opened with OK via target_page. It is not part of normal scrolling.
#   BACK returns to exactly the browse page/block from which it was opened.
#
# Navigation order on a browse page is always top-left -> bottom-right:
#
#   row1cell1 -> row1cell2 -> row1cell3
#       -> row2cell1 -> row2cell2 -> row2cell3
#       -> row3cell1 -> row3cell2 -> row3cell3
#
# Empty positions and non-selectable blocks are skipped.
# A colspan/rowspan block counts as ONE navigation step; its selection frame
# covers the complete large block.
#
# Available classic modules:
# cpu, ram, hdd, uptime, load, ip, hostname, network,
# pivccu, home_assistant (or ha), adguard, proxmox
#
# Additional ring/donut modules:
# cpu_ring, ram_ring, disk_ring, hdd_ring, temp_ring
#
# hdd_ring is an alias for disk_ring. The classic cpu/ram/hdd modules remain
# available and can be mixed freely with ring modules on the same page.

# -----------------------------------------------------------------------------
# SELECTABLE - IMPORTANT
# -----------------------------------------------------------------------------
# 'selectable' controls whether PREVIOUS/NEXT can put the selection frame on a
# block. It does NOT control whether the block itself is displayed.
#
# If selectable is omitted, the default is True:
#
#   'row1cell1': 'cpu'
#
# is equivalent to:
#
#   'row1cell1': {
#       'module': 'cpu',
#       'selectable': True,
#   }
#
# To DISPLAY a block but SKIP it during button navigation, use:
#
#   'row1cell1': {
#       'module': 'cpu',
#       'selectable': False,
#   }
#
# IMPORTANT: this is a Python configuration file. Use False, not "none".
# Python None is written as None, but selectable=None is NOT the setting for
# disabling selection. Use selectable=False explicitly.
#
# Example: hostname stays visible between IP and Home Assistant, but NEXT jumps
# directly from IP to Home Assistant because hostname has selectable=False:
#
#   'row1cell1': {'module': 'ip'},
#   'row1cell2': {'module': 'hostname', 'selectable': False},
#   'row1cell3': {'module': 'home_assistant'},
#
# A non-selectable block should normally have no target_page because OK can
# never be pressed while that block is selected. target_page on such a block is
# harmless, but cannot be reached through normal button navigation.
#
# selectable is mainly useful for informational blocks that should always be
# visible but should not act as menu entries, e.g. hostname, uptime, clock,
# labels, separators or other status-only information.

# -----------------------------------------------------------------------------
# TARGET_PAGE / OK BUTTON
# -----------------------------------------------------------------------------
# target_page defines which page OK opens. The value must exactly match the
# unique 'name' of another page in PAGES.
#
# Example selectable block opening the page named system_detail:
#
#   'row1cell1': {
#       'module': 'cpu',
#       'target_page': 'system_detail',
#   }
#
# Corresponding detail page:
#
#   {
#       'name': 'system_detail',
#       'navigation': 'detail',
#       'layout': {
#           'row1cell1': 'cpu',
#           'row1cell2': 'ram',
#       },
#   }
#
# A selectable block does NOT need a target_page. It can still be selected and
# highlighted, but pressing OK on it then does nothing:
#
#   'row1cell1': {
#       'module': 'uptime',
#       'selectable': True,
#   }

# -----------------------------------------------------------------------------
# BLOCK SIZE / COLSPAN / ROWSPAN
# -----------------------------------------------------------------------------
# Standard 1x1 block:
#   'row1cell1': 'cpu'
#
# Two columns wide (1x2):
#   'row3cell2': {
#       'module': 'network',
#       'colspan': 2,
#       'target_page': 'network_detail',
#   }
#
# Two rows high (2x1):
#   'row1cell1': {
#       'module': 'home_assistant',
#       'rowspan': 2,
#       'target_page': 'services_detail',
#   }
#
# Large 2x2 block:
#   'row1cell1': {
#       'module': 'home_assistant',
#       'colspan': 2,
#       'rowspan': 2,
#       'target_page': 'services_detail',
#   }
#
# Only the anchor cell (top-left position of the large block) is configured.
# Do not configure other blocks in cells occupied by its colspan/rowspan.

# -----------------------------------------------------------------------------
# RING / DONUT MODULE EXAMPLES
# -----------------------------------------------------------------------------
# Ring modules use the same collected system data as the classic modules; they
# do not add extra polling or collector load. The colored arc is the used/load
# portion, while the neutral ring remainder represents the available portion.
# The numeric value in the center uses the same dynamically calculated color.
#
# Basic usage:
#   'row1cell1': 'cpu_ring'
#   'row1cell2': 'ram_ring'
#   'row1cell3': 'disk_ring'
#   'row2cell1': 'temp_ring'
#
# Ring modules work with navigation options exactly like any other module:
#   'row1cell1': {
#       'module': 'cpu_ring',
#       'target_page': 'system_detail',
#   }
#
# They can also be made informational-only:
#   'row2cell1': {
#       'module': 'temp_ring',
#       'selectable': False,
#   }
#
# Example mixed page using both new and existing styles:
#   {
#       'name': 'rings',
#       'navigation': 'browse',
#       'layout': {
#           'row1cell1': 'cpu_ring',
#           'row1cell2': 'ram_ring',
#           'row1cell3': 'disk_ring',
#           'row2cell1': 'temp_ring',
#           'row2cell2': 'home_assistant',
#           'row2cell3': 'adguard',
#           'row3cell1': {'module': 'uptime', 'selectable': False},
#           'row3cell2': {'module': 'network', 'colspan': 2},
#       },
#   }

# -----------------------------------------------------------------------------
# COMPLETE NAVIGATION EXAMPLE
# -----------------------------------------------------------------------------
# In this example the selection order on overview is:
# CPU -> RAM -> HDD -> piVCCU -> Home Assistant -> AdGuard -> Network
# Uptime remains visible but is skipped because selectable=False.
# After Network, NEXT changes to the first selectable block of the 'status' page.
# OK on CPU/RAM opens system_detail; OK on Network opens network_detail.
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
            'row3cell1': {'module': 'uptime', 'selectable': False},
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
            'row1cell3': {'module': 'hostname', 'selectable': False},
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

# -----------------------------------------------------------------------------
# Ring / donut styling
# -----------------------------------------------------------------------------
# The ring is rendered clockwise from the top (12 o'clock).
# RING_TRACK_COLOR is the unused/available part of the ring.
RING_TRACK_COLOR = '#D9D9D9'
RING_WIDTH = 6
RING_PADDING = 4
RING_TITLE_AREA = 15
RING_VALUE_FONT = 17
RING_TITLE_FONT = 13

# Smooth color gradient for both the used ring segment and center value:
# low load -> green -> yellow -> red -> high load.
RING_COLOR_LOW = '#008000'
RING_COLOR_MID = '#E6C200'
RING_COLOR_HIGH = '#FF0000'
RING_COLOR_MIDPOINT = 0.60

# Temperature is converted into a 0..100% ring between these limits.
# Values below MIN show an empty ring; values at/above MAX show a full ring.
TEMP_RING_MIN_C = 0
TEMP_RING_MAX_C = 85
