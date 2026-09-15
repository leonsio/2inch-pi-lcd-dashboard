# LCD Dashboard for Raspberry Pi SBCs

<p align="left">
<a href="/LICENSE"><img src="https://img.shields.io/badge/license-GPL-blue.svg" alt="license" /></a>
</p>

This project displays Raspberry Pi system and service status on a color SPI LCD.
Configure the dashboard in **YAML**, without editing Python source code:

- CPU, temperature, frequency, memory, swap, disk, free space, processes, uptime and system load
- IP address, hostname, network interface, link speed, live RX/TX traffic and Wi-Fi signal quality
- Optional WAN reachability, external/public IPv4 and configurable IPv4 online/offline checks
- Multiple storage devices with usage, free space, I/O rates and optional SMART health
- Optional Home Assistant, AdGuard, OpenCCU/piVCCU, Pi-hole v6, Proxmox, Docker and generic REST modules
- Individual Proxmox VM/LXC and Docker container status cards
- Generic JSON REST values with configurable 1/60/600-second polling and custom HTTP headers
- Multiple Home Assistant sensors, switches and other entity states on custom cards
- Classic cards and ring displays in a configurable grid
- Multiple overview pages and detail pages with optional GPIO buttons
- Optional shutdown and reboot buttons with a preparation command

Start with [config.example.yaml](config.example.yaml). The
[configuration guide](docs/Configuration.md) contains the complete option
reference and configuration examples. Extended System, Network, Proxmox and Docker
examples are documented in [docs/ExtendedModules.md](docs/ExtendedModules.md),
WAN and reachability monitoring in [docs/Network.md](docs/Network.md), storage in
[docs/Storage.md](docs/Storage.md), and the generic REST integration in
[docs/REST.md](docs/REST.md).

## Disclaimer

Raspberry Pi is a trademark of Raspberry Pi Ltd. The use of this trademark here is solely for descriptive purposes. I am not affiliated with Raspberry Pi Ltd. I derive no financial benefit from this content.

## Requirements

- Python >= 3.9
- Run on Raspberry Pi 4 and 5
- Raspberry Pi OS or Ubuntu
- [SPI interface enabled](docs/EnableSPI.md)
- A supported SPI LCD: 2-inch (default, landscape 320×240) or 1.69-inch (280×240)
- For the 1.69-inch ST7789V2 display:
  - Waveshare 24382 - [product page](https://www.waveshare.com/1.69inch-lcd-module.htm)
  - Seeed Studio 104990802 - [product page](https://www.seeedstudio.com/1-69inch-240-280-Resolution-IPS-LCD-Display-Module-p-5755.html)

## Display wiring

Connect the display to the Raspberry Pi according to the diagram below.  
The colors of the cables may vary depending on the supplier and batch. Focus on the function and pin number, not the color.

![Rpi_LCD_diagram.png](docs/img/Rpi_LCD_diagram.png)   
Diagram is valid for Raspberry Pi 4 and Pi 5

If on Raspberry Pi 5 your LCD backlight is flickering connect `BL` to `3.3V PIN 17`

## Installation

To enable the display, the SPI interface must be enabled.  
To do this, execute the following command and then reboot the device:

```shell
sudo sed -i '/^#dtparam=spi=on/s/^#//' /boot/firmware/config.txt
sudo reboot
```

Download the repository.

```shell
sudo apt-get -y install git
git clone https://github.com/leonsio/2inch-pi-lcd-dashboard.git
```

Create your local configuration before starting the dashboard:

```shell
cd 2inch-pi-lcd-dashboard
cp config.example.yaml config.yaml
nano config.yaml
```

Choose `LCD_DEVICE: '2inch'` or `LCD_DEVICE: '1inch69'`, enter your service
addresses/tokens and customize the pages. `config.yaml` is excluded from Git.
Commands below assume you start in the parent directory; if already inside the
repository, omit the repeated `cd`.

Then, you can run the program as a service. The program will start automatically with the system startup.  
Alternatively, you can run it once. The program will stop when you close the console.

### Run as a service - (recommended)   

```shell
cd 2inch-pi-lcd-dashboard
chmod +x *.sh
sudo ./create_service.sh
```

To **stop** the program, execute `sudo systemctl stop dashboard.service`

To **uninstall** the service, execute `sudo ./remove_service.sh`

### or run one time

If you do not want to run the program as a service, you can run it once.   
Note: Do not use both methods simultaneously.

```shell
cd 2inch-pi-lcd-dashboard
chmod +x *.sh
sudo ./run.sh
```
To stop the program, press Ctrl+C.

## Configuration

Edit `config.yaml` in the repository directory. For example:

```yaml
system: {}
network: {}
storage: {}
LCD_DEVICE: '2inch'
SHOW_PER_CORE: false
DISPLAY_BACKLIGHT: 80
BUTTONS_ENABLED: false
PAGES:
  - name: system
    layout:
      row1cell1: cpu_ring
      row1cell2: ram_ring
      row1cell3: storage.root_ring
      row2cell1: temp_ring
      row2cell2: swap_ring
      row2cell3: wifi_ring
      row3cell1: {module: traffic, colspan: 2}
      row3cell3: uptime
```

Omitted global settings inherit from `config.example.yaml`; `PAGES` replaces the entire
example page list. Modules load only when their block is present, such as `system: {}`,
`network: {}`, `storage: {}` or a `pihole` block with its connection settings. Remove a
block to disable its module. See [docs/Network.md](docs/Network.md) for WAN, public IPv4
and IP reachability checks, [docs/Storage.md](docs/Storage.md) for multiple local disks
and optional SMART monitoring, the [module and entity examples](docs/Configuration.md#14-multiple-home-assistant-entities)
for sensors, switches and other Home Assistant cards, or [docs/REST.md](docs/REST.md)
for arbitrary JSON REST APIs. Use `true`/`false` for booleans, `null` for no value,
and quote colors such as `'#FFFFFF'`. `SHOW_PER_CORE: false` displays average CPU usage
(0–100%); `true` sums all cores (0–400% on a four-core Pi).

The installer installs PyYAML and checks the configuration before starting the
service. You can also validate without accessing the hardware:

```shell
sudo ./run.sh --prepare-only
venv/bin/python dashboard_config.py
sudo systemctl restart dashboard.service
```

For display selection, GPIO wiring, page navigation, spanning cards, themes,
fonts, polling, service APIs and power actions, see the
[extended configuration documentation](docs/Configuration.md).

## Project structure

- `dashboard_modules/` contains all dynamically loaded dashboard modules and service integrations.
- `api/` contains shared API and module-loading infrastructure rather than service-specific implementations.
- `lib/` contains reusable dashboard runtime helpers such as buttons, navigation and rendering.
- `dashboard.py` remains the application entry point and `dashboard_config.py` remains the central YAML configuration loader.

## Contribution

Are you passionate about open-source development? We invite you to contribute to our GitHub repository! Whether you're a seasoned developer or just starting out, your ideas, code, and feedback are invaluable. Join our community, collaborate with like-minded individuals, and help us build something amazing together. Every contribution, no matter how small, makes a difference. Fork the repo, dive into the issues, and let's make this project even better!
