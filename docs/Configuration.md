# YAML configuration guide

The dashboard reads **`config.yaml` next to `dashboard.py`**. Python remains the application language; settings are YAML data.

## Contents

- [Getting started](#getting-started)
- [YAML rules and defaults](#yaml-rules-and-defaults)
- [Settings reference](#settings-reference)
- [Available modules](#available-modules)
- [Configuration examples](#configuration-examples)
- [Troubleshooting](#troubleshooting)

## Getting started

From the repository directory:

```shell
cp config.example.yaml config.yaml
nano config.yaml
sudo ./run.sh --prepare-only
venv/bin/python dashboard_config.py
sudo systemctl restart dashboard.service
```

`--prepare-only` installs dependencies (including PyYAML) and validates the
configuration without starting the dashboard. On a new installation, use
`sudo ./create_service.sh` after editing the file. For a foreground session use
`sudo ./run.sh`. Do not run both display instances simultaneously.

## YAML rules and defaults

- Use spaces for indentation, normally two per level; do not use tabs.
- Use `true` and `false` without quotes for booleans; use `null` for no value.
- Quote passwords, tokens, numeric-looking strings, and all `#RRGGBB` colors.
- Keys are case-sensitive. Unknown settings and duplicate keys are rejected.
- The root must be a mapping. An explicit `{}` loads all shipped defaults;
  an empty file is treated as a likely mistake and rejected.
- Missing top-level settings inherit from `config.example.yaml`. Treat that file
  as the shipped default template and edit your private `config.yaml` instead.
- Lists are replaced completely. In particular, specifying `PAGES` replaces
  **all** default pages; it does not merge their individual cells.
- YAML tags that construct Python objects are rejected. `!secret`, `!include`,
  environment-variable substitution and YAML merge keys (`<<`) are not supported.
- Relative `FONT_PATH` values resolve from the application directory. The default
  config file is also found there, independently of the current working directory.
- Changes take effect after a restart; there is no automatic reload.

`config.yaml` is ignored by Git. Keep actual credentials
in the local configuration, not in `config.example.yaml`.

## Settings reference

The complete, executable default template is [config.example.yaml](../config.example.yaml).
The tables below describe every supported top-level setting. Pixel settings are
reference sizes; the renderer may scale fonts and ring dimensions for the LCD.

### Display, polling and network

| Key | Default | Meaning |
| --- | --- | --- |
| `LCD_DEVICE` | `2inch` | `2inch`: landscape 320×240; `1inch69`: 280×240 |
| `DISPLAY_BACKLIGHT` | `100` | Brightness, integer 0–100 |
| `SHOW_PER_CORE` | `false` | `false`: average CPU 0–100%; `true`: summed per-core load |
| `FAST_INTERVAL` | `1` | Seconds between fast system updates; effective minimum 0.5 |
| `MEDIUM_INTERVAL` | `60` | Seconds between system/network/service updates; at least fast interval |
| `SLOW_INTERVAL` | `600` | Seconds between metadata updates; at least medium interval |
| `REQUEST_TIMEOUT` | `5` | Positive HTTP request timeout in seconds |
| `NETWORK_INTERFACES` | `[eth0, wlan0]` | Ordered interface names for IPv4 selection |
| `GRID_ROWS`, `GRID_COLS` | `3`, `3` | Positive integer logical grid dimensions |
| `PAGES` | Six example pages | Complete ordered page list; at least one `browse` page |

Summed CPU load can reach 400% on four cores; the limit depends on the actual
core count. The network card currently shows IP, hostname and interface, not
traffic rates. Changing `LCD_DEVICE` selects a driver and resolution; SPI and
LCD GPIO assignments remain in `lcd/lcdconfig.py`.

### Buttons and selection

| Key | Default | Meaning |
| --- | --- | --- |
| `BUTTONS_ENABLED` | `false` | Enable GPIO navigation and selection |
| `GPIO_BUTTON_PREVIOUS` | `19` | BCM GPIO, physical pin 35 |
| `GPIO_BUTTON_NEXT` | `26` | BCM GPIO, physical pin 37 |
| `GPIO_BUTTON_OK` | `20` | BCM GPIO, physical pin 38 |
| `GPIO_BUTTON_BACK` | `21` | BCM GPIO, physical pin 40 |
| `BUTTON_PULL_UP` | `true` | Connect buttons between GPIO and GND |
| `BUTTON_BOUNCE_TIME` | `0.08` | Debounce time in seconds |
| `SHOW_SELECTION_FRAME` | `true` | Draw selected block frame when buttons are enabled |
| `C_SELECTED` | `'#0066FF'` | Selection color |
| `SELECTED_BORDER_WIDTH` | `4` | Selection border width |
| `SELECTED_INSET` | `3` | Selection inset |
| `pre_shutdown` | `null` | Optional command before shutdown or reboot |

Pins use **BCM numbering**, not header numbers. A pin may be `null` to leave that
button unconfigured. Enabled buttons must use distinct pins. Check your wiring
for conflicts with LCD pins (default reset 22, DC 25, backlight 23) and SPI pins.
Physical pin 39 can serve as common ground. Without buttons the first browse
page stays visible; pages do not rotate automatically.

### Service connections

| Key | Default | Meaning |
| --- | --- | --- |
| `HOME_ASSISTANT_URL` | `http://homeassistant.local:8123` | Home Assistant base URL |
| `HOME_ASSISTANT_TOKEN` | Placeholder | Long-lived access token |
| `ADGUARD_PROTECTION_ENTITY` | `switch.adguard_home_protection` | HA protection switch |
| `ADGUARD_BLOCKED_RATIO_ENTITY` | `sensor.adguard_home_dns_queries_blocked_ratio` | HA blocked percentage sensor |
| `OPENCCU_IP` | `null` | Explicit OpenCCU address; null uses fallback below |
| `PIVCCU_FALLBACK_IP` | `192.168.2.155` | Legacy address alias |
| `XML_RPC_TOKEN` | Placeholder | OpenCCU XML API token |
| `PIHOLE_URL` | `''` | Pi-hole v6 base URL; empty disables Pi-hole polling |
| `PIHOLE_PASSWORD` | `''` | API/application password |
| `PIHOLE_VERIFY_SSL` | `true` | Validate Pi-hole HTTPS certificate |
| `PROXMOX_URL` | `''` | Base URL, usually including port 8006 |
| `PROXMOX_API_TOKEN_ID` | `''` | Full `user@realm!token-name` |
| `PROXMOX_API_TOKEN_SECRET` | `''` | Token secret |
| `PROXMOX_VERIFY_SSL` | `false` | Existing default accepts self-signed certificates; use true with trusted certificates |
| `PROXMOX_INCLUDE_LXC` | `false` | Include LXC guests in VM counts |

AdGuard is read through Home Assistant entities, not directly through an
AdGuard endpoint. Proxmox polling requires URL, token ID and secret. Removing
a card from `PAGES` only changes rendering: it does not disable collectors.
Home Assistant/OpenCCU collectors still run and may log unavailable-service
warnings even on a page containing only local system cards.

### Fonts and colors

| Key | Default | Meaning |
| --- | --- | --- |
| `FONT_PATH` | `./font/JetBrainsMono-Medium.ttf` | TTF font path |
| `FONT_TITLE`, `FONT_VALUE`, `FONT_DETAIL` | `15`, `24`, `13` | Classic card font sizes |
| `AUTO_FONT_SCALE` | `true` | Scale according to display dimensions |
| `FONT_REFERENCE_WIDTH`, `FONT_REFERENCE_HEIGHT` | `320`, `240` | Reference resolution |
| `FONT_SCALE_MIN`, `FONT_SCALE_MAX` | `0.60`, `1.50` | Font scale bounds |
| `TEXT_HORIZONTAL_PADDING` | `5` | Horizontal text padding |
| `FONT_MIN_TITLE`, `FONT_MIN_VALUE`, `FONT_MIN_DETAIL` | `8`, `10`, `7` | Minimum fitting sizes |
| `FONT_MIN_RING_VALUE`, `FONT_MIN_RING_TITLE` | `8`, `7` | Minimum ring fitting sizes |
| `C_SCREEN_BG`, `C_CELL_BG` | `'#FFFFFF'` | Screen and cell backgrounds |
| `C_GRID`, `C_T1` | `'#000000'` | Grid and normal value color |
| `C_T2`, `C_T3` | `'#666666'` | Secondary text; C_T3 retained but currently unused |
| `C_BG` | `'#00129A'` | Legacy color, currently unused by renderer |
| `C_OK`, `C_WARN`, `C_ERROR` | `'#008000'`, `'#D08000'`, `'#FF0000'` | Status colors |

### Rings

| Key | Default | Meaning |
| --- | --- | --- |
| `RING_TRACK_COLOR` | `'#D9D9D9'` | Unused ring portion |
| `RING_WIDTH`, `RING_PADDING`, `RING_TITLE_AREA` | `6`, `4`, `15` | Ring geometry |
| `RING_VALUE_FONT`, `RING_TITLE_FONT` | `17`, `13` | Ring font sizes |
| `RING_COLOR_LOW`, `RING_COLOR_MID`, `RING_COLOR_HIGH` | `'#008000'`, `'#E6C200'`, `'#FF0000'` | Gradient stops |
| `RING_COLOR_MIDPOINT` | `0.60` | Middle gradient stop, strictly between 0 and 1 |
| `TEMP_RING_MIN_C`, `TEMP_RING_MAX_C` | `0`, `85` | Empty/full temperature ring bounds |

Rings reuse collected system values; they do not introduce additional requests.
The arc starts at the top and progresses clockwise. Below the configured minimum
the temperature ring is empty, and at/above its maximum it is full.

### Logging

| Key | Default | Meaning |
| --- | --- | --- |
| `LOG_LEVEL` | `INFO` | DEBUG, INFO, WARNING, ERROR, CRITICAL (standard aliases accepted) |
| `LOG_FAST_VALUES` | `false` | Log fast collector values |
| `LOG_MEDIUM_VALUES`, `LOG_SLOW_VALUES` | `true`, `true` | Log slower collector values |
| `LOG_LOOP_TIMINGS` | `true` | Collector timings at DEBUG level |
| `LOG_BUTTON_EVENTS` | `true` | Log button presses and outcomes |

## Available modules

| Module | Information/action |
| --- | --- |
| `cpu`, `ram`, `hdd` | Classic CPU, memory and root-disk usage |
| `uptime`, `load` | Uptime and system load |
| `ip`, `hostname`, `network` | Individual or combined network identity |
| `home_assistant`, `ha` | Home Assistant availability/version |
| `openccu`, `pivccu` | OpenCCU service notifications; pivccu is an alias |
| `adguard` | AdGuard protection and blocked percentage from HA |
| `pihole` | Pi-hole v6 status |
| `proxmox` | Running/total guests and API status |
| `cpu_ring`, `ram_ring`, `disk_ring`, `hdd_ring`, `temp_ring` | Ring displays; hdd_ring aliases disk_ring |
| `shutdown`, `reboot` | Immediate host power action when OK is pressed |

## Configuration examples

Each fenced YAML example below is a **complete, valid top-level override file**.
You can use one as `config.yaml`; omitted options inherit shipped defaults.
To combine examples, merge their keys rather than pasting duplicate keys.
Combine layouts inside a single `PAGES` list. Replace sample service credentials
with your own. Validation checks configuration structure, not remote credentials,
module availability, installed fonts or actual wiring.

### 1. Compact local system page

```yaml
LCD_DEVICE: '2inch'
BUTTONS_ENABLED: false
PAGES:
  - name: system
    layout:
      row1cell1: cpu
      row1cell2: ram
      row1cell3: hdd
      row2cell1: load
      row2cell2: uptime
      row3cell1: {module: network, colspan: 3}
```

### 2. The 1.69-inch display

```yaml
LCD_DEVICE: '1inch69'
AUTO_FONT_SCALE: true
DISPLAY_BACKLIGHT: 65
FONT_VALUE: 22
FONT_DETAIL: 12
```

This uses the default six-page layout. Buttons remain disabled until explicitly
enabled. The same grid is automatically fitted to 280×240 pixels.

### 3. Rings mixed with classic cards

```yaml
PAGES:
  - name: rings
    layout:
      row1cell1: cpu_ring
      row1cell2: ram_ring
      row1cell3: disk_ring
      row2cell1: temp_ring
      row2cell2: home_assistant
      row2cell3: pihole
      row3cell1: {module: uptime, selectable: false}
      row3cell2: {module: network, colspan: 2}
TEMP_RING_MIN_C: 20
TEMP_RING_MAX_C: 85
RING_WIDTH: 7
RING_COLOR_MIDPOINT: 0.65
```

### 4. Buttons, two overview pages and a detail page

```yaml
BUTTONS_ENABLED: true
GPIO_BUTTON_PREVIOUS: 19
GPIO_BUTTON_NEXT: 26
GPIO_BUTTON_OK: 20
GPIO_BUTTON_BACK: 21
BUTTON_PULL_UP: true
BUTTON_BOUNCE_TIME: 0.08
PAGES:
  - name: overview
    navigation: browse
    layout:
      row1cell1: {module: cpu_ring, target_page: system_detail}
      row1cell2: {module: hostname, selectable: false}
      row1cell3: ram_ring
      row2cell1: {module: network, colspan: 3}
  - name: services
    navigation: browse
    layout:
      row1cell1: home_assistant
      row1cell2: openccu
      row1cell3: pihole
  - name: system_detail
    navigation: detail
    layout:
      row1cell1: cpu
      row1cell2: ram
      row1cell3: hdd
      row2cell1: {module: network, colspan: 3}
```

PREVIOUS/NEXT traverses selectable anchors top-left to bottom-right and wraps
between browse pages. The hostname remains visible but is skipped. OK on CPU
opens `system_detail`; BACK restores the original page and selection. Detail
pages are skipped during normal scrolling. PREVIOUS/NEXT and OK do not navigate
within a detail page; BACK returns. A selectable card without `target_page`
does nothing on OK unless it is a power-action card.

### 5. A large 2×2 block

```yaml
PAGES:
  - name: large
    layout:
      row1cell1: {module: cpu_ring, colspan: 2, rowspan: 2}
      row1cell3: ram_ring
      row2cell3: disk_ring
      row3cell1: {module: network, colspan: 3}
```

Configure only each block's top-left anchor. Do not populate cells covered by
its span. The selection frame covers the full block; it counts as one step.

### 6. A different grid

```yaml
GRID_ROWS: 2
GRID_COLS: 2
PAGES:
  - name: four_cards
    layout:
      row1cell1: cpu_ring
      row1cell2: ram_ring
      row2cell1: temp_ring
      row2cell2: uptime
```

When shrinking the grid, replace `PAGES` too so inherited layouts do not exceed
its bounds. For an informational-only card use `selectable: false`, not `null`.

### 7. Home Assistant and AdGuard

```yaml
HOME_ASSISTANT_URL: 'http://192.168.1.20:8123'
HOME_ASSISTANT_TOKEN: 'YOUR_LONG_LIVED_ACCESS_TOKEN'
ADGUARD_PROTECTION_ENTITY: 'switch.adguard_home_protection'
ADGUARD_BLOCKED_RATIO_ENTITY: 'sensor.adguard_home_dns_queries_blocked_ratio'
PAGES:
  - name: home
    layout:
      row1cell1: {module: home_assistant, colspan: 2}
      row1cell3: adguard
      row2cell1: {module: network, colspan: 3}
```

### 8. OpenCCU / piVCCU XML API

```yaml
OPENCCU_IP: '192.168.1.30'
XML_RPC_TOKEN: 'YOUR_CCU_XML_API_TOKEN'
PAGES:
  - name: automation
    layout:
      row1cell1: {module: openccu, colspan: 2}
      row1cell3: uptime
```

Use an address without `http://` or a path. The collector reads
`http://<address>/addons/xmlapi/systemNotification.cgi` using the token.
No local discovery takes place. `OPENCCU_IP: null` uses `PIVCCU_FALLBACK_IP`;
an empty string explicitly selects no address.

### 9. Pi-hole v6

```yaml
PIHOLE_URL: 'http://pi.hole'
PIHOLE_PASSWORD: 'YOUR_PIHOLE_APPLICATION_PASSWORD'
PIHOLE_VERIFY_SSL: true
PAGES:
  - name: dns
    layout:
      row1cell1: {module: pihole, colspan: 2}
      row1cell3: ip
```

Leave the password empty only if the API needs no password. Leave the URL empty
to disable Pi-hole polling. For an HTTPS endpoint with an intentionally accepted
self-signed certificate, set `PIHOLE_VERIFY_SSL: false`.

### 10. Proxmox including containers

```yaml
PROXMOX_URL: 'https://pve.example.lan:8006'
PROXMOX_API_TOKEN_ID: 'dashboard@pve!lcd-dashboard'
PROXMOX_API_TOKEN_SECRET: 'YOUR_TOKEN_SECRET'
PROXMOX_VERIFY_SSL: true
PROXMOX_INCLUDE_LXC: true
PAGES:
  - name: virtualization
    layout:
      row1cell1: {module: proxmox, colspan: 2}
      row1cell3: uptime
```

Do not append `/api2/json` to the URL. Counts exclude templates and include
stopped guests in the total. See [Proxmox.md](Proxmox.md) for API access and
status meanings.

### 11. Dark theme

```yaml
C_SCREEN_BG: '#101010'
C_CELL_BG: '#181818'
C_GRID: '#404040'
C_T1: '#FFFFFF'
C_T2: '#BBBBBB'
C_SELECTED: '#3399FF'
RING_TRACK_COLOR: '#404040'
RING_COLOR_LOW: '#40C060'
RING_COLOR_MID: '#E6C200'
RING_COLOR_HIGH: '#FF5555'
```

### 12. Polling and debugging

```yaml
FAST_INTERVAL: 2
MEDIUM_INTERVAL: 30
SLOW_INTERVAL: 300
REQUEST_TIMEOUT: 4
NETWORK_INTERFACES: [wlan0, eth0]
LOG_LEVEL: DEBUG
LOG_FAST_VALUES: false
LOG_MEDIUM_VALUES: true
LOG_SLOW_VALUES: true
LOG_LOOP_TIMINGS: true
LOG_BUTTON_EVENTS: true
```

Use `journalctl -u dashboard.service -f` to follow logs. Timings appear only at
DEBUG level. The scheduler enforces fast ≤ medium ≤ slow by raising the slower
intervals when necessary.

### 13. Shutdown/reboot with a preparation hook

```yaml
BUTTONS_ENABLED: true
pre_shutdown: ['/usr/local/bin/prepare-poweroff', '--flush']
PAGES:
  - name: power
    navigation: browse
    layout:
      row1cell1: shutdown
      row1cell2: reboot
      row1cell3: {module: uptime, selectable: false}
```

The command must exist on your Pi. OK runs the action **immediately without a
confirmation dialog**, under the dashboard service account (root with the
provided service). The hook runs first for both actions; failure aborts the
power action. A YAML list executes directly as an argument vector. A string,
such as `pre_shutdown: '/usr/local/bin/prepare-poweroff --flush'`, executes
through the shell. `null`, `false`, `''` or `[]` disables the hook.

## Troubleshooting

Validate without LCD/GPIO or network access:

```shell
venv/bin/python dashboard_config.py
venv/bin/python dashboard_config.py config.example.yaml
```

The optional path is for the **validator**. The running dashboard always uses
`config.yaml` in its application directory.

| Problem | Fix |
| --- | --- |
| Configuration missing | Create `config.yaml` from `config.example.yaml` |
| No module named yaml | Run `sudo ./run.sh --prepare-only` to update dependencies |
| YAML parse error | Check indicated line, indentation and quotes |
| Invalid boolean type | Use `false`, not the string `'false'` |
| Duplicate/unknown key | Keep one occurrence and use exact documented spelling |
| Block exceeds grid / overlapping blocks | Check anchors, spans and grid size |
| Unknown target page | Match `target_page` to a unique page `name` |
| Pages never change | Enable and wire buttons; there is no timed page rotation |
| Service shows AUTH/OFFLINE | Check endpoint, credentials, network and API permissions |
| Font cannot be loaded | Check `FONT_PATH` exists and is readable |

Validation does not display configured credentials and does not execute
`pre_shutdown`. It cannot verify the physical display; test rendering and
navigation on the Raspberry Pi after restarting the service.
