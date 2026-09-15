# Network monitoring

The `network` module provides local interface data and optional WAN/public IPv4 monitoring.

## Basic local monitoring

```yaml
network: {}
```

This keeps the existing cards:

- `network`
- `ip`
- `hostname`
- `traffic`
- `network_rx`
- `network_tx`
- `network_link`
- `wifi`
- `wifi_ring`

## Scheduler intervals

WAN and reachability checks use symbolic interval names:

| Value | Scheduler |
| --- | --- |
| `fast` | `FAST_INTERVAL` |
| `medium` | `MEDIUM_INTERVAL` |
| `slow` | `SLOW_INTERVAL` |

With the shipped defaults these correspond to 1, 60 and 600 seconds. If the global scheduler intervals are changed, the network checks automatically follow those values.

## WAN status

Enable WAN monitoring by pinging a public IPv4 address:

```yaml
network:
  wan:
    enabled: true
    target: 1.1.1.1
    interval: medium
    timeout: 1.0
```

This creates the card:

```text
wan
```

The card shows `ONLINE`, `OFFLINE`, `WAIT` or `N/A`. When online it also displays the target and approximate round-trip time.

The WAN test intentionally uses an IPv4 address instead of a hostname so DNS failure and Internet reachability remain separate failure modes.

## External/public IPv4

The public IPv4 address can be read from an HTTP(S) endpoint that returns a plain IPv4 address:

```yaml
network:
  external_ipv4:
    enabled: true
    url: https://api.ipify.org
    interval: slow
    verify_ssl: true
```

This creates two aliases for the same card:

```text
wan_ip
external_ipv4
```

The response is validated as an IPv4 address before it is displayed. Errors are shown as `OFFLINE`, `AUTH`, `HTTP NNN` or `INVALID`.

The URL is configurable, so a different public-IP service or an internally hosted endpoint can be used instead.

## Custom IP reachability checks

Any number of IPv4 addresses can be monitored:

```yaml
network:
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

    remote_site:
      ip: 203.0.113.10
      title: Remote Site
      interval: slow
      timeout: 2.0
```

Each entry creates a card named `network.<alias>`:

```text
network.router
network.dns
network.remote_site
```

The cards show `ONLINE` or `OFFLINE` and include the tested address and approximate latency when reachable.

## Combined example

```yaml
network:
  wan:
    enabled: true
    target: 1.1.1.1
    interval: fast
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
      title: DNS
      interval: medium
      timeout: 1.0

PAGES:
  - name: connectivity
    layout:
      row1cell1: wan
      row1cell2: wan_ip
      row1cell3: network.router
      row2cell1: network.dns
      row2cell2: network_link
      row2cell3: wifi_ring
      row3cell1: {module: traffic, colspan: 3}
```

## Implementation notes

- Reachability checks use the system `ping` executable and one ICMP echo request.
- If `ping` is not installed or executable, the card shows `N/A` rather than treating the host as offline.
- Identical ping targets with the same timeout within one scheduler cycle are de-duplicated. For example, a WAN check and a named check against `1.1.1.1` result in only one ping per cycle.
- `timeout` is interpreted in seconds and is clamped internally to a safe range.
- External IPv4 retrieval uses the global `REQUEST_TIMEOUT` setting.
- No network monitoring option performs write operations against remote systems.
