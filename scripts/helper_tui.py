#!/usr/bin/env python3

import curses
import json
import random
import subprocess
import time
import webbrowser
from typing import Any


PICK_ID: int = 1
COMPONENTS_PROCESS: subprocess.Popen[str] | None = None


def run_command(cmd: str) -> str:
    """Execute a shell command and return status with output or error."""
    try:
        result: subprocess.CompletedProcess[str] = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )

        output: str = result.stdout.strip()
        error: str = result.stderr.strip()

        if result.returncode == 0:
            return f"SUCCESS\n{output}"
        return f"ERROR\n{error}"

    except Exception as e:
        return f"EXCEPTION\n{str(e)}"


def send_pick() -> str:
    """Generate and send a random pick request to the API."""
    global PICK_ID

    quantity: int = random.randint(1, 10)
    pick_id: int = PICK_ID
    PICK_ID += 1

    payload: str = json.dumps({
        "pickId": pick_id,
        "quantity": quantity
    })

    cmd: str = (
        "curl -s -X POST http://localhost:8081/pick "
        "-H 'Content-Type: application/json' "
        f"-d '{payload}'"
    )

    result: str = run_command(cmd)

    return (
        f"POST SENT\n"
        f"pickId: {pick_id}\n"
        f"quantity: {quantity}\n\n"
        f"{result}"
    )


def toggle_door() -> str:
    """Toggle the door closed status via ROS2 service call."""
    cmd: str = (
        "ros2 service call "
        "/door_closed_status_toggle "
        "std_srvs/srv/Trigger"
    )

    return run_command(cmd)


def press_estop() -> str:
    """Press the emergency stop via ROS2 service call."""
    cmd: str = (
        "ros2 service call "
        "/press_emergency_stop "
        "std_srvs/srv/Trigger"
    )

    return run_command(cmd)


def release_estop() -> str:
    """Release the emergency stop via ROS2 service call."""
    cmd: str = (
        "ros2 service call "
        "/release_emergency_stop "
        "std_srvs/srv/Trigger"
    )

    return run_command(cmd)


def launch_components() -> str:
    """Kill existing component processes and launch fresh components."""
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
    except Exception as e:
        return f"EXCEPTION\n{str(e)}"

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


def stop_components() -> str:
    """Kill all running component processes."""
    try:
        subprocess.run("pkill -f 'ros2 launch components'", shell=True)
        subprocess.run("pkill emergency_stop", shell=True)
        subprocess.run("pkill door", shell=True)
        subprocess.run("pkill stack_light", shell=True)
        subprocess.run("pkill scanner", shell=True)
        subprocess.run("pkill robot_cell", shell=True)
        subprocess.run("pkill ui", shell=True)
        subprocess.run("pkill hmi", shell=True)
        time.sleep(1)
        return "Components stopped"
    except Exception as e:
        return f"EXCEPTION\n{str(e)}"


def open_website() -> str:
    """Open the local website in the default browser."""
    try:
        webbrowser.open("http://localhost:8082/")
        return "Opening http://localhost:8082/ in default browser"
    except Exception as e:
        return f"EXCEPTION\n{str(e)}"


MENU: list[str] = [
    "1. Start Robot Cell",
    "2. Open Website",
    "3. Toggle Door Closed Status",
    "4. Release Emergency Stop",
    "5. Send Random Pick",
    "6. Press Emergency Stop",
    "7. Stop Components",
    "8. Exit"
]


def draw_menu(stdscr: Any, selected: int, message: str) -> None:
    """Draw the menu interface with selected item highlighted and output message."""
    stdscr.clear()

    h: int
    w: int
    h, w = stdscr.getmaxyx()

    title: str = "ROS2 Control TUI"
    stdscr.addstr(1, w // 2 - len(title) // 2, title, curses.A_BOLD)

    for idx, item in enumerate(MENU):
        x: int = 6
        y: int = 5 + idx

        if idx == selected:
            stdscr.attron(curses.A_REVERSE)
            stdscr.addstr(y, x, item)
            stdscr.attroff(curses.A_REVERSE)
        else:
            stdscr.addstr(y, x, item)

    stdscr.addstr(13, 2, "-" * (w - 4))
    stdscr.addstr(14, 2, "Output:")

    lines: list[str] = message.splitlines()

    for i, line in enumerate(lines[: h - 17]):
        stdscr.addstr(16 + i, 2, line[: w - 4])

    stdscr.refresh()


def main(stdscr: Any) -> None:
    """Main curses application loop for ROS2 control interface."""
    curses.curs_set(0)

    selected: int = 0
    message: str = "Ready"

    while True:
        draw_menu(stdscr, selected, message)

        key: int = stdscr.getch()

        if key == curses.KEY_UP:
            selected = (selected - 1) % len(MENU)

        elif key == curses.KEY_DOWN:
            selected = (selected + 1) % len(MENU)

        elif key in [curses.KEY_ENTER, 10, 13]:

            if selected == 0:
                message = launch_components()

            elif selected == 1:
                message = open_website()

            elif selected == 2:
                message = toggle_door()

            elif selected == 3:
                message = release_estop()

            elif selected == 4:
                message = send_pick()

            elif selected == 5:
                message = press_estop()

            elif selected == 6:
                message = stop_components()

            elif selected == 7:
                break

        elif key == ord('q'):
            break


if __name__ == "__main__":
    curses.wrapper(main)