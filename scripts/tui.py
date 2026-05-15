#!/usr/bin/env python3

import curses
import json
import random
import subprocess
import time


PICK_ID = 1
COMPONENTS_PROCESS = None


def run_command(cmd):
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )

        output = result.stdout.strip()
        error = result.stderr.strip()

        if result.returncode == 0:
            return f"SUCCESS\n{output}"
        return f"ERROR\n{error}"

    except Exception as e:
        return f"EXCEPTION\n{str(e)}"


def send_pick():
    global PICK_ID

    quantity = random.randint(1, 10)
    pick_id = PICK_ID
    PICK_ID += 1

    payload = json.dumps({
        "pickId": pick_id,
        "quantity": quantity
    })

    cmd = (
        "curl -s -X POST http://localhost:8081/pick "
        "-H 'Content-Type: application/json' "
        f"-d '{payload}'"
    )

    result = run_command(cmd)

    return (
        f"POST SENT\n"
        f"pickId: {pick_id}\n"
        f"quantity: {quantity}\n\n"
        f"{result}"
    )


def toggle_door():
    cmd = (
        "ros2 service call "
        "/door_closed_status_toggle "
        "std_srvs/srv/Trigger"
    )

    return run_command(cmd)


def press_estop():
    cmd = (
        "ros2 service call "
        "/press_emergency_stop "
        "std_srvs/srv/Trigger"
    )

    return run_command(cmd)


def release_estop():
    cmd = (
        "ros2 service call "
        "/release_emergency_stop "
        "std_srvs/srv/Trigger"
    )

    return run_command(cmd)


def launch_components():
    global COMPONENTS_PROCESS

    try:
        subprocess.run("pkill -f 'ros2 launch components'", shell=True)
        subprocess.run("pkill emergency_stop", shell=True)
        subprocess.run("pkill door", shell=True)
        subprocess.run("pkill stack_light", shell=True)
        subprocess.run("pkill scanner", shell=True)
        subprocess.run("pkill robot_cell", shell=True)
        subprocess.run("pkill ui", shell=True)
        time.sleep(1)
    except:
        pass

    try:
        COMPONENTS_PROCESS = subprocess.Popen(
            "ros2 launch components components.launch.py",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return f"Components launched (PID: {COMPONENTS_PROCESS.pid})"
    except Exception as e:
        return f"EXCEPTION\n{str(e)}"


def stop_components():
    global COMPONENTS_PROCESS

    if COMPONENTS_PROCESS is None or COMPONENTS_PROCESS.poll() is not None:
        return "No components running"

    try:
        COMPONENTS_PROCESS.terminate()
        COMPONENTS_PROCESS.wait(timeout=5)
        return "Components stopped"
    except subprocess.TimeoutExpired:
        COMPONENTS_PROCESS.kill()
        return "Components killed (timeout)"
    except Exception as e:
        return f"EXCEPTION\n{str(e)}"


MENU = [
    "1. Send Random Pick",
    "2. Toggle Door Closed Status",
    "3. Press Emergency Stop",
    "4. Release Emergency Stop",
    "5. Start Robot Cell",
    "6. Stop Components",
    "7. Exit"
]


def draw_menu(stdscr, selected, message):
    stdscr.clear()

    h, w = stdscr.getmaxyx()

    title = "ROS2 Control TUI"
    stdscr.addstr(1, w // 2 - len(title) // 2, title, curses.A_BOLD)

    for idx, item in enumerate(MENU):
        x = 6
        y = 5 + idx

        if idx == selected:
            stdscr.attron(curses.A_REVERSE)
            stdscr.addstr(y, x, item)
            stdscr.attroff(curses.A_REVERSE)
        else:
            stdscr.addstr(y, x, item)

    stdscr.addstr(13, 2, "-" * (w - 4))
    stdscr.addstr(14, 2, "Output:")

    lines = message.splitlines()

    for i, line in enumerate(lines[: h - 17]):
        stdscr.addstr(16 + i, 2, line[: w - 4])

    stdscr.refresh()


def main(stdscr):
    curses.curs_set(0)

    selected = 0
    message = "Ready"

    while True:
        draw_menu(stdscr, selected, message)

        key = stdscr.getch()

        if key == curses.KEY_UP:
            selected = (selected - 1) % len(MENU)

        elif key == curses.KEY_DOWN:
            selected = (selected + 1) % len(MENU)

        elif key in [curses.KEY_ENTER, 10, 13]:

            if selected == 0:
                message = send_pick()

            elif selected == 1:
                message = toggle_door()

            elif selected == 2:
                message = press_estop()

            elif selected == 3:
                message = release_estop()

            elif selected == 4:
                message = launch_components()

            elif selected == 5:
                message = stop_components()

            elif selected == 6:
                break

        elif key == ord('q'):
            break


if __name__ == "__main__":
    curses.wrapper(main)