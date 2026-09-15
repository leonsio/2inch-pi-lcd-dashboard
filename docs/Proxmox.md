# Proxmox module

The `proxmox` module reads Proxmox VE cluster resources through the REST API. It shows an overall VM/LXC status and can expose selected guests as individual cards.

## Enable the module

```yaml
proxmox:
  url: https://pve.example.lan:8006
  api_token_id: dashboard@pve!lcd-dashboard
  api_token_secret: YOUR_TOKEN_SECRET
  verify_ssl: false
  include_lxc: false
  vms: {}
```

## Parameters

| Parameter | Type | Default/example | Purpose |
| --- | --- | --- | --- |
| `url` | string | `https://pve.example.lan:8006` | Required Proxmox VE base URL. |
| `api_token_id` | string | `dashboard@pve!lcd-dashboard` | Required Proxmox API token ID. |
| `api_token_secret` | string | `YOUR_TOKEN_SECRET` | Required token secret. |
| `verify_ssl` | boolean | `false` | Verify the Proxmox HTTPS certificate. Enable when the certificate is trusted by the host. |
| `include_lxc` | boolean | `false` | Include LXC containers in the guest list/count. |
| `vms` | mapping | `{}` | Optional individual VM/LXC cards keyed by alias. |

The global `REQUEST_TIMEOUT` controls HTTP request timeout.

## API token

The module sends the standard Proxmox token header:

```text
Authorization: PVEAPIToken=<api_token_id>=<api_token_secret>
```

Use a dedicated read-only/least-privilege token that can read cluster resources and version information.

## Individual guest parameters

Each entry under `vms` creates `proxmox.<alias>`.

### Short form

```yaml
proxmox:
  url: https://pve.example.lan:8006
  api_token_id: dashboard@pve!lcd-dashboard
  api_token_secret: YOUR_TOKEN_SECRET
  vms:
    dockerhost: 101
```

The integer is the VMID. The title is generated from the alias.

### Long form

```yaml
proxmox:
  url: https://pve.example.lan:8006
  api_token_id: dashboard@pve!lcd-dashboard
  api_token_secret: YOUR_TOKEN_SECRET
  vms:
    homeassistant:
      vmid: 100
      title: Home Assistant
```

| Parameter | Required | Type | Example | Purpose |
| --- | --- | --- | --- | --- |
| `vmid` | yes | positive integer | `100` | Proxmox VM/LXC ID. |
| `title` | no | non-empty string | `Home Assistant` | Custom card title. |

Aliases use lowercase letters, digits and underscores.

## LXC behavior

When `include_lxc: false`, only QEMU VMs are returned by the module's filtering. A configured LXC card will therefore show `NOT FOUND`. Set `include_lxc: true` when LXC containers should be counted and available as individual cards.

## Available cards

| Card | Display |
| --- | --- |
| `proxmox` | Running guests versus total guests |
| `proxmox.<alias>` | State of a configured VM/LXC plus VMID and node |

Individual cards can display `RUNNING`, `STOPPED`, `NOT FOUND`, `AUTH`, `OFFLINE` or `CONFIG` depending on state.

## Polling

- **medium**: `/cluster/resources?type=vm`, guest count and individual guest state
- **slow**: `/version`

With the default scheduler this corresponds to 60 and 600 seconds.

## Complete example

```yaml
proxmox:
  url: https://192.168.1.10:8006
  api_token_id: dashboard@pve!lcd-dashboard
  api_token_secret: YOUR_TOKEN_SECRET
  verify_ssl: false
  include_lxc: true
  vms:
    homeassistant:
      vmid: 100
      title: Home Assistant
    dockerhost: 101
    mqtt_lxc:
      vmid: 200
      title: MQTT LXC

PAGES:
  - name: proxmox
    layout:
      row1cell1: proxmox
      row1cell2: proxmox.homeassistant
      row1cell3: proxmox.dockerhost
      row2cell1: proxmox.mqtt_lxc
```

## SSL

The registry default is currently `verify_ssl: false`, which is convenient for local Proxmox installations with self-signed certificates. For installations with a trusted certificate, explicitly use:

```yaml
proxmox:
  url: https://pve.example.com:8006
  api_token_id: dashboard@pve!lcd-dashboard
  api_token_secret: YOUR_TOKEN_SECRET
  verify_ssl: true
  include_lxc: false
  vms: {}
```

Real token values belong only in the local `config.yaml` and should not be committed.