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

Keep the token secret only in the local `config.yaml`. `config.yaml` is excluded from Git by this project.

## 2. Add the configuration to config.yaml

```yaml
proxmox:
  # Base URL without /api2/json
  url: https://192.168.2.50:8006
  api_token_id: dashboard@pve!lcd-dashboard
  api_token_secret: YOUR_PROXMOX_API_TOKEN_SECRET
  # Use false only to accept an untrusted/self-signed certificate.
  verify_ssl: true
  # Include LXC containers as well as QEMU VMs.
  include_lxc: false
```

The global `REQUEST_TIMEOUT` setting is reused for Proxmox API requests.
Only a present `proxmox` block loads the module; remove it and its page cards
to disable polling. URL, token ID and secret are required.

## 3. Add the module to a page

Insert these snippets inside a page’s `layout` mapping. See the
[configuration guide](Configuration.md) for complete page examples.

Simple 1x1 rectangular block:

```yaml
row2cell3: proxmox
```

With button navigation:

```yaml
row2cell3:
  module: proxmox
  selectable: true
```

Informational only, so PREVIOUS/NEXT skips it:

```yaml
row2cell3:
  module: proxmox
  selectable: false
```

It can also use `colspan`, `rowspan`, and `target_page` like every other classic dashboard module.

## Status behaviour

| API state | Card value | Detail | Color |
| --- | --- | --- | --- |
| reachable and authenticated | `running/total VMs` | `ONLINE` | green |
| reachable but API token rejected | `ONLINE` | `AUTH` | warning |
| server/API unreachable | `OFFLINE` | empty | red |
| incomplete configuration block | Startup validation error | Missing required setting | — |

## Refresh intervals

The running/total VM count is collected in the dashboard's `MEDIUM_INTERVAL` loop. The Proxmox version is collected in the `SLOW_INTERVAL` loop and retained in state for future detail pages or extended cards.
