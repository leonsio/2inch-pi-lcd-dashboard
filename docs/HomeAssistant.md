# Home Assistant module

The `home_assistant` module monitors Home Assistant itself and can create read-only dashboard cards for arbitrary Home Assistant entities.

## Enable the module

```yaml
home_assistant:
  url: http://homeassistant.local:8123
  token: YOUR_LONG_LIVED_ACCESS_TOKEN
  verify_ssl: true
  entities: {}
```

## Top-level parameters

| Parameter | Type | Example/default | Purpose |
| --- | --- | --- | --- |
| `url` | string | `http://homeassistant.local:8123` | Required Home Assistant base URL. |
| `token` | string | `YOUR_LONG_LIVED_ACCESS_TOKEN` | Required long-lived access token. |
| `verify_ssl` | boolean | `true` | Verify HTTPS certificates. |
| `entities` | mapping | `{}` | Optional custom cards keyed by a lowercase alias. |

The shared global `REQUEST_TIMEOUT` controls HTTP timeout; default: `5` seconds.

## Entity parameters

Each entry below `entities` creates a card named `home_assistant.<alias>`.

```yaml
home_assistant:
  url: http://homeassistant.local:8123
  token: YOUR_LONG_LIVED_ACCESS_TOKEN
  verify_ssl: true
  entities:
    living_temperature:
      entity_id: sensor.living_room_temperature
      title: Living room
      precision: 1
      unit: '°C'
      detail: Indoor
```

| Parameter | Required | Type | Example | Purpose |
| --- | --- | --- | --- | --- |
| `entity_id` | yes | string | `sensor.living_room_temperature` | Home Assistant entity to read. |
| `title` | no | string | `Living room` | Card title. If omitted, `friendly_name` or the entity ID is used. |
| `attribute` | no | string | `current_temperature` | Display this entity attribute instead of the entity state. |
| `precision` | no | integer 0–10 | `1` | Decimal places for numeric values. |
| `unit` | no | string | `°C` | Override unit shown after the value. |
| `state_labels` | no | mapping | `{'on': 'ON', 'off': 'OFF'}` | Map raw states/values to display labels. |
| `detail` | no | string | `Indoor` | Fixed detail line below the value. |

Aliases may contain lowercase letters, digits and underscores.

## State examples

### Sensor

```yaml
home_assistant:
  url: http://homeassistant.local:8123
  token: YOUR_LONG_LIVED_ACCESS_TOKEN
  verify_ssl: true
  entities:
    temperature:
      entity_id: sensor.living_room_temperature
      title: Living room
      precision: 1
```

When `unit` is omitted for a normal state, the module uses Home Assistant's `unit_of_measurement` attribute when available.

### Switch or binary state

```yaml
home_assistant:
  url: http://homeassistant.local:8123
  token: YOUR_LONG_LIVED_ACCESS_TOKEN
  verify_ssl: true
  entities:
    lamp:
      entity_id: switch.living_room_lamp
      title: Lamp
      state_labels:
        'on': ON
        'off': OFF
```

The module is read-only; it does not switch the entity.

### Entity attribute

```yaml
home_assistant:
  url: http://homeassistant.local:8123
  token: YOUR_LONG_LIVED_ACCESS_TOKEN
  verify_ssl: true
  entities:
    climate_target:
      entity_id: climate.living_room
      title: Target
      attribute: temperature
      precision: 1
      unit: '°C'
```

## Available cards

| Card | Display |
| --- | --- |
| `home_assistant` | Home Assistant online/offline state and version/auth detail |
| `ha` | Alias of `home_assistant` |
| `home_assistant.<alias>` | Configured entity state or attribute |

## Polling

- **medium**: API reachability and all configured entity states
- **slow**: Home Assistant version from `/api/config`

With defaults this corresponds to 60 seconds and 600 seconds.

## Full page example

```yaml
home_assistant:
  url: http://homeassistant.local:8123
  token: YOUR_LONG_LIVED_ACCESS_TOKEN
  verify_ssl: true
  entities:
    temperature:
      entity_id: sensor.living_room_temperature
      title: Living room
      precision: 1
    lamp:
      entity_id: switch.living_room_lamp
      title: Lamp
      state_labels: {'on': 'ON', 'off': 'OFF'}

PAGES:
  - name: home_assistant
    layout:
      row1cell1: home_assistant
      row1cell2: home_assistant.temperature
      row1cell3: home_assistant.lamp
```

## Error values

Cards can show `WAIT`, `AUTH`, `OFFLINE`, `API`, `ENTITY`, `ATTRIBUTE`, `UNAVAILABLE` or `UNKNOWN` depending on the failure returned by Home Assistant.