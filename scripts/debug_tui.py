#!/usr/bin/env python3

import curses
import subprocess
import threading
import queue
import time
from typing import Any


TOPICS: list[str] = [
    "/door_closed_status",
    "/emergency_stop_status",
    "/pick_request",
    "/pick_response",
    "/scanned_barcode",
    "/stack_light_status",
]

MAX_LINES: int = 100


class TopicMonitor:
    """Monitors ROS2 topics and collects output in queues for display."""

    def __init__(self) -> None:
        """Initialize TopicMonitor with empty data storage and queues."""
        self.data: dict[str, list[str]] = {topic: [] for topic in TOPICS}
        self.queues: dict[str, queue.Queue[str]] = {
            topic: queue.Queue() for topic in TOPICS
        }
        self.running: bool = True

    def start(self) -> None:
        """Start daemon threads to listen to all ROS2 topics."""
        for topic in TOPICS:
            thread = threading.Thread(
                target=self.listen_topic,
                args=(topic,),
                daemon=True
            )
            thread.start()

    def listen_topic(self, topic: str) -> None:
        """Listen to a ROS2 topic and queue timestamped messages."""
        cmd = ["ros2", "topic", "echo", topic]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        while self.running:
            line: str = process.stdout.readline()

            if not line:
                continue

            line = line.strip()

            if line:
                timestamp: str = time.strftime("%H:%M:%S")
                formatted: str = f"[{timestamp}] {line}"

                self.queues[topic].put(formatted)

        process.kill()

    def update(self) -> None:
        """Drain queues and update data storage, limiting to MAX_LINES."""
        for topic in TOPICS:
            while not self.queues[topic].empty():
                msg: str = self.queues[topic].get()

                self.data[topic].append(msg)

                if len(self.data[topic]) > MAX_LINES:
                    self.data[topic] = self.data[topic][-MAX_LINES:]


def draw_box(
    stdscr: Any, y: int, x: int, h: int, w: int, title: str, lines: list[str]
) -> None:
    """Draw a bordered box with content on the curses window."""
    try:
        # Top border
        stdscr.addstr(y, x, "+" + "-" * (w - 2) + "+")

        # Title
        title_text: str = f" {title} "
        stdscr.addstr(y, x + 2, title_text, curses.A_BOLD)

        # Side borders
        for i in range(1, h - 1):
            stdscr.addstr(y + i, x, "|")
            stdscr.addstr(y + i, x + w - 1, "|")

        # Bottom border
        stdscr.addstr(y + h - 1, x, "+" + "-" * (w - 2) + "+")

        # Content
        visible: list[str] = lines[-(h - 2) :]

        for idx, line in enumerate(visible):
            clean: str = line[: w - 3]
            stdscr.addstr(y + 1 + idx, x + 1, clean)

    except curses.error:
        pass


def draw_ui(stdscr: Any, monitor: TopicMonitor) -> None:
    """Draw the multi-topic dashboard layout."""
    stdscr.clear()

    h, w = stdscr.getmaxyx()

    title: str = "ROS2 Multi Topic Dashboard"
    stdscr.addstr(0, w // 2 - len(title) // 2, title, curses.A_BOLD)

    cols: int = 3
    rows: int = 3

    box_width: int = w // cols
    box_height: int = (h - 2) // rows

    for idx, topic in enumerate(TOPICS):
        row: int = idx // cols
        col: int = idx % cols

        y: int = 2 + row * box_height
        x: int = col * box_width

        draw_box(
            stdscr,
            y,
            x,
            box_height,
            box_width,
            topic,
            monitor.data[topic]
        )

    footer: str = "q = quit"
    stdscr.addstr(h - 1, 2, footer)

    stdscr.refresh()


def main(stdscr: Any) -> None:
    """Main curses application loop for the ROS2 topic dashboard."""
    curses.curs_set(0)
    stdscr.nodelay(True)

    monitor = TopicMonitor()
    monitor.start()

    while True:
        monitor.update()

        draw_ui(stdscr, monitor)

        key = stdscr.getch()

        if key == ord('q'):
            monitor.running = False
            break

        time.sleep(0.05)


if __name__ == "__main__":
    curses.wrapper(main)