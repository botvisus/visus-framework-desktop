"""A classic Win32 window that records where every click lands — the ground
truth for the click tests in test_agent_matrix.py. Run as its own process:

    python _click_target_app.py <state-dir>

Plain message-driven Win32 (RegisterClass + WndProc, GDI painting), like a
classic desktop app: a real click and a virtual one (PostMessage) both arrive
as WM_LBUTTONDOWN with client coordinates in lParam, so the two can be compared
pixel for pixel. (Tk was tried first and is no good here: it reads the physical
button state, so it ignores every synthetic click.)

Writes ``<state-dir>/ready.json`` (pid, title, client area and each drawn item
in SCREEN pixels) and appends one JSON line per click to ``clicks.jsonl``.
Per-monitor DPI aware, like the CLI, so both speak physical pixels.
"""

from __future__ import annotations

import ctypes
import json
import os
import sys
from pathlib import Path

import win32api
import win32con
import win32gui

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except (AttributeError, OSError):
    pass

state = Path(sys.argv[1])
title = f"Visus Alvo de Clique {os.getpid()}"

BLUE = win32api.RGB(31, 111, 235)
# client-area coordinates. The same word twice on one line, the right one 2 px
# higher (reading order must still say left = #1); two identical buttons, the
# right one 1 px higher.
WORDS = {"salvar1": (110, 70), "salvar2": (360, 68)}
BUTTONS = {"botao1": (110, 200), "botao2": (360, 199)}
BUTTON_SIZE = (110, 56)
FIELD = (110, 290, 380, 50)  # a classic EDIT control, for the typing tests


def _font():
    lf = win32gui.LOGFONT()
    lf.lfHeight = -34
    lf.lfWeight = 700
    lf.lfFaceName = "Segoe UI"
    return win32gui.CreateFontIndirect(lf)


FONT = _font()


def _signed(v: int) -> int:
    return ctypes.c_short(v & 0xFFFF).value


def _record(hwnd: int, lparam: int, button: int) -> None:
    x, y = _signed(lparam), _signed(lparam >> 16)
    sx, sy = win32gui.ClientToScreen(hwnd, (x, y))
    with (state / "clicks.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"x": sx, "y": sy, "button": button}) + "\n")


def _paint(hwnd: int) -> None:
    hdc, ps = win32gui.BeginPaint(hwnd)
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    win32gui.FillRect(hdc, (left, top, right, bottom), win32gui.GetStockObject(win32con.WHITE_BRUSH))
    old = win32gui.SelectObject(hdc, FONT)
    win32gui.SetBkMode(hdc, win32con.TRANSPARENT)
    win32gui.SetTextColor(hdc, win32api.RGB(20, 20, 20))
    for x, y in WORDS.values():
        win32gui.DrawText(hdc, "Salvar", -1, (x, y, x + 400, y + 80), win32con.DT_SINGLELINE | win32con.DT_NOCLIP)
    brush = win32gui.CreateSolidBrush(BLUE)
    win32gui.SetTextColor(hdc, win32api.RGB(255, 255, 255))
    for x, y in BUTTONS.values():
        rect = (x, y, x + BUTTON_SIZE[0], y + BUTTON_SIZE[1])
        win32gui.FillRect(hdc, rect, brush)
        win32gui.DrawText(hdc, "OK", -1, rect, win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)
    win32gui.DeleteObject(brush)
    win32gui.SelectObject(hdc, old)
    win32gui.EndPaint(hwnd, ps)


def _wndproc(hwnd, msg, wparam, lparam):
    if msg == win32con.WM_LBUTTONDOWN:
        _record(hwnd, lparam, 1)
        return 0
    if msg == win32con.WM_RBUTTONDOWN:
        _record(hwnd, lparam, 3)
        return 0
    if msg == win32con.WM_MOUSEWHEEL:
        with (state / "wheel.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"delta": _signed(wparam >> 16)}) + "\n")
        return 0
    if msg == win32con.WM_PAINT:
        _paint(hwnd)
        return 0
    if msg == win32con.WM_DESTROY:
        win32gui.PostQuitMessage(0)
        return 0
    return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)


def _text_box(hwnd: int, x: int, y: int) -> list[int]:
    hdc = win32gui.GetDC(hwnd)
    old = win32gui.SelectObject(hdc, FONT)
    _h, (left, top, right, bottom) = win32gui.DrawText(
        hdc, "Salvar", -1, (x, y, x + 400, y + 80), win32con.DT_SINGLELINE | win32con.DT_CALCRECT
    )
    win32gui.SelectObject(hdc, old)
    win32gui.ReleaseDC(hwnd, hdc)
    return [left, top, right - left, bottom - top]


wc = win32gui.WNDCLASS()
wc.lpfnWndProc = _wndproc
wc.lpszClassName = f"VisusClickTarget{os.getpid()}"
wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
wc.hInstance = win32api.GetModuleHandle(None)
atom = win32gui.RegisterClass(wc)
hwnd = win32gui.CreateWindowEx(
    win32con.WS_EX_TOPMOST, atom, title, win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE,
    240, 200, 620, 420, 0, 0, wc.hInstance, None,
)
edit = win32gui.CreateWindowEx(
    0, "EDIT", "Digite aqui",
    win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_BORDER | win32con.ES_AUTOHSCROLL,
    *FIELD, hwnd, 0, wc.hInstance, None,
)
win32gui.SendMessage(edit, win32con.WM_SETFONT, FONT, 1)
win32gui.UpdateWindow(hwnd)

ox, oy = win32gui.ClientToScreen(hwnd, (0, 0))
_l, _t, cw, ch = win32gui.GetClientRect(hwnd)
items = {name: _text_box(hwnd, x, y) for name, (x, y) in WORDS.items()}
items.update({name: [x, y, *BUTTON_SIZE] for name, (x, y) in BUTTONS.items()})
items["campo"] = list(FIELD)
(state / "ready.json").write_text(json.dumps({
    "pid": os.getpid(),
    "title": title,
    "edit_hwnd": int(edit),
    "canvas": [ox, oy, cw, ch],
    "items": {name: [ox + b[0], oy + b[1], b[2], b[3]] for name, b in items.items()},
}), encoding="utf-8")

win32gui.PumpMessages()
