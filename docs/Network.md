# Network module

The `network` module displays local interface information and can optionally monitor WAN reachability, the public/external IPv4 address and arbitrary IPv4 hosts.

## Enable the module

The minimal configuration performs only local network monitoring and makes no external HTTP requests or pings:

```yaml
network: {}
```

## Top-level parameters

| Parameter | Type | Default | Purpose |
| --- | --- | --- | --- |
| `wan` | mapping | see below | Optional WAN reachability test. |
| `external_ipv4` | mapping | see below | Optional public IPv4 lookup. |
| `checks` | mapping | `{}` | Optional named IPv4 reachability checks. |

The global `NETWORK_INTERFACES` list controls which local interface is selected first:

```yaml
NETWORK_INTERFACES:
  - eth0
  - wlan0
```

The first listed interface with a usable IPv4 address is selected.

## WAN parameters

Default values:

```yaml
network:
  wan:
    enabled: false
    target: 1.1.1.1
    interval: medium
    timeout: 1.0
```

| Parameter | Type | Default/example | Purpose |
| --- | --- | --- | --- |
| `enabled` | boolean | `false` | Enable the WAN test and `wan` card. |
| `target` | IPv4 string | `1.1.1.1` | IPv4 address pinged with one ICMP request. |
| `interval` | string | `medium` | Scheduler group: `fast`, `medium` or `slow`. |
| `timeout` | number | `1.0` | Ping timeout in seconds. |

The WAN test validates IPv4 targets. Hostnames are not used for the ICMP target.

## External IPv4 parameters

Default values:

```yaml
network:
  external_ipv4:
    enabled: false
    url: https://api.ipify.org
    interval: slow
    verify_ssl: true
```

| Parameter | Type | Default/example | Purpose |
| --- | --- | --- | --- |
| `enabled` | boolean | `false` | Enable external IPv4 lookup and the `wan_ip`/`external_ipv4` cards. |
| `url` | HTTP(S) URL | `https://api.ipify.org` | Service expected to return a plain IPv4 address. |
| `interval` | string | `slow` | Scheduler group: `fast`, `medium` or `slow`. |
| `verify_ssl` | boolean | `true` | Verify HTTPS certificates. |

The shared `REQUEST_TIMEOUT` setting controls the HTTP lookup timeout. The response is accepted only when it parses as a valid IPv4 address.

## Custom reachability checks

Each entry below `checks` creates `network.<alias>`.

```yaml
network:
  checks:
    router:
      ip: 192.168.1.1
      title: Router
      interval: fast
      timeout: 1.0
```

| Parameter | Required | Type | Example/default | Purpose |
| --- | --- | --- | --- | --- |
| `ip` | yes | IPv4 string | `192.168.1.1` | IPv4 target to ping. |
| `title` | no | string | `Router` | Dashboard card title. Alias-derived title is used when omitted. |
| `interval` | no | string | `medium` | `fast`, `medium` or `slow`. |
| `timeout` | no | number | `1.0` | ICMP timeout in seconds. |

Aliases should use lowercase letters, digits and underscores. Identical targets with the same timeout within one scheduler cycle are de-duplicated into one ping.

## Scheduler intervals

`fast`, `medium` and `slow` refer to the global scheduler settings rather than hard-coded times:

```yaml
FAST_INTERVAL: 1
MEDIUM_INTERVAL: 60
SLOW_INTERVAL: 600
```

With these defaults the groups run every 1, 60 and 600 seconds. If the global values are changed, WAN/custom checks follow the changed schedule.

## Available cards

### Always available with `network: {}`

| Card | Display |
| --- | --- |
| `ip` | Local IPv4 and selected interface |
| `hostname` | Hostname and local IPv4 |
| `network` | Combined local IP, hostname, interface and link speed |
| `traffic` | Current RX/TX rates |
| `network_rx` | Current receive rate and total received data |
| `network_tx` | Current transmit rate and total transmitted data |
| `network_link` | Link state, speed and MTU |
| `wifi` | Wi-Fi signal in dBm and quality percent |
| `wifi_ring` | Wi-Fi quality as a ring |

### Optional cards

| Card | Required configuration | Display |
| --- | --- | --- |
| `wan` | `wan.enabled: true` | WAN `ONLINE`/`OFFLINE` and approximate ping time |
| `wan_ip` | `external_ipv4.enabled: true` | Public IPv4 address |
| `external_ipv4` | `external_ipv4.enabled: true` | Alias of `wan_ip` |
| `network.<alias>` | entry under `checks` | Target `ONLINE`/`OFFLINE` and approximate ping time |

## Complete example

```yaml
NETWORK_INTERFACES:
  - eth0
  - wlan0

network:
  wan:
    enabled: true
    target: 1.1.1.1
    interval: medium
    timeout: 1.0

  external_ipv4:
    enabled: true
    url: https://api.ipify.org
    interval: slow
    verify_ssl: true

  checks:
    router:
      ip: 192.168.1.1
      title: Router
      interval: fast
      timeout: 1.0
    dns:
      ip: 8.8.8.8
      title: Google DNS
      interval: medium
      timeout: 1.0

PAGES:
  - name: network
    layout:
      row1cell1: network
      row1cell2: wan
      row1cell3: wan_ip
      row2cell1: network.router
      row2cell2: network.dns
      row2cell3: network_link
      row3cell1: network_rx
      row3cell2: network_tx
      row3cell3: wifi_ring
```

## Requirements and behavior

ICMP checks use the operating system `ping` command. If it is unavailable, the affected card shows `N/A`/`PING`. Wi-Fi signal information is read from `/proc/net/wireless`; Ethernet interfaces or drivers that do not expose this information show `N/A` for Wi-Fi cards.