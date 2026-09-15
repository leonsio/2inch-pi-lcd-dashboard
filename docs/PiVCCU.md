# piVCCU / OpenCCU module

The `pivccu` module reads system notifications from an OpenCCU/piVCCU installation through the XML API add-on.

## Enable the module

```yaml
pivccu:
  ip: 192.168.1.30
  token: YOUR_CCU_XML_API_TOKEN
```

## Parameters

| Parameter | Type | Example/default | Purpose |
| --- | --- | --- | --- |
| `ip` | string | `192.168.1.30` | Required IPv4 address or host value used to reach OpenCCU/piVCCU. |
| `token` | string | `YOUR_CCU_XML_API_TOKEN` | Required XML API token (`sid`). |

The shared global `REQUEST_TIMEOUT` controls the HTTP timeout; the default is `5` seconds.

## Required OpenCCU component

The integration expects the XML API endpoint:

```text
http://<ip>/addons/xmlapi/systemNotification.cgi
```

The configured `token` is sent as the `sid` query parameter. The XML API add-on therefore has to be installed and the token must be valid.

## Polling

The module is refreshed in the **medium** scheduler group. With the default `MEDIUM_INTERVAL: 60`, the system notification count is read once per minute.

## Available cards

`pivccu` and `openccu` are aliases for the same card.

The card displays:

- `ERR 0` when the API is online and there are no system notifications
- `ERR <number>` when OpenCCU reports system notifications
- `OFFLINE` when the API cannot be reached/read

A non-zero notification count is displayed as an error state.

## Complete example

```yaml
pivccu:
  ip: 192.168.1.30
  token: ABCDEF0123456789

PAGES:
  - name: homematic
    layout:
      row1cell1: openccu
```

## Notes

This module currently uses HTTP for the XML API URL and does not expose a separate SSL setting. The token belongs in the local `config.yaml`; do not commit real credentials to the repository.