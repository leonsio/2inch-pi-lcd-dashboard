# Storage module

The `storage` module monitors one or more local filesystems and their backing
block devices. It is separate from the basic `hdd`/`disk_ring` cards in the
`system` module so additional SSDs, NVMe drives and mounted data volumes can be
shown individually.

## Quick start

An empty block monitors the root filesystem:

```yaml
storage: {}

PAGES:
  - name: storage
    layout:
      row1cell1: storage
      row1cell2: storage.root
      row1cell3: storage.root_ring
      row2cell1: storage.root_free
      row2cell2: {module: storage.root_io, colspan: 2}
```

`storage: {}` creates the default `root` device with mountpoint `/`. SMART is
not enabled by default.

## Multiple filesystems

Replace the default device mapping when more than one filesystem should be
monitored:

```yaml
storage:
  smartctl: smartctl
  devices:
    root:
      mount: /
      title: ROOT
      smart: false

    ssd:
      mount: /mnt/ssd
      title: SSD
      device: /dev/sda
      io_device: sda
      smart: true

    nvme:
      mount: /mnt/nvme
      title: NVME
      device: /dev/nvme0n1
      io_device: nvme0n1
      smart: true
```

Each device alias must be unique. The alias becomes part of the dashboard card
name.

### Device options

| Option | Meaning |
| --- | --- |
| `mount` | Filesystem mountpoint used for capacity/free-space information |
| `title` | Optional display title; otherwise the alias is used |
| `device` | Physical block device used by SMART, e.g. `/dev/sda` or `/dev/nvme0n1` |
| `io_device` | Linux/psutil disk-counter name, e.g. `sda`, `mmcblk0` or `nvme0n1` |
| `smart` | Enable SMART polling for this device; default `false` |

If `io_device` is omitted, the module first uses `device` and then attempts to
use the block-device source of the configured mountpoint. Explicit
`io_device` is recommended for device-mapper, RAID or unusual mount layouts.

## Available cards

For every configured alias, the following cards are generated:

| Card | Information |
| --- | --- |
| `storage` | Overall mounted-device count and SMART summary |
| `storage.<alias>` | Used percentage and used/total capacity |
| `storage.<alias>_ring` | Used percentage as ring |
| `storage.<alias>_free` | Free capacity |
| `storage.<alias>_io` | Current read and write throughput |
| `storage.<alias>_smart` | SMART health and temperature when available |

Example:

```yaml
PAGES:
  - name: disks
    layout:
      row1cell1: storage
      row1cell2: storage.ssd_ring
      row1cell3: storage.nvme_ring
      row2cell1: storage.ssd_free
      row2cell2: storage.ssd_io
      row2cell3: storage.ssd_smart
      row3cell1: storage.nvme_free
      row3cell2: storage.nvme_io
      row3cell3: storage.nvme_smart
```

The usage ring uses the same thresholds and green-to-red color scale as the
system CPU/RAM/disk rings.

## Polling

Storage information uses the existing dashboard scheduler:

- **fast**: disk read/write rate (`FAST_INTERVAL`, default 1 second)
- **medium**: mount and capacity information (`MEDIUM_INTERVAL`, default 60 seconds)
- **slow**: SMART health and temperature (`SLOW_INTERVAL`, default 600 seconds)

The first I/O sample shows `WAIT`, because two counter samples are required to
calculate a rate.

## SMART support

SMART is optional and does not add a Python dependency. The module executes the
system `smartctl` command only for devices with `smart: true`.

On Raspberry Pi OS / Debian / Ubuntu:

```shell
sudo apt-get install smartmontools
```

The default command is `smartctl`. It can be changed if necessary:

```yaml
storage:
  smartctl: /usr/sbin/smartctl
  devices:
    ssd:
      mount: /mnt/ssd
      device: /dev/sda
      io_device: sda
      smart: true
```

SMART card states include:

- `PASSED` - device reports healthy SMART status
- `FAILED` - device reports a SMART failure
- `UNKNOWN` - smartctl returned data but no supported health result
- `UNAVAILABLE` - smartctl executable was not found
- `ERROR` - smartctl could not be executed or returned unusable output
- `DISABLED` - SMART was intentionally disabled for this device

If smartctl reports a temperature, it is displayed in the card detail line.
Some USB-to-SATA bridges, SD cards and storage controllers do not expose SMART
information. In those cases keep `smart: false` or use the controller-specific
smartctl configuration outside the dashboard.

## Typical Raspberry Pi device names

| Storage | `device` example | `io_device` example |
| --- | --- | --- |
| microSD | `/dev/mmcblk0` | `mmcblk0` |
| USB/SATA SSD | `/dev/sda` | `sda` |
| NVMe SSD | `/dev/nvme0n1` | `nvme0n1` |

Use `lsblk` to verify the real device and mountpoint on the target Raspberry Pi.
