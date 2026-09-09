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

# Choose how to display CPU usage percentages
SHOW_PER_CORE = False
# False = [0 - 100%]
# True  = [0 - 400%]

# Raspberry Pi LCD pin configuration:
# to be done in lcdconfig.py
disp = None

xml_rpc_token = 'NNXkXnaGVXpFDLgz'

# Text colors
C_BG = '#00129A'  # LCD background
C_T1 = '#FFFFFF'  # main text
C_T2 = '#c9c9c9'  # secondary text
C_T3 = '#c9c9c9'  # bottom text

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)


def get_pivccu3_system_notification(pivccu_ip):
    """Return the number of piVCCU system notifications."""
    pivccu_xmlrpc_url = (
        f"http://{pivccu_ip.strip()}"
        f"/addons/xmlapi/systemNotification.cgi?sid={xml_rpc_token}"
    )
    response = requests.get(pivccu_xmlrpc_url, timeout=5)
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
    pivccu_version = os.popen(
        "pivccu-info | grep version | cut -d\":\" -f2 | tr -d ' '"
    ).read().strip()

    try:
        pivccu_messages = get_pivccu3_system_notification(pivccu_ip)
    except Exception:
        logging.exception("Failed to read piVCCU system notifications")
        pivccu_messages = -1

    return True, pivccu_version, pivccu_messages


def checkIfProcessRunning(processName):
    """Check if any running process contains the given process name."""
    for proc in psutil.process_iter():
        try:
            if processName.lower() in proc.name().lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


def clear_screen():
    """Clear the screen and shut down the display cleanly."""
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

    if checkIfProcessRunning('pihole-FTL'):
        pihole_active = True
        logging.info('Pi-hole is running')
    else:
        pihole_active = False
        logging.info('Pi-hole is offline')

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
    disp.bl_DutyCycle(100)  # ToDo: Fix hardware PWM on Rpi 5

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
                high_frequency_tasks()  # every second

                if skip % 10 == 0:
                    medium_frequency_tasks()

                if skip % 30 == 0:
                    low_frequency_tasks()
                    pivccu_active, pivccu_version, pivccu_messages = get_pivccu_status()

                # The LCD driver exposes portrait dimensions. The dashboard is rendered
                # in landscape orientation, therefore width and height are swapped here.
                screen_width = disp.height
                screen_height = disp.width

                image1 = Image.new("RGB", (screen_width, screen_height), "WHITE")
                draw = ImageDraw.Draw(image1)

                cell_width = screen_width / 3
                cell_height = screen_height / 3

                cpu_x = cell_width * 0.5
                ram_x = cell_width * 1.5
                hdd_x = cell_width * 2.5

                row1_center_y = cell_height * 0.5
                row2_center_y = cell_height * 1.5

                title_y = cell_height * 0.12
                value_y = cell_height * 0.50
                detail_y = cell_height * 0.875
                percent_offset_x = cell_width * 0.26
                percent_offset_y = cell_height * 0.06

                # Draw vertical lines
                draw.line(
                    [(cell_width, 0), (cell_width, screen_height)],
                    fill="BLACK",
                    width=2
                )
                draw.line(
                    [(cell_width * 2, 0), (cell_width * 2, screen_height - cell_height)],
                    fill="BLACK",
                    width=2
                )

                # Draw horizontal lines
                draw.line(
                    [(0, cell_height), (screen_width, cell_height)],
                    fill="BLACK",
                    width=2
                )
                draw.line(
                    [(0, cell_height * 2), (screen_width, cell_height * 2)],
                    fill="BLACK",
                    width=2
                )

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
                        '%',
                        fill=C_T2,
                        font=Font2,
                        anchor="mm"
                    )

                draw.text(
                    (cpu_x, detail_y),
                    f'TEMP:{int(cpu_temp)}°C',
                    fill=C_T2,
                    font=Font4,
                    anchor="mm"
                )

                # piVCCU
                draw.text(
                    (cpu_x, row2_center_y - cell_height * 0.36),
                    'piVCCU',
                    fill=C_T2,
                    font=Font2,
                    anchor="mm"
                )
                if pivccu_active:
                    message_text = 'Err:?' if pivccu_messages < 0 else f'Err:{pivccu_messages}'
                    draw.text(
                        (cpu_x, row2_center_y),
                        message_text,
                        fill="#FF0000",
                        font=Font3,
                        anchor="mm"
                    )
                    draw.text(
                        (cpu_x, row2_center_y + cell_height * 0.50),
                        f'V:{pivccu_version}',
                        fill=C_T2,
                        font=Font4,
                        anchor="mm"
                    )
                else:
                    draw.text(
                        (cpu_x, row2_center_y),
                        'OFFLINE',
                        fill="#FF0000",
                        font=Font3,
                        anchor="mm"
                    )

                # Pi-hole placeholder. pihole_active is already detected and can be
                # rendered in one of the remaining cells in a later layout step.

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
                    '%',
                    fill=C_T2,
                    font=Font2,
                    anchor="mm"
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
                    '%',
                    fill=C_T2,
                    font=Font2,
                    anchor="mm"
                )
                draw.text(
                    (hdd_x, detail_y),
                    f'{disk_used_gb:.1f}/{int(disk_total_gb)}GB',
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
    """Retrieve the current CPU temperature using psutil."""
    temps = psutil.sensors_temperatures()
    if not temps:
        logging.error("sensors_temperatures not supported")
        return 0

    try:
        return temps[next(iter(temps))][0].current
    except (KeyError, IndexError):
        logging.exception("Failed to read CPU temperature")
        return 0


def high_frequency_tasks():
    logging.debug("high_frequency_tasks()")
    global cpu_percent
    global cpu_temp

    if SHOW_PER_CORE:
        cpu_percent = sum(psutil.cpu_percent(percpu=True))
    else:
        cpu_percent = psutil.cpu_percent()

    cpu_temp = get_cpu_temperature()


def medium_frequency_tasks():
    logging.debug("medium_frequency_tasks()")

    global mem
    global swap
    global ram_used, ram_total

    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    ram_used = (mem.total - mem.available) / (1024 ** 3)
    ram_total = round(mem.total / (1024 ** 3))

    print_stats()


def low_frequency_tasks():
    logging.debug("low_frequency_tasks()")

    global disk
    global disk_used_gb, disk_total_gb
    global ip_local_address

    disk = psutil.disk_usage("/")
    disk_used_gb = disk.used / (1024 ** 3)
    disk_total_gb = round(disk.total / (1024 ** 3), 0)
    ip_local_address = get_ip_address()


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
    """Get the local IP address, prioritizing Ethernet over Wi-Fi."""
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
    """Check whether the script is running on a Raspberry Pi."""
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
            if 'Raspberry Pi' in cpuinfo:
                return True
    except FileNotFoundError:
        return False

    return False


def is_spi_enabled():
    """Check whether an SPI device is available."""
    spi_devices = [
        "/dev/spidev0.0",
        "/dev/spidev0.1",
        "/dev/spidev1.0",
        "/dev/spidev1.1"
    ]

    return any(os.path.exists(device) for device in spi_devices)


def is_spi_enabled_config():
    """Check whether SPI is enabled in Raspberry Pi config.txt."""
    try:
        with open('/boot/firmware/config.txt', 'r') as f:
            config = f.read()
            return 'dtparam=spi=on' in config
    except FileNotFoundError:
        return False


def check_python_version():
    """Check whether the current Python version is greater than 3.8."""
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
