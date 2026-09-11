# Proxmox dashboard module

The dashboard module `proxmox` reads a local Proxmox VE server through its REST API and renders a normal rectangular dashboard card.

Example display:

```text
PROXMOX
3/5 VMs
ONLINE
```

- `3` = running VMs
- `5` = total VMs
- stopped VMs are included in the total
- templates are ignored
- by default only QEMU virtual machines are counted
- LXC containers can optionally be included

## 1. Create a read-only API token

Use a dedicated Proxmox user/API token for the dashboard rather than a root credential. A read-only `PVEAuditor` permission on `/` is sufficient for a simple monitoring token.

The token ID passed to the dashboard must include user, realm and token name, for example:

```text
dashboard@pve!lcd-dashboard
```

Keep the token secret only in the local `config.py`. `config.py` is excluded from Git by this project.

## 2. Add the configuration to config.py

```python
# -----------------------------------------------------------------------------
# Proxmox VE REST API
# -----------------------------------------------------------------------------
# Base URL of the local Proxmox web/API service. Do not append /api2/json.
PROXMOX_URL = 'https://192.168.2.50:8006'

# Format: user@realm!token-name
PROXMOX_API_TOKEN_ID = 'dashboard@pve!lcd-dashboard'
PROXMOX_API_TOKEN_SECRET = 'YOUR_PROXMOX_API_TOKEN_SECRET'

# Local Proxmox installations often use a self-signed certificate.
# False accepts that certificate. True requires normal certificate validation.
PROXMOX_VERIFY_SSL = False

# False = count QEMU virtual machines only.
# True  = count QEMU VMs and LXC containers together.
PROXMOX_INCLUDE_LXC = False
```

The global `REQUEST_TIMEOUT` setting is reused for Proxmox API requests.

## 3. Add the module to a page

Simple 1x1 rectangular block:

```python
'row2cell3': 'proxmox',
```

With button navigation:

```python
'row2cell3': {
    'module': 'proxmox',
    'selectable': True,
},
```

Informational only, so PREVIOUS/NEXT skips it:

```python
'row2cell3': {
    'module': 'proxmox',
    'selectable': False,
},
```

It can also use `colspan`, `rowspan`, and `target_page` like every other classic dashboard module.

## Status behaviour

| API state | Card value | Detail | Color |
| --- | --- | --- | --- |
| reachable and authenticated | `running/total VMs` | `ONLINE` | green |
| reachable but API token rejected | `ONLINE` | `AUTH` | warning |
| server/API unreachable | `OFFLINE` | empty | red |
| configuration missing | `CONFIG` | `NOT SET` | warning |

## Refresh intervals

The running/total VM count is collected in the dashboard's `MEDIUM_INTERVAL` loop. The Proxmox version is collected in the `SLOW_INTERVAL` loop and retained in state for future detail pages or extended cards.
