"""Read emulator memory through VisualBoyAdvance 1.7.2's GDB stub."""

from __future__ import annotations

import argparse
import ctypes
import socket
import time
from ctypes import wintypes
from pathlib import Path

user32 = ctypes.windll.user32
WM_COMMAND = 0x0111
BM_CLICK = 0x00F5
GDB_CONNECT_COMMAND = 40152
GDB_PORT_CONTROL = 1217
GDB_OK_CONTROL = 1008


def windows_for_pid(pid: int) -> list[tuple[int, str]]:
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    found: list[tuple[int, str]] = []

    def callback(hwnd: int, _lparam: int) -> bool:
        window_pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
        if window_pid.value == pid:
            title = ctypes.create_unicode_buffer(260)
            user32.GetWindowTextW(hwnd, title, len(title))
            found.append((hwnd, title.value))
        return True

    user32.EnumWindows(callback_type(callback), 0)
    return found


def open_gdb_listener(pid: int, port: int) -> None:
    windows = windows_for_pid(pid)
    main = next((hwnd for hwnd, title in windows if title.startswith("VisualBoyAdvance-")), None)
    if main is None:
        main = next((hwnd for hwnd, title in windows if title.startswith("VisualBoyAdvance")), None)
    if main is None:
        raise RuntimeError(f"VBA window not found for PID {pid}")

    # Post asynchronously: sending WM_COMMAND synchronously blocks until the
    # modal port dialog closes, which would also stop this client from connecting.
    user32.PostMessageW(main, WM_COMMAND, GDB_CONNECT_COMMAND, 0)
    dialog = None
    for _ in range(100):
        time.sleep(0.05)
        for hwnd, title in windows_for_pid(pid):
            if "GDB" in title:
                dialog = hwnd
                break
        if dialog:
            break
    if dialog is None:
        raise RuntimeError("VBA did not open its GDB port dialog")

    port_edit = user32.GetDlgItem(dialog, GDB_PORT_CONTROL)
    ok_button = user32.GetDlgItem(dialog, GDB_OK_CONTROL)
    if not port_edit or not ok_button:
        raise RuntimeError("VBA GDB dialog controls were not found")
    user32.SetWindowTextW(port_edit, str(port))
    user32.SendMessageW(ok_button, BM_CLICK, 0, 0)


def read_rsp_packet(sock: socket.socket) -> bytes:
    data = bytearray()
    while True:
        part = sock.recv(4096)
        if not part:
            raise ConnectionError("VBA closed the GDB connection")
        data.extend(part)
        start = data.find(b"$")
        if start >= 0:
            end = data.find(b"#", start + 1)
            if end >= 0 and len(data) >= end + 3:
                payload = bytes(data[start + 1 : end])
                sock.sendall(b"+")
                return payload


def request(sock: socket.socket, payload: str) -> bytes:
    raw = payload.encode("ascii")
    packet = b"$" + raw + b"#" + f"{sum(raw) & 255:02x}".encode("ascii")
    sock.sendall(packet)
    response = read_rsp_packet(sock)
    if response.startswith(b"E"):
        raise RuntimeError(f"VBA GDB error for {payload}: {response.decode(errors='replace')}")
    return response


def read_memory(sock: socket.socket, address: int, length: int, chunk: int = 0x100) -> bytes:
    out = bytearray()
    while len(out) < length:
        size = min(chunk, length - len(out))
        response = request(sock, f"m{address + len(out):08x},{size:x}")
        if len(response) != size * 2:
            raise RuntimeError(
                f"Short memory reply at 0x{address + len(out):08X}: "
                f"expected {size * 2} hex chars, received {len(response)}"
            )
        out.extend(bytes.fromhex(response.decode("ascii")))
    return bytes(out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--port", type=int, default=55555)
    parser.add_argument("--address", type=lambda s: int(s, 0), default=0x02000000)
    parser.add_argument("--length", type=lambda s: int(s, 0), default=16)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    open_gdb_listener(args.pid, args.port)
    with socket.create_connection(("127.0.0.1", args.port), timeout=4) as sock:
        sock.settimeout(4)
        data = read_memory(sock, args.address, args.length)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(data)
    print(f"0x{args.address:08X} + {args.length:#x}: {data.hex(' ')}")


if __name__ == "__main__":
    main()
