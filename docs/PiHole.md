# Pi-hole module

The `pihole` module reads Pi-hole v6 status and statistics through the Pi-hole REST API.

## Enable the module

```yaml
pihole:
  url: http://pi.hole
  password: ''
  verify_ssl: true
```

The module is loaded only when the `pihole` block exists.

## Parameters

| Parameter | Type | Example/default | Purpose |
| --- | --- | --- | --- |
| `url` | string | `http://pi.hole` | Required Pi-hole base URL. Do not append `/api`. |
| `password` | string | `''` | Pi-hole API/web password. Leave empty when the Pi-hole API does not require a password. |
| `verify_ssl` | boolean | `true` | Verify the HTTPS certificate. Set `false` only for a deliberately trusted self-signed/local setup. |

The shared global `REQUEST_TIMEOUT` controls HTTP request timeout; the default is `5` seconds.

## Polling

Pi-hole status and statistics are refreshed in the **medium** scheduler group. With the default configuration this means every 60 seconds (`MEDIUM_INTERVAL: 60`).

The integration reads:

- `/api/dns/blocking`
- `/api/stats/summary`
- `/api/auth` when a password is configured

A Pi-hole v6 session ID is cached and automatically renewed once after an HTTP 401 response.

## Available cards

`pihole` and `pi_hole` are aliases for the same card.

The card normally shows the blocked-query percentage. Its detail line shows blocked queries versus total queries. If blocking is disabled, it displays `DISABLED`; API/authentication failures are shown as an error state.

## Example with HTTP

```yaml
pihole:
  url: http://192.168.1.2
  password: 'YOUR_PIHOLE_PASSWORD'
  verify_ssl: true

PAGES:
  - name: services
    layout:
      row1cell1: pihole
```

## Example with local HTTPS and a self-signed certificate

```yaml
pihole:
  url: https://pihole.example.lan
  password: 'YOUR_PIHOLE_PASSWORD'
  verify_ssl: false
```

Use `verify_ssl: false` only when certificate verification is intentionally not possible. A valid certificate with `verify_ssl: true` is preferred.