# Power module

The `power` module adds dashboard actions for shutting down or rebooting the host.

## Enable the module

```yaml
power: {}
```

The module has no module-local parameters. Removing the block removes the `shutdown` and `reboot` cards/actions.

## Related global parameter

| Parameter | Example/default | Purpose |
| --- | --- | --- |
| `pre_shutdown` | `null` | Optional command that must complete successfully before shutdown or reboot. |

Accepted `pre_shutdown` forms:

```yaml
pre_shutdown: null
```

or a shell command string:

```yaml
pre_shutdown: 'systemctl stop example.service'
```

or, preferably, an argument list that does not invoke a shell:

```yaml
pre_shutdown:
  - systemctl
  - stop
  - example.service
```

`null`, `false` or an empty string disables the preparation command. If the preparation command fails, the requested power action is aborted.

## Available cards

| Card | Action |
| --- | --- |
| `shutdown` | Executes `systemctl poweroff` after `pre_shutdown` succeeds. |
| `reboot` | Executes `systemctl reboot` after `pre_shutdown` succeeds. |

These cards are actions, not monitoring cards. Selecting a card and confirming it with the dashboard OK action triggers the system command.

## Complete example

```yaml
power: {}

pre_shutdown:
  - systemctl
  - stop
  - docker.service

PAGES:
  - name: power
    layout:
      row1cell1: shutdown
      row1cell2: reboot
```

## Permissions and safety

The dashboard process must be allowed to execute the corresponding `systemctl` commands. A failed `pre_shutdown` command prevents the shutdown/reboot operation. Do not place an untrusted or user-controlled command in `pre_shutdown`.