import curses
import multiprocessing
from curses import wrapper
from datetime import datetime
from datetime import date
import time
import getpass
import cpuinfo
import shellingham
import pyfiglet
import platform
import psutil
import subprocess
import re
import threading
import json
import netifaces
from uptime import uptime
import operator
import os

stdscr = curses.initscr()
# curses.noecho()
# curses.cbreak()
# stdscr.keypad(True)
curses.start_color()
curses.curs_set(0)

default = {'clock-time-format': '12h', 'user': {'user-custom-name': '', 'shell-custom-name': '', 'shell-custom-cmd': '', 'force-custom-utc': '', 'os-custom-pretty': '', 'os-custom-ver': ''}, 'processor': {'cpu-custom-name': ''}, 'network': {'force-iface-display': ''}, 'memory': {'size-unit': 'GiB'}, 'disk': {'base-dir': '/', 'size-unit': 'GiB'}, 'colors': {'field-name-accent': 'RED', 'field-name-weight': 'BOLD', 'field-data-accent': 'YELLOW', 'field-data-weight': 'NORMAL', 'border-accent': 'RED', 'box-label-accent': 'RED', 'box-label-weight': 'BOLD', 'clock-accent': 'RED', 'bar-accent': 'RED', 'transparency': 'no'}, 'layout': {'too-small-exclude': ['clock', 'user', 'vol', 'memuse', 'swapuse', 'mem', 'swap', 'usechart'], 'win-order-left': ['user', 'proc', 'cpuuse', 'net', 'mem', 'swap', 'memuse', 'swapuse'], 'win-order-center': ['vol'], 'win-order-right': ['clock']}}

try:
    config_data = json.load(open(f"{os.path.expanduser("~")}/.config/span/config.json"))
except FileNotFoundError:
    print("config not found! creating default in ~/.config/span/config.json")
    if not os.path.exists(f"{os.path.expanduser("~")}/.config/span"):
        os.makedirs(f"{os.path.expanduser("~")}/.config/span")
    with open(f"{os.path.expanduser("~")}/.config/span/config.json", "w") as f:
        json.dump(default, f, indent=4)
    config_data = json.load(open(f"{os.path.expanduser("~")}/.config/span/config.json"))

tp = curses.COLOR_BLACK if config_data["colors"]["transparency"] == "no" else -1

if tp == -1:
    curses.use_default_colors()

curses.init_pair(1, curses.COLOR_RED, tp)
#curses.init_pair(1, curses.COLOR_RED, -1)
curses.init_pair(2, curses.COLOR_BLUE, tp)
curses.init_pair(3, curses.COLOR_CYAN, tp)
curses.init_pair(4, curses.COLOR_GREEN, tp)
curses.init_pair(5, curses.COLOR_MAGENTA, tp)
curses.init_pair(6, curses.COLOR_WHITE, tp)
curses.init_pair(7, curses.COLOR_YELLOW, tp)
#curses.init_pair(7, curses.COLOR_YELLOW, -1)

color_conversion = {
    "RED": curses.color_pair(1),
    "BLUE": curses.color_pair(2),
    "CYAN": curses.color_pair(3),
    "GREEN": curses.color_pair(4),
    "MAGENTA": curses.color_pair(5),
    "WHITE": curses.color_pair(6),
    "YELLOW": curses.color_pair(7)
}

fmt_conversion = {
    "BOLD": curses.A_BOLD,
    "ITALIC": curses.A_ITALIC,
    "UNDERLINE": curses.A_UNDERLINE,
    "NORMAL": curses.A_NORMAL
}

colors_table = config_data["colors"]
uconf = config_data["user"]
procconf = config_data["processor"]
netconf = config_data["network"]
memconf = config_data["memory"]
diskconf = config_data["disk"]


# fmt_data["field-name-accent"]
# fmt_data["field-data-accent"]

fmt_data = {
    "field-name-accent": color_conversion[colors_table["field-name-accent"]],
    "field-name-weight": fmt_conversion[colors_table["field-name-weight"]],
    "field-data-accent": color_conversion[colors_table["field-data-accent"]],
    "field-data-weight": fmt_conversion[colors_table["field-data-weight"]],
    "border-accent": color_conversion[colors_table["border-accent"]],
    "box-label-accent": color_conversion[colors_table["box-label-accent"]],
    "box-label-weight": fmt_conversion[colors_table["box-label-weight"]],
    "clock-accent": color_conversion[colors_table["clock-accent"]],
    "bar-accent": color_conversion[colors_table["bar-accent"]],
    "transparency": config_data["colors"]["transparency"]
}

