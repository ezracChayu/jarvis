"""
Computer control skills — JARVIS's ability to interact with the Windows PC.
All functions return a string result that Claude will relay to the user.
"""
import subprocess
import webbrowser
import datetime
import asyncio
import psutil


APP_MAP = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "spotify": "spotify.exe",
    "word": "winword.exe",
    "excel": "excel.exe",
    "vs code": "code",
    "vscode": "code",
    "terminal": "wt.exe",
    "cmd": "cmd.exe",
    "task manager": "taskmgr.exe",
    "paint": "mspaint.exe",
}


async def open_application(app_name: str) -> str:
    normalized = app_name.lower().strip()
    exe = APP_MAP.get(normalized, normalized)
    try:
        subprocess.Popen(exe, shell=True)
        return f"Opened {app_name}."
    except Exception as e:
        return f"Could not open {app_name}: {e}"


async def web_search(query: str) -> str:
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    webbrowser.open(url)
    return f"Searching Google for: {query}"


async def get_system_info() -> str:
    now = datetime.datetime.now().strftime("%A, %B %d %Y — %H:%M")
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    ram_used = ram.used // (1024 ** 2)
    ram_total = ram.total // (1024 ** 2)

    battery = ""
    if hasattr(psutil, "sensors_battery") and psutil.sensors_battery():
        b = psutil.sensors_battery()
        battery = f"\nBattery: {b.percent:.0f}% {'(charging)' if b.power_plugged else '(on battery)'}"

    return (
        f"Time: {now}\n"
        f"CPU: {cpu}%\n"
        f"RAM: {ram_used} MB / {ram_total} MB{battery}"
    )
