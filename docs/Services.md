# Services module

The `services` module monitors local `systemd` services. It can show aggregate counts for running, active, failed and loaded service units and can also expose the state of selected units as individual dashboard cards.

The module is read-only. It does not start, stop or restart services.

## Enable the module

For aggregate counters only:

```yaml
services: {}
```

To additionally monitor specific services:

```yaml
services:
  units:
    dashboard:
      name: dashboard.service
      title: LCD Dashboard
    ssh: ssh.service
    docker:
      name: docker.service
      title: Docker Engine
```

Removing the `services` block disables the module and all of its cards.

## Module parameters

| Parameter | Type | Default/example | Purpose |
| --- | --- | --- | --- |
| `units` | mapping | `{}` | Defines individual systemd units that become `services.<alias>` cards. |

The module itself has no connection credentials or service-specific timeout setting. It uses the global `REQUEST_TIMEOUT` when invoking `systemctl`.

## `units` entries

Each entry below `services.units` has an alias. The alias becomes part of the card name.

### Short form

```yaml
services:
  units:
    ssh: ssh.service
    docker: docker.service
```

This creates:

- `services.ssh`
- `services.docker`

If the service name contains no dot, `.service` is appended automatically. Therefore this is also valid:

```yaml
services:
  units:
    ssh: ssh
```

### Long form

```yaml
services:
  units:
    dashboard:
      name: dashboard.service
      title: LCD Dashboard
```

| Unit parameter | Type | Required | Example | Purpose |
| --- | --- | --- | --- | --- |
| `name` | string | yes in long form | `dashboard.service` | systemd unit name queried with `systemctl show`. |
| `title` | string | no | `LCD Dashboard` | Display title. If omitted, the alias is converted to uppercase text. |

The intended target is a `.service` unit. Other systemd unit types are not included in the aggregate service counters.

## Available cards

| Card | Meaning |
| --- | --- |
| `services` | Summary: number of actually running services plus failed/active counts. |
| `services_running` | Number of service units whose `SubState` is `running`. |
| `services_active` | Number of service units whose `ActiveState` is `active`. This also includes services such as `active (exited)`. |
| `services_failed` | Number of failed service units. The card becomes an error when the value is greater than zero. |
| `services_total` | Number of service units currently loaded by systemd. |
| `services.<alias>` | State of one configured unit. |

`services_total` counts units returned by `systemctl list-units --type=service --all`. It is therefore the number of currently loaded service units, not the number of all installed unit files on disk.

## Individual service states

For configured `services.<alias>` cards the module reads:

- `LoadState`
- `ActiveState`
- `SubState`
- `UnitFileState`

Typical card values include:

| Value | Meaning | Card status |
| --- | --- | --- |
| `RUNNING` | Unit is active and currently running. | OK |
| `EXITED` | Unit is active but its process already exited, common for one-shot services. | OK |
| `INACTIVE` | Unit exists but is inactive. | Warning |
| `ACTIVATING` / `DEACTIVATING` / `RELOADING` | Transitional state. | Warning |
| `FAILED` | systemd reports the service as failed. | Error |
| `NOT FOUND` | Unit does not exist. | Error |
| `SYSTEMD` | `systemctl` could not return the unit state. | Error |
| `WAIT` | No collector result has been received yet. | Normal |

The detail line contains the unit name and, when available, the unit-file state such as `ENABLED`, `DISABLED`, `STATIC` or `MASKED`.

## Polling

The module uses the medium collector.

| Setting | Default | Effect |
| --- | ---: | --- |
| `MEDIUM_INTERVAL` | `60` | Refresh interval for counters and configured unit states. |
| `REQUEST_TIMEOUT` | `5` | Maximum time allowed for each `systemctl` invocation. |
| `LOG_MEDIUM_VALUES` | `true` | Enables the normal medium-level service summary log entry. |

Every medium cycle normally performs:

1. one `systemctl list-units` call for all aggregate counters;
2. one `systemctl show` call containing all configured individual units.

Adding more configured unit cards therefore does not create one subprocess per service.

## Complete configuration example

```yaml
services:
  units:
    dashboard:
      name: dashboard.service
      title: LCD Dashboard
    ssh: ssh.service
    docker:
      name: docker.service
      title: Docker Engine
    cron: cron.service

PAGES:
  - name: services
    layout:
      row1cell1: services
      row1cell2: services_running
      row1cell3: services_failed
      row2cell1: services.dashboard
      row2cell2: services.ssh
      row2cell3: services.docker
      row3cell1: services_active
      row3cell2: services_total
      row3cell3: services.cron
```

## Minimal overview example

```yaml
services: {}

PAGES:
  - name: status
    layout:
      row1cell1: services_running
      row1cell2: services_failed
      row1cell3: services_total
```

## Requirements and permissions

- The host must use `systemd` and provide the `systemctl` command.
- Reading ordinary service status normally does not require root privileges.
- The dashboard process must be able to communicate with the local systemd manager.
- On non-systemd systems or restricted containers the summary cards show `N/A / SYSTEMD`.

The module never invokes `systemctl start`, `stop`, `restart`, `enable` or `disable`.