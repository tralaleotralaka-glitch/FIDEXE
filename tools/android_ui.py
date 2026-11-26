"""Tiny adb helper used by the Android UI screenshot workflow.

    python tools/android_ui.py shot out.png
    python tools/android_ui.py tap-edit 0
    python tools/android_ui.py tap-text "Подключиться"
    python tools/android_ui.py tap-exact "Закрыть"
    python tools/android_ui.py type "10.0.2.2:47811"
    python tools/android_ui.py dump
"""
from __future__ import annotations

import subprocess
import sys
import time
import xml.etree.ElementTree as ET


def adb(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(["adb", *args], capture_output=True, text=True, timeout=timeout)


def screen_size() -> tuple[int, int]:
    out = adb("shell", "wm", "size").stdout
    for line in out.splitlines():
        if "Physical size" in line or "Override size" in line:
            value = line.split(":")[-1].strip()
            width, height = value.split("x")
            return int(width), int(height)
    return 1080, 1920


def nodes():
    adb("shell", "uiautomator", "dump", "/sdcard/ui.xml")
    xml_text = adb("exec-out", "cat", "/sdcard/ui.xml").stdout
    start = xml_text.find("<?xml")
    if start > 0:
        xml_text = xml_text[start:]
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    result = []
    for node in root.iter("node"):
        bounds = node.get("bounds", "")
        if not bounds.startswith("["):
            continue
        left_top, right_bottom = bounds.strip("[]").split("][")
        x1, y1 = (int(v) for v in left_top.split(","))
        x2, y2 = (int(v) for v in right_bottom.split(","))
        result.append(
            {
                "class": node.get("class", ""),
                "text": node.get("text", ""),
                "desc": node.get("content-desc", ""),
                "bounds": (x1, y1, x2, y2),
                "center": ((x1 + x2) // 2, (y1 + y2) // 2),
                "clickable": node.get("clickable") == "true",
            }
        )
    return result


def tap(x: int, y: int) -> None:
    adb("shell", "input", "tap", str(x), str(y))


def scroll_up() -> None:
    width, height = screen_size()
    adb("shell", "input", "swipe", str(width // 2), str(int(height * 0.75)), str(width // 2), str(int(height * 0.35)), "250")
    time.sleep(0.6)


def hide_keyboard() -> None:
    adb("shell", "input", "keyevent", "111")  # ESC
    adb("shell", "input", "keyevent", "4")    # BACK
    time.sleep(0.4)


def find_text(fragment: str):
    for node in nodes():
        haystack = f"{node['text']} {node['desc']}"
        if fragment.lower() in haystack.lower():
            return node
    return None


def find_exact(text: str):
    """Node whose visible text is exactly `text` (buttons, not hints that quote them)."""
    for node in nodes():
        if node["text"].strip().lower() == text.strip().lower():
            return node
    return None


def tap_exact(text: str, attempts: int = 4) -> bool:
    for _ in range(attempts):
        node = find_exact(text)
        if node is not None:
            x, y = node["center"]
            tap(x, y)
            time.sleep(0.8)
            return True
        scroll_up()
    return False


def tap_text(fragment: str, attempts: int = 5) -> bool:
    for attempt in range(attempts):
        node = find_text(fragment)
        if node is not None:
            x, y = node["center"]
            width, height = screen_size()
            if y > height - 30:
                scroll_up()
                continue
            tap(x, y)
            time.sleep(0.8)
            return True
        scroll_up()
    return False


def tap_edit(index: int) -> bool:
    edits = [n for n in nodes() if "EditText" in n["class"]]
    if index >= len(edits):
        return False
    x, y = edits[index]["center"]
    tap(x, y)
    time.sleep(0.6)
    return True


def screenshot(path: str) -> None:
    result = subprocess.run(["adb", "exec-out", "screencap", "-p"], capture_output=True, timeout=60)
    with open(path, "wb") as handle:
        handle.write(result.stdout)
    print("saved", path, len(result.stdout), "bytes")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    command = sys.argv[1]
    argument = sys.argv[2] if len(sys.argv) > 2 else ""
    if command == "shot":
        screenshot(argument)
    elif command == "tap-edit":
        ok = tap_edit(int(argument))
        print("tap-edit", argument, "ok" if ok else "NOT FOUND")
        return hygiene(ok)
    elif command == "tap-text":
        ok = tap_text(argument)
        print("tap-text", argument, "ok" if ok else "NOT FOUND")
        return hygiene(ok)
    elif command == "tap-exact":
        ok = tap_exact(argument)
        print("tap-exact", argument, "ok" if ok else "NOT FOUND")
        return hygiene(ok)
    elif command == "type":
        escaped = argument.replace(" ", "%s")
        adb("shell", "input", "text", escaped)
        time.sleep(0.5)
    elif command == "hide-keyboard":
        hide_keyboard()
    elif command == "dump":
        for node in nodes():
            if node["text"] or "EditText" in node["class"] or node["clickable"]:
                print(f"{node['class'].split('.')[-1]:<14} {node['bounds']} clickable={node['clickable']} text={node['text']!r}")
    elif command == "open":
        adb("shell", "am", "start", "-n", "app.fidexe.remote/.MainActivity")
    else:
        print("unknown command", command)
        return 2
    return 0


def hygiene(ok: bool) -> int:
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
