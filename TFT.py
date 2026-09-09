import os
import sys
import time
import psutil
import socket
import logging
import netifaces
import signal
import requests
from lxml import etree
from lcd import LCD_2inch
from PIL import Image, ImageDraw, ImageFont

try:
    from config import (
        SHOW_PER_CORE,
        REQUEST_TIMEOUT,
        DISPLAY_BACKLIGHT,
        PIVCCU_FALLBACK_IP,
        XML_RPC_TOKEN,
        HOME_ASSISTANT_URL,
        HOME_ASSISTANT_TOKEN,
        ADGUARD_URL,
        ADGUARD_USERNAME,
        ADGUARD_PASSWORD,
        C_BG,
        C_T1,
        C_T2,
        C_T3,
        C_OK,
        C_ERROR,
    )
except ImportError as error:
    print(
        "Missing config.py. Copy config.example.py to config.py and enter your local values.",
        file=sys.stderr,
    )
    raise SystemExit(1) from error


disp = None

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)


def get_pivccu3_system_notification(pivccu_ip):
    """Return the number of piVCCU system notifications."""
    pivccu_xmlrpc_url = (
        f"http://{pivccu_ip.strip()}"
        f"/addons/xmlapi/systemNotification.cgi?sid={XML_RPC_TOKEN}"
    )
    response = requests.get(pivccu_xmlrpc_url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    tree = etree.fromstring(response.content)
    return len(tree.xpath(".//notification"))


def get_pivccu_status():
    """Return current piVCCU status, version and system notification count."""
    status = os.system('systemctl is-active --quiet pivccu.service')
    if status != 0:
        logging.info("piVCCU is not running")
        return False, '', 0

    pivccu_ip = os.popen(
        "pivccu-info | grep ^IP | cut -d\":\" -f2 | tr -d ' '"
    ).read().strip()

    if not pivccu_ip:
        pivccu_ip = PIVCCU_FALLBACK_IP
        logging.warning(
            "Could not determine piVCCU IP from pivccu-info; using fallback IP %s",
            pivccu_ip
        )

    pivccu_version = os.popen(
        "pivccu-info | grep version | cut -d\":\" -f2 | tr -d ' '"
    ).read().strip()

    try:
        pivccu_messages = get_pivccu3_system_notification(pivccu_ip)
    except Exception:
        logging.exception("Failed to read piVCCU system notifications")
        pivccu_messages = -1

    return True, pivccu_version, pivccu_messages


def get_home_assistant_status():
    """Return whether Home Assistant is reachable and its version."""
    url = f"{HOME_ASSISTANT_URL.rstrip('/')}/api/config"
    headers = {
        'Authorization': f'Bearer {HOME_ASSISTANT_TOKEN}',
        'Content-Type': 'application/json',
    }

    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code in (401, 403):
            return True, 'AUTH'
        response.raise_for_status()
        data = response.json()
        return True, str(data.get('version') or '?')
    except requests.RequestException:
        logging.exception("Failed to reach Home Assistant")
        return False, ''
    except ValueError:
        logging.exception("Invalid JSON response from Home Assistant")
        return True, '?'


def get_adguard_status():
    """Return AdGuard Home reachability, protection state and blocked percentage."""
    base_url = ADGUARD_URL.rstrip('/')
    auth = None
    if ADGUARD_USERNAME or ADGUARD_PASSWORD:
        auth = (ADGUARD_USERNAME, ADGUARD_PASSWORD)

    try:
        status_response = requests.get(
            f"{base_url}/control/status",
            auth=auth,
            timeout=REQUEST_TIMEOUT,
        )

        if status_response.status_code in (401, 403):
            return True, None, None, 'AUTH'

        status_response.raise_for_status()
        status_data = status_response.json()
        protection_enabled = bool(status_data.get('protection_enabled', False))

        stats_response = requests.get(
            f"{base_url}/control/stats",
            auth=auth,
            timeout=REQUEST_TIMEOUT,
        )

        if stats_response.status_code in (401, 403):
            return True, protection_enabled, None, 'AUTH'

        stats_response.raise_for_status()
        stats_data = stats_response.json()
        dns_queries = int(stats_data.get('num_dns_queries') or 0)
        blocked_queries = int(stats_data.get('num_blocked_filtering') or 0)
        blocked_percent = (blocked_queries / dns_queries * 100.0) if dns_queries else 0.0

        return True, protection_enabled, blocked_percent, ''

    except requests.RequestException:
        logging.exception("Failed to reach AdGuard Home")
        return False, None, None, ''
    except (ValueError, TypeError):
        logging.exception("Invalid response from AdGuard Home")
        return True, None, None, 'API'


def clear_screen():
    global disp
    if disp is None:
        return
    empty_image = Image.new('RGB', (disp.width, disp.height), color=(0, 0, 0))
    disp.ShowImage(empty_image)
    disp.bl_DutyCycle(0)
    disp.module_exit()


def handle_shutdown_signal(signum, frame):
    logging.info("Shutting down, clearing the screen...")
    clear_screen()
    sys.exit(0)


signal.signal(signal.SIGINT, handle_shutdown_signal)
signal.signal(signal.SIGTERM, handle_shutdown_signal)


def main():
    pivccu_active, pivccu_version, pivccu_messages = get_pivccu_status()
    ha_online, ha_version = get_home_assistant_status()
    adguard_online, adguard_protection, adguard_blocked_percent, adguard_detail = get_adguard_status()

    logging.info('Raspberry Pi Hardware Monitor Start')

    if not hasattr(psutil, "sensors_temperatures"):
        logging.error("sensors_temperatures not supported")
        sys.exit("CPU temperature sensors are not supported")

    temps = psutil.sensors_temperatures()
    if not temps:
        logging.error("sensors_temperatures not available")
        sys.exit("CPU temperature sensors are not available")

    global hostname
    hostname = get_hostname()

    global disp
    disp = LCD_2inch.LCD_2inch()
    disp.Init()
    disp.clear()
    disp.bl_DutyCycle(DISPLAY_BACKLIGHT)

    Font1 = ImageFont.truetype("./font/JetBrainsMono-Medium.ttf", 35)
    Font2 = ImageFont.truetype("./font/JetBrainsMono-Medium.ttf", 25)
    Font3 = ImageFont.truetype("./font/JetBrainsMono-Medium.ttf", 20)
    Font4 = ImageFont.truetype("./font/JetBrainsMono-Medium.ttf", 15)

    get_ip_address()
    low_frequency_tasks()
    high_frequency_tasks()
    medium_frequency_tasks()

    try:
        next_time = time.time() + 1
        skip = 0
        logging.info('Entering forever loop')

        while True:
            try:
                high_frequency_tasks()

                if skip % 10 == 0:
                    medium_frequency_tasks()

                if skip % 30 == 0:
                    low_frequency_tasks()
                    pivccu_active, pivccu_version, pivccu_messages = get_pivccu_status()
                    ha_online, ha_version = get_home_assistant_status()
                    adguard_online, adguard_protection, adguard_blocked_percent, adguard_detail = get_adguard_status()

                    print(
                        f'DEBUG SERVICES -> HA online={ha_online}, version={ha_version!r}; '
                        f'AdGuard online={adguard_online}, protection={adguard_protection}, '
                        f'blocked={adguard_blocked_percent!r}, detail={adguard_detail!r}',
                        flush=True
                    )

                screen_width = disp.height
                screen_height = disp.width

                image1 = Image.new("RGB", (screen_width, screen_height), "WHITE")
                draw = ImageDraw.Draw(image1)

                cell_width = screen_width / 3
                cell_height = screen_height / 3

                cpu_x = cell_width * 0.5
                ram_x = cell_width * 1.5
                hdd_x = cell_width * 2.5
                row2_center_y = cell_height * 1.5
                row3_center_y = cell_height * 2.5

                title_y = cell_height * 0.12
                value_y = cell_height * 0.50
                detail_y = cell_height * 0.875
                percent_offset_x = cell_width * 0.26
                percent_offset_y = cell_height * 0.06

                draw.line([(cell_width, 0), (cell_width, screen_height)], fill="BLACK", width=2)
                draw.line([(cell_width * 2, 0), (cell_width * 2, screen_height - cell_height)], fill="BLACK", width=2)
                draw.line([(0, cell_height), (screen_width, cell_height)], fill="BLACK", width=2)
                draw.line([(0, cell_height * 2), (screen_width, cell_height * 2)], fill="BLACK", width=2)

                # CPU
                draw.text((cpu_x, title_y), 'CPU', fill=C_T2, font=Font2, anchor="mm")
                if SHOW_PER_CORE:
                    draw.text(
                        (cpu_x, value_y),
                        f'{int(cpu_percent)}',
                        fill=value_to_hex_color_cpu_usage_400(int(cpu_percent)),
                        font=Font1,
                        anchor="mm"
                    )
                else:
                    draw.text(
                        (cpu_x, value_y),
                        f'{int(cpu_percent)}',
                        fill=value_to_hex_color_cpu_usage(int(cpu_percent)),
                        font=Font1,
                        anchor="mm"
                    )
                    draw.text(
                        (cpu_x + percent_offset_x, value_y + percent_offset_y),
                        '%', fill=C_T2, font=Font2, anchor="mm"
                    )

                draw.text(
                    (cpu_x, detail_y),
                    f'TEMP:{int(cpu_temp)}°C',
                    fill=C_T2,
                    font=Font4,
                    anchor="mm"
                )

                # piVCCU - middle left
                draw.text(
                    (cpu_x, row2_center_y - cell_height * 0.36),
                    'piVCCU', fill=C_T2, font=Font2, anchor="mm"
                )
                if pivccu_active:
                    message_text = 'Err:?' if pivccu_messages < 0 else f'Err:{pivccu_messages}'
                    draw.text(
                        (cpu_x, row2_center_y - cell_height * 0.02),
                        message_text,
                        fill=C_ERROR,
                        font=Font3,
                        anchor="mm"
                    )
                    draw.text(
                        (cpu_x, row2_center_y + cell_height * 0.30),
                        f'V:{pivccu_version}',
                        fill=C_T2,
                        font=Font4,
                        anchor="mm"
                    )
                else:
                    draw.text(
                        (cpu_x, row2_center_y),
                        'OFFLINE', fill=C_ERROR, font=Font3, anchor="mm"
                    )

                # Home Assistant - middle center
                draw.text(
                    (ram_x, row2_center_y - cell_height * 0.36),
                    'HOME ASST', fill=C_T2, font=Font4, anchor="mm"
                )
                draw.text(
                    (ram_x, row2_center_y - cell_height * 0.02),
                    'ONLINE' if ha_online else 'OFFLINE',
                    fill=C_OK if ha_online else C_ERROR,
                    font=Font3,
                    anchor="mm"
                )
                if ha_online:
                    draw.text(
                        (ram_x, row2_center_y + cell_height * 0.30),
                        f'V:{ha_version}',
                        fill=C_T1,
                        font=Font4,
                        anchor="mm"
                    )

                # AdGuard Home - middle right
                draw.text(
                    (hdd_x, row2_center_y - cell_height * 0.36),
                    'ADGUARD', fill=C_T2, font=Font4, anchor="mm"
                )
                draw.text(
                    (hdd_x, row2_center_y - cell_height * 0.02),
                    'ONLINE' if adguard_online else 'OFFLINE',
                    fill=C_OK if adguard_online else C_ERROR,
                    font=Font3,
                    anchor="mm"
                )
                if adguard_online:
                    if adguard_detail:
                        adguard_text = adguard_detail
                    elif adguard_protection is False:
                        adguard_text = 'PROT OFF'
                    elif adguard_blocked_percent is not None:
                        adguard_text = f'BLOCK {adguard_blocked_percent:.1f}%'
                    else:
                        adguard_text = 'ONLINE'
                    draw.text(
                        (hdd_x, row2_center_y + cell_height * 0.30),
                        adguard_text,
                        fill=C_T1,
                        font=Font4,
                        anchor="mm"
                    )

                # RAM
                draw.text((ram_x, title_y), 'RAM', fill=C_T2, font=Font2, anchor="mm")
                draw.text(
                    (ram_x, value_y),
                    f'{int(mem.percent)}',
                    fill=value_to_hex_color_cpu_usage(int(mem.percent)),
                    font=Font1,
                    anchor="mm"
                )
                draw.text(
                    (ram_x + percent_offset_x, value_y + percent_offset_y),
                    '%', fill=C_T2, font=Font2, anchor="mm"
                )
                draw.text(
                    (ram_x, detail_y),
                    f'{ram_used:.1f}/{ram_total}GB',
                    fill=C_T2,
                    font=Font4,
                    anchor="mm"
                )

                # HDD
                draw.text((hdd_x, title_y), 'HDD', fill=C_T2, font=Font2, anchor="mm")
                draw.text(
                    (hdd_x, value_y),
                    f'{int(disk.percent)}',
                    fill=value_to_hex_color_cpu_usage(int(disk.percent)),
                    font=Font1,
                    anchor="mm"
                )
                draw.text(
                    (hdd_x + percent_offset_x, value_y + percent_offset_y),
                    '%', fill=C_T2, font=Font2, anchor="mm"
                )
                draw.text(
                    (hdd_x, detail_y),
                    f'{disk_used_gb:.1f}/{int(disk_total_gb)}GB',
                    fill=C_T2,
                    font=Font4,
                    anchor="mm"
                )

                # Uptime and load - bottom left cell
                draw.text(
                    (cpu_x, cell_height * 2 + cell_height * 0.14),
                    'UPTIME',
                    fill=C_T2,
                    font=Font3,
                    anchor="mm"
                )
                draw.text(
                    (cpu_x, row3_center_y - cell_height * 0.02),
                    uptime_text,
                    fill=C_T1,
                    font=Font3,
                    anchor="mm"
                )
                draw.text(
                    (cpu_x, row3_center_y + cell_height * 0.31),
                    f'L:{load_1:.1f}/{load_5:.1f}/{load_15:.1f}',
                    fill=C_T2,
                    font=Font4,
                    anchor="mm"
                )

                # IP address and hostname - merged bottom-right 2x1 area
                info_x = cell_width * 2
                draw.text(
                    (info_x, cell_height * 2 + cell_height * 0.14),
                    'IP / HOSTNAME',
                    fill=C_T2,
                    font=Font3,
                    anchor="mm"
                )
                draw.text(
                    (info_x, row3_center_y - cell_height * 0.03),
                    ip_local_address or 'No IP',
                    fill=C_T1,
                    font=Font3,
                    anchor="mm"
                )
                draw.text(
                    (info_x, row3_center_y + cell_height * 0.31),
                    hostname,
                    fill=C_T2,
                    font=Font4,
                    anchor="mm"
                )

                disp.ShowImage(image1)
                skip += 1

                time.sleep(max(0, next_time - time.time()))
                next_time += (time.time() - next_time) // 1 * 1 + 1

            except Exception:
                logging.exception("Dashboard update failed")
                time.sleep(1)

    except KeyboardInterrupt:
        logging.info("Loop interrupted by user")
    except Exception:
        logging.exception("Dashboard main loop failed")

    logging.info('End forever loop')
    logging.info('Hardware Monitor End')
    clear_screen()


def print_stats():
    try:
        logging.info(
            f'Values -> CPU: {int(cpu_percent)}%, '
            f'CPU_TEMP: {int(cpu_temp)}°C, '
            f'RAM: {int(mem.percent)}%, '
            f'SWAP: {int(swap.percent)}%, '
            f'DISK: {int(disk.percent)}%'
        )
    except Exception:
        logging.exception("Failed to print system statistics")


def get_cpu_temperature():
    temps = psutil.sensors_temperatures()
    if not temps:
        logging.error("sensors_temperatures not supported")
        return 0

    try:
        return temps[next(iter(temps))][0].current
    except (KeyError, IndexError):
        logging.exception("Failed to read CPU temperature")
        return 0


def format_uptime():
    uptime_seconds = max(0, int(time.time() - psutil.boot_time()))
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60

    if days > 0:
        return f'{days}d {hours:02d}h'
    if hours > 0:
        return f'{hours}h {minutes:02d}m'
    return f'{minutes}m'


def high_frequency_tasks():
    global cpu_percent
    global cpu_temp

    if SHOW_PER_CORE:
        cpu_percent = sum(psutil.cpu_percent(percpu=True))
    else:
        cpu_percent = psutil.cpu_percent()

    cpu_temp = get_cpu_temperature()


def medium_frequency_tasks():
    global mem
    global swap
    global ram_used, ram_total
    global uptime_text
    global load_1, load_5, load_15

    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    ram_used = (mem.total - mem.available) / (1024 ** 3)
    ram_total = round(mem.total / (1024 ** 3))

    uptime_text = format_uptime()
    load_1, load_5, load_15 = os.getloadavg()

    print(
        f'DEBUG UPTIME/LOAD -> uptime={uptime_text}, '
        f'load1={load_1:.2f}, load5={load_5:.2f}, load15={load_15:.2f}',
        flush=True
    )

    print_stats()


def low_frequency_tasks():
    global disk
    global disk_used_gb, disk_total_gb
    global ip_local_address

    disk = psutil.disk_usage("/")
    disk_used_gb = disk.used / (1024 ** 3)
    disk_total_gb = round(disk.total / (1024 ** 3), 0)
    ip_local_address = get_ip_address()

    print(
        f'DEBUG NETWORK -> ip={ip_local_address!r}, hostname={hostname!r}',
        flush=True
    )


def value_to_hex_color_cpu_usage(value):
    if not (0 <= value <= 100):
        return C_BG

    green = (0, 255, 0)
    yellow = (255, 255, 0)
    red = (255, 0, 0)

    if value <= 50:
        ratio = value / 50
        r = int(green[0] + ratio * (yellow[0] - green[0]))
        g = int(green[1] + ratio * (yellow[1] - green[1]))
        b = int(green[2] + ratio * (yellow[2] - green[2]))
    else:
        ratio = (value - 50) / 50
        r = int(yellow[0] + ratio * (red[0] - yellow[0]))
        g = int(yellow[1] + ratio * (red[1] - yellow[1]))
        b = int(yellow[2] + ratio * (red[2] - yellow[2]))

    return f'#{r:02x}{g:02x}{b:02x}'


def value_to_hex_color_cpu_usage_400(value):
    if not (0 <= value <= 400):
        return C_BG

    green = (0, 255, 0)
    yellow = (255, 255, 0)
    red = (255, 0, 0)

    if value <= 200:
        ratio = value / 200
        r = int(green[0] + ratio * (yellow[0] - green[0]))
        g = int(green[1] + ratio * (yellow[1] - green[1]))
        b = int(green[2] + ratio * (yellow[2] - green[2]))
    else:
        ratio = (value - 200) / 200
        r = int(yellow[0] + ratio * (red[0] - yellow[0]))
        g = int(yellow[1] + ratio * (red[1] - yellow[1]))
        b = int(yellow[2] + ratio * (red[2] - yellow[2]))

    return f'#{r:02x}{g:02x}{b:02x}'


def get_hostname():
    return socket.gethostname()


def get_ip_address():
    interfaces = ['eth0', 'wlan0']

    for interface in interfaces:
        try:
            addresses = netifaces.ifaddresses(interface)
            ip_info = addresses.get(netifaces.AF_INET)
            if ip_info:
                ip_address = ip_info[0]['addr']
                if ip_address and not ip_address.startswith("127."):
                    global net_interface
                    net_interface = interface
                    return ip_address
        except ValueError:
            continue

    return None


def is_raspberry_pi():
    try:
        with open('/proc/cpuinfo', 'r') as f:
            return 'Raspberry Pi' in f.read()
    except FileNotFoundError:
        return False


def is_spi_enabled():
    spi_devices = [
        "/dev/spidev0.0",
        "/dev/spidev0.1",
        "/dev/spidev1.0",
        "/dev/spidev1.1"
    ]
    return any(os.path.exists(device) for device in spi_devices)


def is_spi_enabled_config():
    try:
        with open('/boot/firmware/config.txt', 'r') as f:
            return 'dtparam=spi=on' in f.read()
    except FileNotFoundError:
        return False


def check_python_version():
    required_version = (3, 8)
    current_version = sys.version_info[:3]
    return current_version > required_version


if __name__ == '__main__':
    if check_python_version():
        if is_raspberry_pi():
            if is_spi_enabled() or is_spi_enabled_config():
                main()
            else:
                logging.error("SPI is not enabled on Raspberry Pi")
                sys.exit("SPI is not enabled")
        else:
            logging.error("Only Raspberry Pi is supported")
            sys.exit("Only Raspberry Pi is supported")
    else:
        logging.error("Python version is not greater than 3.8")
        sys.exit("Python version is not greater than 3.8")
