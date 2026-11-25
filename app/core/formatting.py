"""Human friendly formatting helpers (Russian)."""
from __future__ import annotations

from datetime import datetime, timedelta

APP_LABELS = {
    "chrome.exe": "Google Chrome",
    "msedge.exe": "Microsoft Edge",
    "firefox.exe": "Firefox",
    "opera.exe": "Opera",
    "brave.exe": "Brave",
    "yandex.exe": "Яндекс Браузер",
    "code.exe": "Visual Studio Code",
    "devenv.exe": "Visual Studio",
    "pycharm64.exe": "PyCharm",
    "idea64.exe": "IntelliJ IDEA",
    "explorer.exe": "Проводник",
    "winword.exe": "Microsoft Word",
    "excel.exe": "Microsoft Excel",
    "powerpnt.exe": "PowerPoint",
    "outlook.exe": "Outlook",
    "telegram.exe": "Telegram",
    "discord.exe": "Discord",
    "slack.exe": "Slack",
    "whatsapp.exe": "WhatsApp",
    "spotify.exe": "Spotify",
    "vlc.exe": "VLC",
    "notepad.exe": "Блокнот",
    "notepad++.exe": "Notepad++",
    "cmd.exe": "Командная строка",
    "windowsterminal.exe": "Windows Terminal",
    "powershell.exe": "PowerShell",
    "steam.exe": "Steam",
    "steamwebhelper.exe": "Steam",
    "taskmgr.exe": "Диспетчер задач",
    "snippingtool.exe": "Ножницы",
    "fidexe.exe": "FIDEXE",
    "figma.exe": "Figma",
    "photoshop.exe": "Photoshop",
    "acrobat.exe": "Acrobat Reader",
    "zoom.exe": "Zoom",
    "ms-teams.exe": "Microsoft Teams",
}


def app_label(process: str) -> str:
    if not process:
        return "Неизвестно"
    key = process.lower()
    if key in APP_LABELS:
        return APP_LABELS[key]
    stem = key[:-4] if key.endswith(".exe") else key
    return stem[:1].upper() + stem[1:]


def app_initials(process: str) -> str:
    label = app_label(process)
    parts = [p for p in label.replace(".", " ").split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()


def format_duration(seconds: float, *, compact: bool = False) -> str:
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if compact:
        if hours:
            return f"{hours} ч {minutes:02d} м"
        if minutes:
            return f"{minutes} м"
        return f"{secs} с"
    if hours:
        return f"{hours} ч {minutes} мин"
    if minutes:
        return f"{minutes} мин"
    return f"{secs} сек"


def format_clock(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes = rem // 60
    return f"{hours}:{minutes:02d}"


def relative_time(ts: int) -> str:
    now = datetime.now()
    moment = datetime.fromtimestamp(ts)
    delta = now - moment
    secs = delta.total_seconds()
    if secs < 45:
        return "только что"
    if secs < 3600:
        minutes = int(secs // 60)
        return f"{minutes} мин назад"
    if moment.date() == now.date():
        return f"сегодня в {moment:%H:%M}"
    if moment.date() == (now - timedelta(days=1)).date():
        return f"вчера в {moment:%H:%M}"
    if now.year == moment.year:
        return f"{moment:%d.%m в %H:%M}"
    return f"{moment:%d.%m.%Y}"


def short_title(title: str, app: str = "", limit: int = 90) -> str:
    title = (title or "").strip()
    if app:
        for sep in (" - ", " — ", " – ", " | "):
            if f"{sep}{app_label(app)}" in title:
                title = title.split(f"{sep}{app_label(app)}")[0]
                break
    title = " ".join(title.split())
    return title[:limit] + ("…" if len(title) > limit else "")


def plural_ru(number: int, one: str, few: str, many: str) -> str:
    n = abs(number) % 100
    if 11 <= n <= 14:
        return many
    n %= 10
    if n == 1:
        return one
    if 2 <= n <= 4:
        return few
    return many
