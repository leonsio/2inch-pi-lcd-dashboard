# System module

The `system` module displays local Raspberry Pi/Linux system metrics. It does not require a network service or credentials.

## Enable the module

```yaml
system: {}
```

Removing the `system` block disables the module and all system cards.

## Module parameters

The `system` block currently has no module-specific parameters. Use an empty mapping `{}`.

Several global settings affect the module:

| Parameter | Example/default | Purpose |
| --- | --- | --- |
| `SHOW_PER_CORE` | `false` | `false` shows average CPU usage from 0–100%. `true` sums all logical cores. |
| `FAST_INTERVAL` | `1` | Refresh interval for CPU, temperature, CPU frequency, RAM and swap. |
| `MEDIUM_INTERVAL` | `60` | Refresh interval for disk usage, free space, processes, uptime and load. |
| `SLOW_INTERVAL` | `600` | Refresh interval for CPU count and boot metadata. |
| `TEMP_RING_MIN_C` | `0` | Lower temperature value used by `temp_ring`. |
| `TEMP_RING_MAX_C` | `85` | Upper temperature value used by `temp_ring`. |

Global ring appearance settings such as `RING_COLOR_LOW`, `RING_COLOR_MID`, `RING_COLOR_HIGH`, `RING_WIDTH` and `RING_TRACK_COLOR` affect the ring cards as well.

## Available cards

| Card | Display |
| --- | --- |
| `cpu` | CPU load and CPU temperature |
| `ram` | RAM usage and used/total memory |
| `swap` | Swap usage; shows `OFF` when no swap is configured |
| `hdd` | Usage of the root filesystem `/` |
| `disk_free` | Free space of `/` |
| `uptime` | Uptime and load averages |
| `load` | 1, 5 and 15 minute load averages |
| `cpu_freq` | Current and reported maximum CPU frequency |
| `processes` | Number of processes and logical CPU threads |
| `cpu_ring` | CPU usage ring |
| `ram_ring` | RAM usage ring |
| `swap_ring` | Swap usage ring |
| `disk_ring` | Root filesystem usage ring |
| `hdd_ring` | Alias of `disk_ring` |
| `freq_ring` | Current CPU frequency relative to reported maximum |
| `temp_ring` | CPU temperature ring |

Usage/load cards become warning/error states at approximately 70%/90%.

## Complete example

```yaml
system: {}

SHOW_PER_CORE: false
FAST_INTERVAL: 1
MEDIUM_INTERVAL: 60
SLOW_INTERVAL: 600
TEMP_RING_MIN_C: 0
TEMP_RING_MAX_C: 85

PAGES:
  - name: system
    layout:
      row1cell1: cpu_ring
      row1cell2: ram_ring
      row1cell3: temp_ring
      row2cell1: cpu_freq
      row2cell2: processes
      row2cell3: load
      row3cell1: swap_ring
      row3cell2: disk_ring
      row3cell3: uptime
```

## Notes

CPU temperature and frequency depend on what the operating system exposes through `psutil`. If a value is unavailable, the corresponding card shows `?` rather than failing the module. The legacy `hdd`/`disk_ring` cards monitor only `/`; use the separate [Storage module](Storage.md) for multiple filesystems, I/O rates and SMART.