clock_form = "%I" if config_data["clock-time-format"] == "12h" else "%H"

def get_top_processes_by_memory(n=5):
    """
    Retrieves the top N processes by memory usage.

    Args:
        n (int): The number of top processes to return.

    Returns:
        list: A list of dictionaries with process details (PID, Name, Memory Usage).
    """
    process_list = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            # Get process info as a dict
            process_info = proc.as_dict(attrs=['pid', 'name', 'memory_info'])
            # Calculate memory usage in MB
            process_info['memory_usage_mb'] = process_info['memory_info'].rss / (1024 * 1024)
            process_list.append(process_info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # Sort the processes by memory usage in descending order
    process_list.sort(key=lambda x: x['memory_usage_mb'], reverse=True)

    return process_list[:n]

def parse_sensors_output():
    """
    Runs the 'sensors -u' command and parses the output into a dictionary.
    """
    try:
        # Run the command and capture the output
        result = subprocess.run(['sensors', '-u'], capture_output=True, text=True, check=True)
        output = result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running sensors command: {e.stderr}")
        return {}
    except FileNotFoundError:
        print("The 'sensors' command was not found. Ensure 'lm-sensors' is installed.")
        return {}

    data = {}
    current_chip = None
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue

        # Check for chip names (lines ending with ':')
        if line.endswith(':'):
            current_chip = line[:-1]
            data[current_chip] = {}
        elif current_chip:
            # Look for sensor input values (e.g., 'temp1_input:')
            match = re.match(r'^(\w+)_input:\s*(\S+)', line)
            if match:
                sensor_name = match.group(1)
                try:
                    value = float(match.group(2))
                    data[current_chip][sensor_name] = value
                except ValueError:
                    continue # Skip if value isn't a float
    return data

parse_sensors_output()

def get_default_interface_name():
    """
    Retrieves the name of the network interface used for the default route.
    Works across Windows, Linux, and macOS.
    """
    try:
        # Get the default gateway information for IPv4 (AF_INET)
        gws = netifaces.gateways()
        default_interface = gws['default'][netifaces.AF_INET][1]
        return default_interface
    except Exception as e:
        #print(f"Error finding default interface: {e}")
        return None

def get_volume():
    try:
        # Run the command to get the status of the default sink
        command = "wpctl get-volume @DEFAULT_AUDIO_SINK@"
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output = result.stdout.strip()

        # Use a regular expression to extract the volume level (a float between 0 and 1)
        match = re.search(r'Volume: (\d+\.\d+)', output)
        if match:
            volume_level_float = float(match.group(1))
            # Convert the 0.0 to 1.0 range to a percentage
            volume_percent = int(volume_level_float * 100)
            is_muted = "MUTED" in output
            return volume_percent, is_muted
        else:
            return None, None
    except subprocess.CalledProcessError as e:
        print(f"Error running wpctl: {e.stderr}")
        return None, None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None, None

def get_network_download_usage(interval=1):
    """
    Calculates the system-wide network download usage over a given interval.

    :param interval: The time interval in seconds to measure the usage (default 1 second).
    :return: The download speed in bytes per second (bytes/s).
    """
    # Get initial network I/O counters
    # nowrap=True detects and adjusts for kernel counter overflows
    last_io = psutil.net_io_counters(nowrap=True)
    last_bytes_recv = last_io.bytes_recv

    # Wait for the specified interval
    time.sleep(interval)

    # Get new network I/O counters
    new_io = psutil.net_io_counters(nowrap=True)
    new_bytes_recv = new_io.bytes_recv

    # Calculate the bytes received during the interval
    download_usage_bytes = new_bytes_recv - last_bytes_recv

    # Return the speed in bytes per second
    return download_usage_bytes / interval

def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = float(f.read()) / 1000.0
        return temp
    except FileNotFoundError:
        return None

def map_value_to_range(value, min_input, max_input, min_output, max_output):
    """
    Maps a value from one range to another.
    """
    input_range = max_input - min_input
    output_range = max_output - min_output

    # Calculate the relative position (ratio between 0 and 1)
    ratio = (value - min_input) / input_range

    # Map the ratio to the output range
    mapped_value = min_output + (ratio * output_range)

    return mapped_value

def generate_bicolor_line(str1, str2, attr1, attr2, y, x, win):
    win.addstr(y, x, str1, attr1)
    win.addstr(y, x + len(str1), str2, attr2)

def draw_user_data():
    local_now = datetime.now().astimezone()
    uinfo = generate_lb_win(7, 55, 1, 1, "User Info")
    generate_bicolor_line("Current user: ", uconf["user-custom-name"] if uconf["user-custom-name"] else getpass.getuser(), fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 1, 5, uinfo)
    generate_bicolor_line("Current user shell: ", uconf["shell-custom-name"] if uconf["shell-custom-name"] else shellingham.detect_shell()[0], fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 2, 5, uinfo)
    generate_bicolor_line("Shell command: ", uconf["shell-custom-cmd"] if uconf["shell-custom-cmd"] else shellingham.detect_shell()[1], fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 3, 5, uinfo)
    generate_bicolor_line("System UTC offset: ", uconf["force-custom-utc"] if uconf["force-custom-utc"] else local_now.strftime("%z"), fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 4, 5, uinfo)
    generate_bicolor_line("OS: ", f"{uconf["os-custom-pretty"] if uconf["os-custom-pretty"] else platform.system()} {uconf["os-custom-ver"] if uconf["os-custom-ver"] else platform.release()}", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 5, 5, uinfo)
    # uinfo.bkgd(' ', fmt_data["field-name-accent"])
    return uinfo

def draw_proc_data(stop_event):
    while True:
        try:
            cname = cpuinfo.get_cpu_info()["brand_raw"]
            cpu = psutil.cpu_percent()
            procinfo = generate_lb_win(7, 55, 8, 1, "Processor Info")
            generate_lb_border(procinfo, "Processor Info")
            generate_bicolor_line("CPU: ", procconf["cpu-custom-name"] if procconf["cpu-custom-name"] else cname, fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 1, 5, procinfo)
            generate_bicolor_line("Cores: ", f"{psutil.cpu_count()}", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 2, 5, procinfo)
            generate_bicolor_line("Running processes: ", f"{len(list(psutil.process_iter()))}", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 3, 5, procinfo)
            generate_bicolor_line("CPU utilization: ", f"{cpu}%", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 4, 5, procinfo)
            generate_bicolor_line("CPU temp (overall): ", f"{get_cpu_temp()}°C", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 5, 5, procinfo)
            # procinfo.bkgd(' ', fmt_data["field-name-accent"])
            draw_cpu_bar(cpu)
            draw_memory_data()
            draw_disk_data()
            draw_usage_chart(cpu, get_network_download_usage(interval=1))
            draw_task_chart()
            procinfo.noutrefresh()
            if stop_event.wait(timeout=1):
                break  # Exit the loop if the event is set
            #time.sleep(0.1)
        except Exception as e:
            print(e)
            print("-------------------")
            print("Please ensure your terminal size is at least 41 rows by 157 columns! You may change your text size to achieve this, but it will result in less readability. span is ideally a standalone application that takes up the whole screen in one specific workspace.")
            return e

def draw_cpu_bar(cpu):
    cpuperc = generate_lb_win(3, 55, 15, 1, "CPU Utilization (%)")
    generate_lb_border(cpuperc, "CPU Utilization (%)")
    cpuperc.attrset(fmt_data["bar-accent"])
    cpuperc.hline(1, 1, curses.ACS_CKBOARD, int(cpu) // 2)
    cpuperc.attrset(curses.A_NORMAL)
    # cpuperc.bkgd(' ', curses.color_pair(1))
    cpuperc.noutrefresh()
    cpuperc.erase()

def draw_net_data():
    interfaces = psutil.net_if_addrs()
    inter_list = list(interfaces)
    netinfo = generate_lb_win(7, 55, 18, 1, "Network Info")
    generate_lb_border(netinfo, "Network Info")
    if get_default_interface_name() != None:
        ipv4_data = list(interfaces[netconf["force-iface-display"] if netconf["force-iface-display"] else get_default_interface_name()])
        generate_bicolor_line("Interface: ", netconf["force-iface-display"] if netconf["force-iface-display"] else get_default_interface_name(), fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 1, 5, netinfo)
        generate_bicolor_line("IPv4: ", ipv4_data[0].address, fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 2, 5, netinfo)
        generate_bicolor_line("IPv6: ", ipv4_data[1].address, fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 3, 5, netinfo)
        generate_bicolor_line("Subnet mask: ", ipv4_data[0].netmask, fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 4, 5, netinfo)
        generate_bicolor_line("Broadcast: ", ipv4_data[0].broadcast, fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 5, 5, netinfo)
        # netinfo.bkgd(' ', fmt_data["field-name-accent"])
    else:
        generate_bicolor_line("Interface: ", "None (DISCONNECTED)", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 1, 5, netinfo)
        generate_bicolor_line("IPv4: ", "None (DISCONNECTED)", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 2, 5,
                              netinfo)
        generate_bicolor_line("IPv6: ", "None (DISCONNECTED)", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 3, 5,
                              netinfo)
        generate_bicolor_line("Subnet mask: ", "None (DISCONNECTED)", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 4, 5, netinfo)
        generate_bicolor_line("Broadcast: ", "None (DISCONNECTED)", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 5, 5, netinfo)
        # netinfo.bkgd(' ', fmt_data["field-name-accent"])
    return netinfo

def draw_memory_data():
    #while True:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        meminfo = generate_lb_win(5, 55, 25, 1, "Memory Info")
        generate_lb_border(meminfo, "Memory Info")
        swapinfo = generate_lb_win(5, 55, 30, 1, "Swap Info")
        generate_lb_border(swapinfo, "Swap Info")
        unit = ["GiB", 1074000000] if memconf["size-unit"] == "GiB" else ["GB", 1000000000]
        generate_bicolor_line("Total: ", f"{mem.total} Bytes ({mem.total / unit[1]:.2f} {unit[0]})", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 1, 5, meminfo)
        generate_bicolor_line("Open: ", f"{mem.free} Bytes ({mem.free / unit[1]:.2f} {unit[0]})", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 2, 5, meminfo)
        generate_bicolor_line("Used: ", f"{mem.used} Bytes ({mem.used / unit[1]:.2f} {unit[0]}/{mem.percent}%)", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 3, 5, meminfo)
        generate_bicolor_line("Total: ", f"{swap.total} Bytes ({swap.total / unit[1]:.2f} {unit[0]})", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 1, 5, swapinfo)
        generate_bicolor_line("Open: ", f"{swap.free} Bytes ({swap.free / unit[1]:.2f} {unit[0]})", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 2, 5, swapinfo)
        generate_bicolor_line("Used: ", f"{swap.used} Bytes ({swap.used / unit[1]:.2f} {unit[0]}/{swap.percent}%)", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 3, 5, swapinfo)
        # meminfo.bkgd(' ', fmt_data["field-name-accent"])
        # swapinfo.bkgd(' ', fmt_data["field-name-accent"])
        draw_mem_bar(mem.percent)
        draw_swap_bar(swap.percent)
        meminfo.noutrefresh()
        swapinfo.noutrefresh()
        #time.sleep(1)

#41

def draw_disk_data():
    rows, cols = stdscr.getmaxyx()
    io_counters = psutil.disk_io_counters()
    unit = ["GiB", 1074000000] if diskconf["size-unit"] == "GiB" else ["GB", 1000000000]
    diskinfo = generate_lb_win(11, 40, 30, 61, "Disk Info")
    direct = diskconf["base-dir"]
    generate_lb_border(diskinfo, "Disk Info")
    #diskinfo.vline(1, 37, curses.ACS_VLINE, 9)
    generate_bicolor_line("Disk total: ", f"{psutil.disk_usage(direct).total / unit[1]:.2f} {unit[0]}", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 1, 5, diskinfo)
    generate_bicolor_line("Disk used: ", f"{psutil.disk_usage(direct).used / unit[1]:.2f} {unit[0]} ({psutil.disk_usage("/").percent}%)", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 2, 5, diskinfo)
    generate_bicolor_line("Disk free: ", f"{psutil.disk_usage(direct).free / unit[1]:.2f} {unit[0]}", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 3, 5, diskinfo)
    generate_bicolor_line("Read count: ", f"{io_counters.read_count}", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 4, 5, diskinfo)
    generate_bicolor_line("Write count: ", f"{io_counters.write_count}", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 5, 5, diskinfo)
    generate_bicolor_line("Read time: ", f"{io_counters.read_time:.2f} ms", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 6, 5, diskinfo)
    generate_bicolor_line("Write time: ", f"{io_counters.write_time:.2f} ms", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 7, 5, diskinfo)
    generate_bicolor_line("Cumulative R/W diff: ", f"{(io_counters.read_bytes - io_counters.write_bytes) / unit[1]:.2f} {unit[0]}", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 8, 5, diskinfo)
    generate_bicolor_line("Busy time: ", f"{io_counters.busy_time:.2f} ms", fmt_data["field-name-weight"] | fmt_data["field-name-accent"], fmt_data["field-data-accent"], 9, 5, diskinfo)

    #diskinfo.bkgd(' ', fmt_data["field-name-accent"])
    diskinfo.noutrefresh()

def draw_usage_chart(cpu, net):
    rows, cols = stdscr.getmaxyx()
    io_counters = psutil.disk_io_counters()
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    sens = parse_sensors_output()
    chart = generate_lb_win(11, cols - 102, 30, 101, "Disk Info")
    generate_lb_border(chart, "Usage Chart")
    chart.attrset(fmt_data["field-data-accent"])
    chart.vline(1, 5, curses.ACS_VLINE, 9)
    chart.attrset(curses.A_NORMAL)
    chart.addstr(2, 2, "mem", fmt_data["field-name-accent"])
    chart.addstr(3, 1, "swap", fmt_data["field-name-accent"])
    chart.addstr(4, 2, "cpu", fmt_data["field-name-accent"])
    chart.addstr(5, 2, "net", fmt_data["field-name-accent"])
    chart.addstr(6, 2, "vol", fmt_data["field-name-accent"])
    chart.addstr(7, 1, "temp", fmt_data["field-name-accent"])
    chart.addstr(8, 1, "disk", fmt_data["field-name-accent"])
    draw_bar_chart(mem.percent, chart, 2, 6)
    draw_bar_chart(swap.percent, chart, 3, 6)
    draw_bar_chart(cpu, chart, 4, 6)
    draw_bar_chart(net / 1024, chart, 5, 6)
    draw_bar_chart(int(get_volume()[0]), chart, 6, 6) 
    draw_bar_chart(int(get_cpu_temp()), chart, 7, 6)
    draw_bar_chart(int(psutil.disk_usage("/").percent), chart, 8, 6)


    #diskinfo.bkgd(' ', fmt_data["field-name-accent"])
    chart.noutrefresh()
    chart.clear()

def draw_mem_bar(mem):
    cpuperc = generate_lb_win(3, 55, 35, 1, "Memory Usage (%)")
    generate_lb_border(cpuperc, "Memory Usage (%)")
    cpuperc.attrset(fmt_data["bar-accent"])
    cpuperc.hline(1, 1, curses.ACS_CKBOARD, int(mem) // 2)
    cpuperc.attrset(curses.A_NORMAL)
    # cpuperc.bkgd(' ', curses.color_pair(1))
    cpuperc.noutrefresh()
    cpuperc.erase()

def draw_bar_chart(v, win, y, x):
    rows, cols = stdscr.getmaxyx()
    win.attrset(fmt_data["bar-accent"])
    win.hline(y, x, curses.ACS_CKBOARD, int(map_value_to_range(v, 0, 100, 0, 45)))
    win.attrset(curses.A_NORMAL)
    # cpuperc.bkgd(' ', curses.color_pair(1))

def draw_swap_bar(swap):
    cpuperc = generate_lb_win(3, 55, 38, 1, "Swap Usage (%)")
    generate_lb_border(cpuperc, "Swap Usage (%)")
    cpuperc.attrset(fmt_data["bar-accent"])
    cpuperc.hline(1, 1, curses.ACS_CKBOARD, int(swap) // 2)
    cpuperc.attrset(curses.A_NORMAL)
    # cpuperc.bkgd(' ', curses.color_pair(1))
    cpuperc.noutrefresh()
    cpuperc.erase()

def draw_vol_bar(stop_event):
    while True:
        vol = generate_lb_win(40, 5, 1, 56, "Vol")
        # vol.bkgd(' ', fmt_data["field-name-accent"])
        generate_lb_border(vol, "Vol")
        vol.attrset(fmt_data["bar-accent"])
        vol.vline(0, 2, curses.ACS_CKBOARD, int(map_value_to_range(get_volume()[0], 0, 100, 0, 40)))
        vol.attrset(curses.A_NORMAL)
        vol.addstr(int(map_value_to_range(get_volume()[0], 0, 100, 0, 40)) - 1 if get_volume()[0] > 0 else int(map_value_to_range(get_volume()[0], 0, 100, 0, 40)), 1, f"{get_volume()[0]}%" if get_volume()[0] <= 95 else "", fmt_data["field-data-accent"])
        vol.addstr(0, 1, "Vol", fmt_data["box-label-accent"])
        vol.addstr(39, 1, "Max", fmt_data["field-data-accent"] if get_volume()[0] == 100 else fmt_data["field-name-accent"])
        vol.noutrefresh()
        vol.erase()
        if stop_event.wait(timeout=1):
            break  # Exit the loop if the event is set
        time.sleep(0.1)

def draw_date_data():
    datetm = date.today()
    tz = datetime.now().astimezone()
    rows, cols = stdscr.getmaxyx()
    dt = generate_lb_win(9, cols - 124, 1, 123, "Datetime Info")
    generate_lb_border(dt, "Datetime Info")
    generate_bicolor_line("Date: ", f"{datetm}", fmt_data["field-name-accent"] | curses.A_BOLD, fmt_data["field-data-accent"], 1, 5, dt) 
    generate_bicolor_line("Day: ", f"{date.today().strftime("%A, %B %d")}", fmt_data["field-name-accent"] | curses.A_BOLD, fmt_data["field-data-accent"], 2, 5, dt)
    generate_bicolor_line("UTC locale: ", f"UTC{tz.strftime("%z").replace("0", "")}", fmt_data["field-name-accent"] | curses.A_BOLD, fmt_data["field-data-accent"], 3, 5, dt)
    generate_bicolor_line("Timezone: ", f"{tz.strftime("%Z")}", fmt_data["field-name-accent"] | curses.A_BOLD, fmt_data["field-data-accent"], 4, 5, dt)
    generate_bicolor_line("Uptime: ", f"{uptime():.2f}s", fmt_data["field-name-accent"] | curses.A_BOLD, fmt_data["field-data-accent"], 5, 5, dt)
    generate_bicolor_line("Littletime: ", f"", fmt_data["field-name-accent"] | curses.A_BOLD, fmt_data["field-data-accent"], 6, 5, dt)
    generate_bicolor_line("Clock format: ", f"{config_data["clock-time-format"]}", fmt_data["field-name-accent"] | curses.A_BOLD, fmt_data["field-data-accent"], 7, 5, dt)
    return dt

def draw_task_chart():
    rows, cols = stdscr.getmaxyx()
    top = get_top_processes_by_memory(18)
    mem = psutil.virtual_memory()
    task = generate_lb_win(20, cols - 62, 10, 61, "Top processes (by memory):")
    generate_lb_border(task, "Top processes (by memory):")
    i = 0
    for proc in top:
        memstr =  f"PID: {proc["pid"]:<6}\tName: {proc["name"]:<25}Mem: {proc["memory_usage_mb"]:<2,.2f}MB"
        #task.addstr(1 + i, 5, memstr, fmt_data["field-data-accent"])
        task.addstr(1 + i, 5, f"PID: ", fmt_data["field-name-accent"])
        task.addstr(1 + i, 10, f"{proc["pid"]:<6}", fmt_data["field-data-accent"])
        task.addstr(1 + i, 20, f"Name: ", fmt_data["field-name-accent"])
        task.addstr(1 + i, 26, f"{proc["name"]:<25}", fmt_data["field-data-accent"])
        task.addstr(1 + i, 45, f"Mem: ", fmt_data["field-name-accent"])
        task.addstr(1 + i, 50, f"{proc["memory_usage_mb"]:.2f}MB", fmt_data["field-data-accent"])
        task.attrset(fmt_data["bar-accent"])
        task.hline(1 + i, 60, curses.ACS_CKBOARD, int(map_value_to_range((proc["memory_usage_mb"] / (mem.total / 1000000)) * 3, 0, 3, 0, (cols - 30) - len(memstr))))
        task.attrset(curses.A_NORMAL)
        i += 1
    task.noutrefresh()
    task.clear()


def generate_lb_win(nlines, ncols, y, x, label):
    wn = curses.newwin(nlines, ncols, y, x)
    #wn.bkgd(' ', fmt_data["border-accent"])
    wn.attrset(fmt_data["border-accent"])
    wn.box()
    wn.attrset(curses.A_NORMAL)
    wn.addstr(0, 1, label, fmt_data["box-label-accent"])
    return wn

def generate_lb_border(win, label):
    #win.bkgd(' ', fmt_data["border-accent"])
    win.attrset(fmt_data["border-accent"])
    win.border()
    win.attrset(curses.A_NORMAL)
    win.addstr(0, 1, label, fmt_data["box-label-weight"] | fmt_data["box-label-accent"])

def c_main(stdscr):
    stdscr.nodelay(1)
    stop_event = threading.Event()
    proc = threading.Thread(target=draw_proc_data, args=(stop_event,))
    vol = threading.Thread(target=draw_vol_bar, args=(stop_event,))
    proc.start()
    vol.start()

    rows, cols = stdscr.getmaxyx()

    bg = curses.newwin(0, 0, rows - 1, cols - 1)
    clock = curses.newwin(9, 62, 1, 61)
    dt = draw_date_data()
    # span = curses.newwin(8, 44, rows - 10, cols - 44)
    uinfo = draw_user_data()

    while True:
        try:
            key = stdscr.getch()
            if key == ord('q'):
                stop_event.set()
                break
            # mem = threading.Thread(target=draw_memory_data)
            # mem.start()
            #while True:
            netinfo = draw_net_data()
            cpu = psutil.cpu_percent()
            bg.bkgd(' ', curses.color_pair(2))
            clock.bkgd(' ', curses.color_pair(1))
            time_big = pyfiglet.figlet_format(f"{datetime.now().strftime(f"{clock_form}:%M:%S")}", font="banner").splitlines()
            span_big = pyfiglet.figlet_format("sPan v1.0.0", font="slant").splitlines()
            for i, line in enumerate(time_big):
                new_string = re.sub(r'#', '█', line)
                clock.addstr(i + 1, 3, f"{new_string}", fmt_data["clock-accent"])
                generate_bicolor_line("Littletime: ", f"{datetime.now().strftime(f"{clock_form}:%M:%S")}", fmt_data["field-name-accent"] | curses.A_BOLD, fmt_data["field-data-accent"], 6, 5, dt)
                # for i, line in enumerate(span_big):
                #     span.addstr(i, 0, f"{line}", curses.color_pair(1))
            stdscr.bkgd(' ', curses.color_pair(1))
            stdscr.hline(0, 1, curses.ACS_HLINE, cols - 2)
            generate_bicolor_line("sPan ", "v1.0.0", curses.A_BOLD, fmt_data["field-data-accent"], 0, (cols // 2) - 6, stdscr)
            curses.napms(100)
            generate_lb_border(uinfo, "User Info")
            generate_lb_border(clock, "Current Time")

            bg.noutrefresh()
            stdscr.noutrefresh()
            netinfo.noutrefresh()
            uinfo.noutrefresh()
            dt.noutrefresh()
            clock.noutrefresh()
            clock.erase()
            #span.noutrefresh()
            stdscr.timeout(10)
            curses.doupdate()
        # except KeyboardInterrupt:
        #     break        except KeyboardInterrupt:
        #except curses.error:

        except Exception as e:
            print(e)
            stop_event.set()
            print("-------------------")
            print("Please ensure your terminal size is at least 41 rows by 157 columns! You may change your text size to achieve this, but it will result in less readability. span is ideally a standalone application that takes up the whole screen in one specific workspace.")
            break

def main():
    try:
        now = time.time()
        next_second = int(now) + 1
        sleep_time = next_second - now

        if sleep_time > 0:
           time.sleep(sleep_time)
        c_main(stdscr)
    except Exception as e:
        #with open("log.txt", "w") as f:
        #   f.write(f"{e}\n")
        print(e)
        print("-------------------")
        print("Please ensure your terminal size is at least 41 rows by 157 columns! You may change your text size to achieve this, but it will result in less readability. span is ideally a standalone application that takes up the whole screen in one specific workspace.")
        return

if __name__ == "__main__":
    multiprocessing.freeze_support()
    wrapper(c_main)
