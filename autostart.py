"""Windows autostart via HKCU\\Run registry key (no admin required)."""

import sys
import winreg

REG_PATH = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "ClaudeHappyHours"


def _exe_path() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    return str(__file__)


def enable() -> None:
    path = _exe_path()
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{path}"')
    winreg.CloseKey(key)


def disable() -> None:
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE)
    try:
        winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass
    winreg.CloseKey(key)


def is_enabled() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
