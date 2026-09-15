# Storage module

The `storage` module monitors one or more mounted filesystems, free/used capacity, disk I/O rates and optional SMART health information.

## Enable the module

The minimal form monitors the root filesystem `/`:

```yaml
storage: {}
```

This uses the built-in defaults:

```yaml
storage:
  smartctl: smartctl
  devices:
    root:
      mount: /
      title: ROOT
      device: ''
      io_device: ''
      smart: false
```

## Top-level parameters

| Parameter | Type | Default/example | Purpose |
| --- | --- | --- | --- |
| `devices` | mapping | `root: ...` | Filesystems/storage devices to expose as dashboard cards. |
| `smartctl` | string | `smartctl` | Executable name or path used for SMART queries. |

## Device parameters

Each key below `devices` becomes a card alias such as `storage.ssd`.

```yaml
storage:
  devices:
    ssd:
      mount: /mnt/ssd
      title: SSD
      device: /dev/sda
      io_device: sda
      smart: true
```

| Parameter | Required | Type | Example/default | Purpose |
| --- | --- | --- | --- | --- |
| `mount` | yes | path string | `/mnt/ssd` | Mounted filesystem whose capacity is measured. |
| `title` | no | string | `SSD` | Card title. |
| `device` | no* | string | `/dev/sda` | Physical block device passed to `smartctl`; required when `smart: true`. Also used as an I/O device fallback. |
| `io_device` | no | string | `sda` | Explicit Linux/psutil diskstats key used for I/O rates. |
| `smart` | no | boolean | `false` | Enable SMART health polling for this device. |

When `io_device` is omitted, the module first tries `device`, then the block-device source detected for the mount point. For mapped/LVM/RAID setups, an explicit `io_device` is often clearer.

## Available cards

For every alias below `devices`, the following cards are generated:

| Card | Display |
| --- | --- |
| `storage.<alias>` | Used percentage and used/total GiB |
| `storage.<alias>_ring` | Used percentage as a ring |
| `storage.<alias>_free` | Free capacity in GiB |
| `storage.<alias>_io` | Current read and write rate |
| `storage.<alias>_smart` | SMART status and temperature |

The base card `storage` displays how many configured filesystems are mounted and reports SMART failures when enabled.

For the default `storage: {}` configuration the generated device cards are:

```text
storage.root
storage.root_ring
storage.root_free
storage.root_io
storage.root_smart
```

## Polling

- **fast**: read/write byte counters and calculated I/O rates
- **medium**: mount state and filesystem capacity
- **slow**: optional SMART health and temperature

With default scheduler values this corresponds to approximately 1, 60 and 600 seconds.

## SMART

SMART is disabled by default. To enable it:

```yaml
storage:
  smartctl: smartctl
  devices:
    ssd:
      mount: /mnt/ssd
      title: SSD
      device: /dev/sda
      io_device: sda
      smart: true
```

The target system must have `smartctl` available, normally from the `smartmontools` package. The dashboard service also needs permission to query the device.

The module runs an equivalent of:

```text
smartctl -j -H -A /dev/sda
```

Typical card values include `PASSED`, `FAILED`, `UNKNOWN`, `UNAVAILABLE` and `DISABLED`. When reported by SMART/NVMe data, temperature is shown in the detail line.

## Multiple-device example

```yaml
storage:
  smartctl: smartctl
  devices:
    root:
      mount: /
      title: ROOT
      device: ''
      io_device: ''
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

PAGES:
  - name: storage
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

## Notes

A missing/unmounted filesystem is reported as `UNMOUNTED`. The legacy `system` module also contains `hdd`, `disk_free` and `disk_ring` cards for `/`; use this Storage module when multiple mounts, I/O rates or SMART are required.