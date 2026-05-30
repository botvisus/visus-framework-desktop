"""
Fast click-through Win32 layered overlay.

A frameless top-most window with ``WS_EX_TRANSPARENT`` so mouse input
falls through to whatever is underneath. It draws on absolute screen
coordinates, so it works over **any** host technology (native Win32,
WPF/WinUI, Java/Swing, Electron, browsers) -- there is no DOM/UI-tree
inspection, just GDI lines on top of the desktop.

Designed to be cheap: ~5 ms to show, daemon-threaded teardown, never
blocks the caller. Falls back gracefully (returns ``False``) on
non-Windows platforms so callers can chain a different overlay there.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import logging
import sys
import threading
import time

logger = logging.getLogger(__name__)

_IS_WIN = sys.platform == "win32"

if _IS_WIN:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    WS_POPUP = 0x80000000
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020
    WS_EX_TOPMOST = 0x00000008
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_NOACTIVATE = 0x08000000
    SW_SHOWNOACTIVATE = 4
    LWA_COLORKEY = 0x00000001
    PS_SOLID = 0
    NULL_BRUSH = 5
    BLACK_BRUSH = 4
    CS_HREDRAW = 0x0002
    CS_VREDRAW = 0x0001
    WM_QUIT = 0x0012
    PM_REMOVE = 0x0001
    # Text drawing constants (for the optional label on a numbered overlay).
    TRANSPARENT = 1
    FW_BOLD = 700
    DEFAULT_CHARSET = 1
    OUT_DEFAULT_PRECIS = 0
    CLIP_DEFAULT_PRECIS = 0
    DEFAULT_QUALITY = 0
    DEFAULT_PITCH = 0
    FF_DONTCARE = 0
    LABEL_FONT_HEIGHT = 22
    LABEL_BAND_HEIGHT = 28  # vertical room reserved above the rectangle
    # Pure black is the color-key — any black pixel in the window becomes
    # fully transparent, leaving only the drawn outline visible.
    COLOR_KEY = 0x000000

    LRESULT = ctypes.c_ssize_t
    HBRUSH = wintypes.HANDLE
    HICON = wintypes.HANDLE
    HCURSOR = wintypes.HANDLE
    HINSTANCE = wintypes.HANDLE

    WNDPROC = ctypes.WINFUNCTYPE(
        LRESULT,
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    )

    class WNDCLASSW(ctypes.Structure):
        _fields_ = [
            ("style", wintypes.UINT),
            ("lpfnWndProc", WNDPROC),
            ("cbClsExtra", ctypes.c_int),
            ("cbWndExtra", ctypes.c_int),
            ("hInstance", HINSTANCE),
            ("hIcon", HICON),
            ("hCursor", HCURSOR),
            ("hbrBackground", HBRUSH),
            ("lpszMenuName", wintypes.LPCWSTR),
            ("lpszClassName", wintypes.LPCWSTR),
        ]

    class MSG(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("message", wintypes.UINT),
            ("wParam", wintypes.WPARAM),
            ("lParam", wintypes.LPARAM),
            ("time", wintypes.DWORD),
            ("pt", wintypes.POINT),
        ]

    user32.DefWindowProcW.restype = LRESULT
    user32.DefWindowProcW.argtypes = [
        wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
    ]
    user32.RegisterClassW.restype = wintypes.ATOM
    user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
    user32.CreateWindowExW.restype = wintypes.HWND
    user32.CreateWindowExW.argtypes = [
        wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        wintypes.HWND, wintypes.HMENU, HINSTANCE, wintypes.LPVOID,
    ]
    user32.DestroyWindow.restype = wintypes.BOOL
    user32.DestroyWindow.argtypes = [wintypes.HWND]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.UpdateWindow.restype = wintypes.BOOL
    user32.UpdateWindow.argtypes = [wintypes.HWND]
    user32.SetLayeredWindowAttributes.restype = wintypes.BOOL
    user32.SetLayeredWindowAttributes.argtypes = [
        wintypes.HWND, wintypes.COLORREF, wintypes.BYTE, wintypes.DWORD,
    ]
    user32.GetDC.restype = wintypes.HDC
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.ReleaseDC.restype = ctypes.c_int
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user32.FillRect.restype = ctypes.c_int
    user32.FillRect.argtypes = [
        wintypes.HDC, ctypes.POINTER(wintypes.RECT), HBRUSH,
    ]
    user32.PeekMessageW.restype = wintypes.BOOL
    user32.PeekMessageW.argtypes = [
        ctypes.POINTER(MSG), wintypes.HWND,
        wintypes.UINT, wintypes.UINT, wintypes.UINT,
    ]
    user32.TranslateMessage.restype = wintypes.BOOL
    user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
    user32.DispatchMessageW.restype = LRESULT
    user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]

    gdi32.CreatePen.restype = wintypes.HANDLE
    gdi32.CreatePen.argtypes = [ctypes.c_int, ctypes.c_int, wintypes.COLORREF]
    gdi32.GetStockObject.restype = wintypes.HANDLE
    gdi32.GetStockObject.argtypes = [ctypes.c_int]
    gdi32.SelectObject.restype = wintypes.HANDLE
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
    gdi32.DeleteObject.restype = wintypes.BOOL
    gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
    gdi32.Rectangle.restype = wintypes.BOOL
    gdi32.Rectangle.argtypes = [
        wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    ]
    gdi32.MoveToEx.restype = wintypes.BOOL
    gdi32.MoveToEx.argtypes = [
        wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.LPVOID,
    ]
    gdi32.LineTo.restype = wintypes.BOOL
    gdi32.LineTo.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
    # Font / text drawing for the optional numeric label.
    gdi32.CreateFontW.restype = wintypes.HANDLE
    gdi32.CreateFontW.argtypes = [
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
        wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
        wintypes.DWORD, wintypes.LPCWSTR,
    ]
    gdi32.SetTextColor.restype = wintypes.COLORREF
    gdi32.SetTextColor.argtypes = [wintypes.HDC, wintypes.COLORREF]
    gdi32.SetBkMode.restype = ctypes.c_int
    gdi32.SetBkMode.argtypes = [wintypes.HDC, ctypes.c_int]
    gdi32.TextOutW.restype = wintypes.BOOL
    gdi32.TextOutW.argtypes = [
        wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.LPCWSTR, ctypes.c_int,
    ]

    kernel32.GetModuleHandleW.restype = HINSTANCE
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]

    @WNDPROC
    def _wnd_proc(hwnd, msg, wparam, lparam):
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    _CLASS_NAME = "VisusOverlayClickThrough"
    _class_lock = threading.Lock()
    _class_registered = False
    # Hold a strong reference to the WNDCLASSW so its lpfnWndProc callback
    # is not garbage-collected after RegisterClassW returns.
    _wndclass_holder = None


_COLORS_RGB = {
    "red": (255, 0, 0),
    "blue": (0, 128, 255),
    "green": (0, 255, 0),
    "yellow": (255, 255, 0),
    "purple": (128, 0, 128),
    "orange": (255, 128, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "white": (255, 255, 255),
    # Pure black would be eaten by the color-key. Bias by 1 so a "black"
    # request still draws something visible.
    "black": (1, 1, 1),
}


def _rgb_to_colorref(rgb):
    r, g, b = rgb
    return r | (g << 8) | (b << 16)


def _ensure_class_registered():
    global _class_registered, _wndclass_holder
    if _class_registered:
        return
    with _class_lock:
        if _class_registered:
            return
        wc = WNDCLASSW()
        wc.style = CS_HREDRAW | CS_VREDRAW
        wc.lpfnWndProc = _wnd_proc
        wc.cbClsExtra = 0
        wc.cbWndExtra = 0
        wc.hInstance = kernel32.GetModuleHandleW(None)
        wc.hIcon = None
        wc.hCursor = None
        wc.hbrBackground = gdi32.GetStockObject(BLACK_BRUSH)
        wc.lpszMenuName = None
        wc.lpszClassName = _CLASS_NAME
        atom = user32.RegisterClassW(ctypes.byref(wc))
        if not atom:
            err = ctypes.get_last_error()
            # ERROR_CLASS_ALREADY_EXISTS — a previous import already did it.
            if err != 1410:
                raise OSError(f"RegisterClassW failed (err={err})")
        _wndclass_holder = wc
        _class_registered = True


def _paint(
    hwnd, win_w, win_h, pad_left, pad_top,
    region_w, region_h, color_rgb, line_width, label,
):
    hdc = user32.GetDC(hwnd)
    if not hdc:
        return
    try:
        rect = wintypes.RECT(0, 0, win_w, win_h)
        user32.FillRect(
            hdc, ctypes.byref(rect), gdi32.GetStockObject(BLACK_BRUSH)
        )

        colorref = _rgb_to_colorref(color_rgb)
        pen = gdi32.CreatePen(PS_SOLID, line_width, colorref)
        if not pen:
            return
        old_pen = gdi32.SelectObject(hdc, pen)
        old_brush = gdi32.SelectObject(hdc, gdi32.GetStockObject(NULL_BRUSH))
        try:
            gdi32.Rectangle(
                hdc, pad_left, pad_top,
                pad_left + region_w, pad_top + region_h,
            )
            cx = pad_left + region_w // 2
            cy = pad_top + region_h // 2
            cross = max(2, min(10, region_w // 4, region_h // 4))
            gdi32.MoveToEx(hdc, cx - cross, cy, None)
            gdi32.LineTo(hdc, cx + cross, cy)
            gdi32.MoveToEx(hdc, cx, cy - cross, None)
            gdi32.LineTo(hdc, cx, cy + cross)
        finally:
            gdi32.SelectObject(hdc, old_pen)
            gdi32.SelectObject(hdc, old_brush)
            gdi32.DeleteObject(pen)

        # Optional numeric label drawn above the rectangle's top-left corner
        # in the same color. Sits inside the reserved top band so it never
        # eats into the highlighted region.
        if label:
            hfont = gdi32.CreateFontW(
                -LABEL_FONT_HEIGHT, 0, 0, 0, FW_BOLD,
                0, 0, 0,
                DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                DEFAULT_QUALITY, DEFAULT_PITCH | FF_DONTCARE, "Segoe UI",
            )
            if hfont:
                old_font = gdi32.SelectObject(hdc, hfont)
                try:
                    gdi32.SetTextColor(hdc, colorref)
                    gdi32.SetBkMode(hdc, TRANSPARENT)
                    text = str(label)
                    gdi32.TextOutW(
                        hdc, pad_left + 2, max(2, pad_top - LABEL_FONT_HEIGHT - 2),
                        text, len(text),
                    )
                finally:
                    gdi32.SelectObject(hdc, old_font)
                    gdi32.DeleteObject(hfont)
    finally:
        user32.ReleaseDC(hwnd, hdc)


def _overlay_worker(region, color, line_width, duration_ms, label):
    x, y, w, h = region
    line_width = max(1, int(line_width))
    pad = max(line_width, 2)
    # If a label is present, reserve a band above the rectangle for the
    # text. Otherwise pad symmetrically.
    pad_left = pad
    pad_right = pad
    pad_bottom = pad
    pad_top = max(pad, LABEL_BAND_HEIGHT) if label else pad
    win_x = x - pad_left
    win_y = y - pad_top
    win_w = w + pad_left + pad_right
    win_h = h + pad_top + pad_bottom

    try:
        _ensure_class_registered()
    except OSError as e:
        logger.debug(f"Overlay class registration failed: {e}")
        return

    rgb = _COLORS_RGB.get(color.lower(), _COLORS_RGB["red"])

    ex_style = (
        WS_EX_LAYERED
        | WS_EX_TRANSPARENT
        | WS_EX_TOPMOST
        | WS_EX_TOOLWINDOW
        | WS_EX_NOACTIVATE
    )

    hwnd = user32.CreateWindowExW(
        ex_style,
        _CLASS_NAME,
        None,
        WS_POPUP,
        win_x, win_y, win_w, win_h,
        None, None, kernel32.GetModuleHandleW(None), None,
    )
    if not hwnd:
        logger.debug(f"CreateWindowExW failed (err={ctypes.get_last_error()})")
        return

    try:
        user32.SetLayeredWindowAttributes(hwnd, COLOR_KEY, 0, LWA_COLORKEY)
        user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
        _paint(
            hwnd, win_w, win_h, pad_left, pad_top,
            w, h, rgb, line_width, label,
        )
        user32.UpdateWindow(hwnd)

        end_ts = time.monotonic() + duration_ms / 1000.0
        msg = MSG()
        while time.monotonic() < end_ts:
            while user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, PM_REMOVE):
                if msg.message == WM_QUIT:
                    return
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            time.sleep(0.01)
    finally:
        user32.DestroyWindow(hwnd)


def show_click_through_overlay(
    region: tuple[int, int, int, int],
    color: str = "red",
    width: int = 4,
    duration_ms: int = 1000,
    label: str | None = None,
) -> bool:
    """Display a click-through topmost overlay rectangle.

    The window uses ``WS_EX_TRANSPARENT``, so the click that follows passes
    straight through to the host below -- including Java apps, browsers,
    Electron, etc. Returns immediately; the overlay tears itself down in a
    daemon thread after ``duration_ms``.

    When ``label`` is given, a bold colored caption (e.g. ``"1"``, ``"2"``)
    is drawn just above the rectangle's top-left corner so the caller can
    number multiple occurrences on screen.

    Returns ``True`` if the overlay was scheduled, ``False`` if this
    platform is unsupported (non-Windows) so the caller can fall back.
    """
    if not _IS_WIN:
        return False
    threading.Thread(
        target=_overlay_worker,
        args=(
            region,
            color,
            max(1, int(width)),
            max(50, int(duration_ms)),
            label,
        ),
        daemon=True,
        name="VisusOverlay",
    ).start()
    return True
