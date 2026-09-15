# Extended System, Network, Proxmox and Docker modules

This page documents the additional information cards for the local Raspberry Pi,
network interfaces, Proxmox guests and Docker containers.

## System cards

Enable local system metrics with:

```yaml
system: {}
```

Available classic cards:

- `cpu` - CPU usage and CPU temperature
- `ram` - RAM usage
- `swap` - swap usage, or `OFF` when no swap is configured
- `hdd` - root filesystem usage
- `disk_free` - free space on the root filesystem
- `uptime` - system uptime and load averages
- `load` - 1, 5 and 15 minute load averages
- `cpu_freq` - current CPU frequency and maximum reported frequency
- `processes` - current process count and logical CPU count

Available ring cards:

- `cpu_ring`
- `ram_ring`
- `swap_ring`
- `disk_ring` / `hdd_ring`
- `freq_ring`
- `temp_ring`

CPU, RAM, swap and disk rings use the normal green-to-red load scale. The CPU
frequency ring shows the current fraction of the reported maximum frequency but
keeps a neutral/healthy color because high clock frequency is not itself an error.

## Network cards

Enable network monitoring with:

```yaml
network: {}
NETWORK_INTERFACES:
  - eth0
  - wlan0
```

The first interface in `NETWORK_INTERFACES` with an IPv4 address is selected.
Available cards:

- `network` - combined IP, hostname, interface and link speed
- `ip` - IPv4 address and interface
- `hostname` - hostname and current IPv4 address
- `traffic` - live receive/transmit rate
- `network_rx` - receive rate and total received bytes
- `network_tx` - transmit rate and total transmitted bytes
- `network_link` - link state, speed and MTU
- `wifi` - Wi-Fi signal in dBm and quality percentage
- `wifi_ring` - Wi-Fi quality as a ring; strong signal is green, weak signal red

Traffic rates are calculated from Linux network counters during the fast polling
interval. Wi-Fi quality is read from `/proc/net/wireless`; on Ethernet or drivers
that do not expose this information the Wi-Fi cards show `N/A`.

Example:

```yaml
system: {}
network: {}
PAGES:
  - name: network
    layout:
      row1cell1: network_rx
      row1cell2: network_tx
      row1cell3: network_link
      row2cell1: wifi_ring
      row2cell2: {module: traffic, colspan: 2}
```

## Proxmox guest cards

The `proxmox` card continues to show the total number of running guests. Individual
VM or LXC status cards can additionally be configured under `vms`.

```yaml
proxmox:
  url: https://pve.example.lan:8006
  api_token_id: dashboard@pve!lcd-dashboard
  api_token_secret: YOUR_TOKEN_SECRET
  verify_ssl: false
  include_lxc: true
  vms:
    homeassistant:
      vmid: 100
      title: Home Assistant
    dockerhost: 101

PAGES:
  - name: proxmox
    layout:
      row1cell1: proxmox
      row1cell2: proxmox.homeassistant
      row1cell3: proxmox.dockerhost
```

The short form `dockerhost: 101` uses the alias as the card title. The long form
allows a custom title. Cards display `RUNNING`, `STOPPED`, `NOT FOUND`, `AUTH` or
`OFFLINE` and include the VMID and Proxmox node in the detail line.

When `include_lxc: false`, LXC resources are not included in the Proxmox result and
therefore cannot be displayed as individual cards.

## Docker module

Docker is accessed directly through the local Docker Engine Unix socket; no
additional Docker Python package is required.

```yaml
docker:
  socket: /var/run/docker.sock
  containers:
    homeassistant:
      name: homeassistant
      title: Home Assistant
    mqtt: mosquitto

PAGES:
  - name: docker
    layout:
      row1cell1: docker
      row1cell2: docker_ring
      row2cell1: docker.homeassistant
      row2cell2: docker.mqtt
```

Available cards:

- `docker` - number of running containers versus all containers
- `docker_ring` - same ratio as a ring; all containers running is green
- `docker.<alias>` - state of an individually configured container

Individual container cards report states such as `RUNNING`, `EXITED`, `PAUSED` or
`RESTARTING`. A configured container that is not returned by Docker is shown as
`NOT FOUND`.

The dashboard process must have permission to access the configured socket. On a
standard Docker installation this normally means running as root or using a user
that is permitted to access `/var/run/docker.sock`.
