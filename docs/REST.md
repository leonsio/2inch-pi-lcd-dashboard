# REST module

The `rest` module creates read-only dashboard cards from arbitrary JSON HTTP(S) endpoints. All requests are GET requests.

## Enable the module

```yaml
rest:
  endpoints: {}
```

The module creates no cards until at least one endpoint is configured.

## Top-level parameters

| Parameter | Type | Default | Purpose |
| --- | --- | --- | --- |
| `endpoints` | mapping | `{}` | Named REST cards keyed by alias. |

## Endpoint parameters

Each item under `endpoints` creates a card named `rest.<alias>`.

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
      detail: Living room
      detail_path: device.name
      verify_ssl: true
      headers:
        Authorization: 'Bearer YOUR_TOKEN'
```

| Parameter | Required | Type | Example/default | Purpose |
| --- | --- | --- | --- | --- |
| `url` | yes | HTTP(S) URL | `http://192.168.1.50/api/status` | Endpoint to query with GET. |
| `interval` | no | integer | `60` | Polling group selector: exactly `1`, `60` or `600`. Default: `60`. |
| `path` | no | string | `sensors.temperature` | Dot-separated path to the value in the JSON response. Empty path means the entire JSON payload. |
| `title` | no | string | `Temperature` | Card title; alias-derived title is used when omitted. |
| `unit` | no | string | `°C` | Text appended to the displayed value. |
| `precision` | no | integer 0–10 | `1` | Decimal places for numeric values. |
| `detail` | no | string | `Living room` | Static detail text. |
| `detail_path` | no | string | `device.name` | Optional JSON path whose value replaces the static detail text when available. |
| `headers` | no | mapping | `Authorization: 'Bearer ...'` | Additional HTTP request headers. Header values must be strings. |
| `verify_ssl` | no | boolean | `true` | Verify HTTPS certificates. |

Aliases should use lowercase letters, digits and underscores.

## JSON paths

Object keys are separated by dots:

```json
{
  "sensors": {
    "temperature": 21.7
  }
}
```

Use:

```yaml
path: sensors.temperature
```

Numeric list indexes are also supported. For this payload:

```json
{
  "channels": [
    {"value": 10},
    {"value": 20}
  ]
}
```

use:

```yaml
path: channels.1.value
```

to display `20`.

## Polling intervals

The REST module accepts the numeric values `1`, `60` and `600` for `interval`:

| `interval` | Scheduler group | Default global scheduler value |
| ---: | --- | ---: |
| `1` | fast | `FAST_INTERVAL: 1` |
| `60` | medium | `MEDIUM_INTERVAL: 60` |
| `600` | slow | `SLOW_INTERVAL: 600` |

The numbers select a scheduler group. If the global `FAST_INTERVAL`, `MEDIUM_INTERVAL` or `SLOW_INTERVAL` values are changed, the real elapsed polling time follows that group. For example, `interval: 60` still selects the medium group even if `MEDIUM_INTERVAL` is changed to `30`.

The global `REQUEST_TIMEOUT` controls HTTP timeout.

## Request de-duplication

Multiple cards can read different values from the same response without issuing duplicate HTTP requests during the same scheduler cycle. Requests are shared when URL, headers and SSL verification settings are identical.

Example:

```yaml
rest:
  endpoints:
    temperature:
      url: http://192.168.1.50/api/status
      interval: 60
      path: sensors.temperature
      title: Temperature
      unit: '°C'

    humidity:
      url: http://192.168.1.50/api/status
      interval: 60
      path: sensors.humidity
      title: Humidity
      unit: '%'
```

Both cards use one GET request per medium cycle.

## Headers and authentication

Bearer token example:

```yaml
rest:
  endpoints:
    service_status:
      url: https://service.example.lan/api/status
      interval: 60
      path: status
      headers:
        Authorization: 'Bearer YOUR_TOKEN'
```

API key example:

```yaml
rest:
  endpoints:
    service_status:
      url: https://service.example.lan/api/status
      interval: 60
      path: status
      headers:
        X-API-Key: 'YOUR_API_KEY'
```

Credentials stored in headers belong only in the local `config.yaml` and should not be committed.

## Available cards

For each endpoint alias there is exactly one card:

```text
rest.<alias>
```

For example `temperature` creates `rest.temperature`.

## Complete example

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
      detail_path: device.name
      verify_ssl: true
      headers: {}

    status:
      url: http://192.168.1.50/api/status
      interval: 1
      path: status
      title: Service
      detail: Live status
      verify_ssl: true
      headers: {}

    version:
      url: http://192.168.1.50/api/status
      interval: 600
      path: system.version
      title: Version
      verify_ssl: true
      headers: {}

PAGES:
  - name: rest
    layout:
      row1cell1: rest.temperature
      row1cell2: rest.status
      row1cell3: rest.version
```

## Error values

Depending on the response, cards can show `WAIT`, `OFFLINE`, `AUTH`, `HTTP <status>`, `JSON` or `PATH`.

- `AUTH`: HTTP 401 or 403
- `JSON`: response could not be parsed as JSON
- `PATH`: configured `path` was not found
- `OFFLINE`: request failed before a usable HTTP response was obtained

The module is intentionally GET-only so a periodic dashboard refresh cannot trigger write operations on a REST service.