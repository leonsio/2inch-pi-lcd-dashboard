# Generic REST module

The `rest` module exposes values from arbitrary JSON HTTP endpoints as dashboard
cards. It is intentionally read-only: polling uses HTTP GET only.

## Basic configuration

```yaml
rest:
  endpoints:
    temperature:
      url: http://192.168.1.50/api/status
      interval: 60
      path: sensors.temperature
      title: Temperature
      unit: '°C'
      precision: 1

PAGES:
  - name: api
    layout:
      row1cell1: rest.temperature
```

Each entry under `rest.endpoints` creates a card named `rest.<alias>`.
Aliases may contain lowercase letters, digits and underscores.

## Polling interval

`interval` controls how often the endpoint is assigned to a dashboard polling
cycle. Supported values are deliberately restricted to:

- `1` - fast cycle, normally every second
- `60` - medium cycle, normally every minute; this is the default
- `600` - slow cycle, normally every ten minutes

These values map to the dashboard's existing `FAST_INTERVAL`, `MEDIUM_INTERVAL`
and `SLOW_INTERVAL` scheduler groups. With the shipped defaults those groups run
at exactly 1, 60 and 600 seconds. If the global scheduler intervals are changed,
the corresponding REST polling cycle changes with them.

Several REST cards with the same URL, headers, SSL setting and interval share one
HTTP request during that cycle. This allows multiple values from one JSON response
without repeatedly querying the remote service.

## JSON paths

`path` selects the value to display. Use dot-separated object keys. Numeric path
segments address list indexes.

Example response:

```json
{
  "device": {"name": "Boiler"},
  "sensors": {
    "temperature": 54.27,
    "channels": [12.1, 13.5]
  }
}
```

Examples:

- `sensors.temperature` -> `54.27`
- `device.name` -> `Boiler`
- `sensors.channels.0` -> `12.1`
- an empty or omitted `path` selects the complete JSON response

A missing path is shown as `PATH` on the card.

## Card options

| Option | Default | Meaning |
| --- | --- | --- |
| `url` | required | Complete HTTP or HTTPS GET URL; query parameters are allowed |
| `interval` | `60` | Polling cycle: `1`, `60` or `600` seconds |
| `path` | `''` | Dot-separated JSON value path |
| `title` | alias | Card title |
| `unit` | `''` | Unit appended to the displayed value |
| `precision` | unchanged | Decimal places for numeric values, 0-10 |
| `detail` | `''` | Fixed detail line |
| `detail_path` | `''` | JSON path whose value replaces the fixed detail line |
| `headers` | `{}` | Additional HTTP request headers |
| `verify_ssl` | `true` | Verify HTTPS certificates |

Boolean JSON values are displayed as `ON` and `OFF`. Dictionaries and arrays are
rendered as compact JSON, although scalar values are usually more suitable for a
small LCD.

## Authentication headers

Bearer tokens, API keys and other header-based authentication can be configured
without adding service-specific code:

```yaml
rest:
  endpoints:
    battery:
      url: https://device.example.lan/api/telemetry
      interval: 60
      path: battery.percent
      title: Battery
      unit: '%'
      headers:
        Authorization: 'Bearer YOUR_TOKEN'
        X-API-Key: 'YOUR_API_KEY'
```

Credentials embedded in the URL itself are rejected. Keep real tokens only in the
local `config.yaml`, which is ignored by Git.

## Multiple values from one response

```yaml
rest:
  endpoints:
    temperature:
      url: http://192.168.1.50/api/status
      interval: 60
      path: sensors.temperature
      title: Temperature
      unit: '°C'
      precision: 1

    humidity:
      url: http://192.168.1.50/api/status
      interval: 60
      path: sensors.humidity
      title: Humidity
      unit: '%'
      precision: 0

    device_state:
      url: http://192.168.1.50/api/status
      interval: 60
      path: state
      title: Device
      detail_path: device.name
```

All three cards above use one GET request per medium polling cycle.

## Errors

REST cards use short status values that remain readable on the LCD:

- `WAIT` - no poll has completed yet
- `OFFLINE` - connection, timeout or other request failure
- `AUTH` - HTTP 401 or 403
- `HTTP NNN` - other HTTP error response
- `JSON` - response was not valid JSON
- `PATH` - configured JSON path was not found

The module does not log configured headers, so authentication values are not
written to the normal dashboard log output.
