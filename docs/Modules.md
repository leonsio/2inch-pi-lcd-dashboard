# Module documentation

Every dashboard module is enabled by adding its top-level YAML block to `config.yaml`. If a module block is absent, the module is not imported or polled.

This index links to the complete parameter reference for every module currently registered in `api/registry.py`.

| Module block | Documentation | Purpose |
| --- | --- | --- |
| `system` | [System.md](System.md) | Local CPU, RAM, swap, disk, load, uptime, temperature and frequency metrics |
| `network` | [Network.md](Network.md) | Local network, traffic, Wi-Fi, WAN, external IPv4 and reachability checks |
| `storage` | [Storage.md](Storage.md) | Multiple filesystems, free/used space, I/O and SMART |
| `services` | [Services.md](Services.md) | systemd running/active/failed counts and selected unit states |
| `power` | [Power.md](Power.md) | Shutdown and reboot actions |
| `pihole` | [PiHole.md](PiHole.md) | Pi-hole v6 blocking and query statistics |
| `pivccu` | [PiVCCU.md](PiVCCU.md) | OpenCCU/piVCCU XML API system notifications |
| `home_assistant` | [HomeAssistant.md](HomeAssistant.md) | Home Assistant status and arbitrary read-only entity cards |
| `adguard` | [AdGuard.md](AdGuard.md) | AdGuard summary through Home Assistant entities |
| `proxmox` | [Proxmox.md](Proxmox.md) | Proxmox cluster and VM/LXC status |
| `docker` | [Docker.md](Docker.md) | Docker daemon and container status through the Unix socket |
| `rest` | [REST.md](REST.md) | Generic read-only JSON REST cards |

## Basic module activation

Modules without required connection parameters can be activated with an empty mapping:

```yaml
system: {}
network: {}
storage: {}
services: {}
power: {}
```

Service integrations need their connection parameters, for example:

```yaml
home_assistant:
  url: http://homeassistant.local:8123
  token: YOUR_LONG_LIVED_ACCESS_TOKEN
  verify_ssl: true
  entities: {}
```

## Using a module card in a page

A module being enabled makes its static and configured dynamic cards available to `PAGES`.

```yaml
PAGES:
  - name: example
    layout:
      row1cell1: cpu_ring
      row1cell2: network
      row1cell3: storage.root_ring
```

Dynamic cards use the alias configured inside the module, for example:

```yaml
home_assistant:
  url: http://homeassistant.local:8123
  token: YOUR_LONG_LIVED_ACCESS_TOKEN
  verify_ssl: true
  entities:
    temperature:
      entity_id: sensor.living_room_temperature
      title: Living room

PAGES:
  - name: home
    layout:
      row1cell1: home_assistant.temperature
```

See each module document for all accepted parameters, default/example values, generated cards, polling intervals, dependencies and full YAML examples.

## Shared configuration

Module documentation also points out global settings that affect that module. Common examples are:

| Global setting | Default | Meaning |
| --- | ---: | --- |
| `REQUEST_TIMEOUT` | `5` | Network/API request timeout in seconds; also used as the local `systemctl` timeout by the services module |
| `FAST_INTERVAL` | `1` | Fast scheduler interval |
| `MEDIUM_INTERVAL` | `60` | Medium scheduler interval |
| `SLOW_INTERVAL` | `600` | Slow scheduler interval |
| `LOG_FAST_VALUES` | `false` | Log fast collector values |
| `LOG_MEDIUM_VALUES` | `true` | Log medium collector values |
| `LOG_SLOW_VALUES` | `true` | Log slow collector values |

The full non-module/global configuration remains documented in [Configuration.md](Configuration.md).