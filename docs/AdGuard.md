# AdGuard module

The `adguard` module displays AdGuard Home status by reading AdGuard-related entities from Home Assistant. It does not connect directly to the AdGuard Home API.

## Dependency

A configured `home_assistant` block is required:

```yaml
home_assistant:
  url: http://homeassistant.local:8123
  token: YOUR_LONG_LIVED_ACCESS_TOKEN
  verify_ssl: true
  entities: {}
```

Then enable AdGuard:

```yaml
adguard: {}
```

## Parameters

| Parameter | Type | Default/example | Purpose |
| --- | --- | --- | --- |
| `protection_entity` | entity ID string | `switch.adguard_home_protection` | Home Assistant entity that reports whether AdGuard protection is enabled. |
| `blocked_ratio_entity` | entity ID string | `sensor.adguard_home_dns_queries_blocked_ratio` | Home Assistant sensor that reports the blocked DNS query percentage. |

Both values must be valid Home Assistant entity IDs.

## Default configuration

```yaml
home_assistant:
  url: http://homeassistant.local:8123
  token: YOUR_LONG_LIVED_ACCESS_TOKEN
  verify_ssl: true
  entities: {}

adguard:
  protection_entity: switch.adguard_home_protection
  blocked_ratio_entity: sensor.adguard_home_dns_queries_blocked_ratio
```

If your Home Assistant integration creates different entity IDs, replace them with the actual IDs from Home Assistant.

## Polling

AdGuard values are read in the **medium** scheduler group, after the Home Assistant status has been collected. With the default `MEDIUM_INTERVAL: 60`, values are normally refreshed once per minute.

The Home Assistant connection settings, authentication token, SSL handling and request timeout come from the `home_assistant` module and global `REQUEST_TIMEOUT`.

## Available card

| Card | Display |
| --- | --- |
| `adguard` | `ONLINE`/`OFFLINE` plus protection or blocked-query information |

When protection is disabled, the detail line shows `PROT OFF`. When the blocked ratio is available, the detail line shows for example `BLOCK 18.5%`.

## Page example

```yaml
home_assistant:
  url: http://homeassistant.local:8123
  token: YOUR_LONG_LIVED_ACCESS_TOKEN
  verify_ssl: true
  entities: {}

adguard:
  protection_entity: switch.adguard_home_protection
  blocked_ratio_entity: sensor.adguard_home_dns_queries_blocked_ratio

PAGES:
  - name: dns
    layout:
      row1cell1: adguard
      row1cell2: home_assistant
```

## Error behavior

If Home Assistant is offline or authentication fails, AdGuard cannot be queried. The card can show details such as `AUTH`, `ENTITY`, `UNAVAIL` or `API` depending on the failure.