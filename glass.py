"""Windows DWM glass effects — multi-tier approach for Win10/Win11."""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import platform

# ── DWM attributes ───────────────────────────────────────────────────────────
DWMWA_USE_IMMERSIVE_DARK_MODE   = 20
DWMWA_WINDOW_CORNER_PREFERENCE  = 33
DWMWCP_ROUND                    = 2
DWMWA_SYSTEMBACKDROP_TYPE       = 38
DWMSBT_TRANSIENTWINDOW          = 3   # Acrylic

# ── SetWindowCompositionAttribute ────────────────────────────────────────────
WCA_ACCENT_POLICY                = 19
ACCENT_ENABLE_ACRYLICBLURBEHIND  = 4
ACCENT_ENABLE_BLURBEHIND         = 3


class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState",   ctypes.c_int),
        ("AccentFlags",   ctypes.c_int),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId",   ctypes.c_int),
    ]


class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [
        ("Attribute",  ctypes.c_int),
        ("Data",       ctypes.POINTER(ACCENT_POLICY)),
        ("SizeOfData", ctypes.c_size_t),
    ]


class MARGINS(ctypes.Structure):
    _fields_ = [
        ("cxLeftWidth",    ctypes.c_int),
        ("cxRightWidth",   ctypes.c_int),
        ("cyTopHeight",    ctypes.c_int),
        ("cyBottomHeight", ctypes.c_int),
    ]


dwmapi  = ctypes.windll.dwmapi
user32  = ctypes.windll.user32


def get_windows_build() -> int:
    try:
        return int(platform.version().split(".")[-1])
    except Exception:
        return 0


def _extend_frame(hwnd: int) -> None:
    margins = MARGINS(-1, -1, -1, -1)
    dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))


def _set_dark_mode(hwnd: int) -> None:
    val = ctypes.c_int(1)
    dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                                  ctypes.byref(val), ctypes.sizeof(val))


def _set_rounded_corners(hwnd: int) -> None:
    val = ctypes.c_int(DWMWCP_ROUND)
    dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
                                  ctypes.byref(val), ctypes.sizeof(val))


def _try_dwm_acrylic(hwnd: int) -> bool:
    """Win11 22H2+: native Acrylic via DwmSetWindowAttribute."""
    val = ctypes.c_int(DWMSBT_TRANSIENTWINDOW)
    hr = dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_SYSTEMBACKDROP_TYPE,
                                       ctypes.byref(val), ctypes.sizeof(val))
    return hr == 0


def _try_swca_acrylic(hwnd: int, tint: int = 0x01000000) -> bool:
    """SetWindowCompositionAttribute Acrylic (Win10 / fallback)."""
    accent = ACCENT_POLICY()
    accent.AccentState   = ACCENT_ENABLE_ACRYLICBLURBEHIND
    accent.AccentFlags   = 2
    accent.GradientColor = tint  # nearly transparent tint → see-through

    data = WINDOWCOMPOSITIONATTRIBDATA()
    data.Attribute  = WCA_ACCENT_POLICY
    data.Data       = ctypes.pointer(accent)
    data.SizeOfData = ctypes.sizeof(accent)

    try:
        return user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data)) != 0
    except (AttributeError, OSError):
        return False


def _try_swca_blur(hwnd: int) -> bool:
    """Plain DWM blur (no tint) — last resort."""
    accent = ACCENT_POLICY()
    accent.AccentState = ACCENT_ENABLE_BLURBEHIND

    data = WINDOWCOMPOSITIONATTRIBDATA()
    data.Attribute  = WCA_ACCENT_POLICY
    data.Data       = ctypes.pointer(accent)
    data.SizeOfData = ctypes.sizeof(accent)

    try:
        return user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data)) != 0
    except (AttributeError, OSError):
        return False


def apply_glass(hwnd: int, build: int) -> str:
    """Apply best available glass effect. Returns the method that succeeded."""
    _extend_frame(hwnd)
    _set_dark_mode(hwnd)

    if build >= 22000:
        _set_rounded_corners(hwnd)

    # Tier 1: Win11 native Acrylic
    if build >= 22621 and _try_dwm_acrylic(hwnd):
        return "dwm_acrylic"

    # Tier 2: SWCA Acrylic (very transparent tint so blur dominates)
    if _try_swca_acrylic(hwnd, tint=0x01000000):
        return "swca_acrylic"

    # Tier 3: plain blur
    if _try_swca_blur(hwnd):
        return "swca_blur"

    return "none"
