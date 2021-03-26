import json
import os

from emoji import emojize

COLORS = {
    "black": (0, 0, 0, 255),
    "white": (255, 255, 255, 255),
}

USERNAME_COLORS = {
    "red": (255, 0, 0, 255),
    "purple": (100, 0, 200, 255),
}

# Stickers
STICKERS = {
    "hahaclassic": "CAACAgIAAxkBAAL1al7t3M55gfj6YTVuJuETd2ZttQY0AAL6AANWnb0KR976l3F0cQEaBA",
}

# Emoji
EMOJI = {
    "pistol": emojize(":pistol:", use_aliases=True),
    "fire": emojize(":fire:", use_aliases=True),
    "zzz": emojize(":zzz:", use_aliases=True),
    "party": emojize(":party_popper:", use_aliases=True),
    "dizzy": emojize(":dizzy_face:", use_aliases=True),
    "clock": emojize(":alarm_clock:", use_aliases=True),
    "check": emojize(":white_check_mark:", use_aliases=True),
    "scream": emojize(":scream:", use_aliases=True),
    "suprise": emojize(":open_mouth:", use_aliases=True),
    "thumbsup": emojize(":thumbsup:", use_aliases=True),
}

LEETCODE_LEVELS = {
    1: "easy",
    2: "medium",
    3: "hard",
}

USAGE_TEXT = """\
```
usage:
\t\t/in <hour> [<hours>]
\t\t/out <hour> [<hours>]

examples:
\t\t/in 18-21 23
\t\t/i 22 20-0
\t\t/out 23
\t\t/ou 23 22
\t\t/o 20-1 18
\t\t/in 19 /out 21

all existing games:
\t\t/in all
\t\t/out all
```
"""

DAYS_OFF = ["Wednesday", "Sunday"]

# Commands
COMMANDS = [
    ("chettam", "create new game or join existing one"),
    ("status", "show current status"),
    ("menu", "bot and user settings"),
    ("in", "join with argumnets"),
    ("out", "leave with argumnets"),
]

MAIN_HOURS = [18, 19, 20, 21, 22, 23, 0, 1]

# Timezones
COMMON_TIMEZONES = {
    "Europe/Amsterdam": "EU",
    "Europe/London": "UK",
    "Asia/Almaty": "KZ",
    "Asia/Atyrau": "KZ+1",
}

# Converstion states
MAIN_STATE, SECONDARY_STATE = range(2)

# Patterns
HOUR_MINUTE_PATTERN = "^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$"

# App variables
APP_URL = os.getenv("APP_URL")
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8443"))
TOKEN = os.getenv("TOKEN")
DB_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")
SENTRY_DSN = os.getenv("SENTRY_DSN")
ALLOWED_CHATS_INTERNAL = json.loads(os.getenv("ALLOWED_CHATS_INTERNAL"))
ALLOWED_CHATS_EXTERNAL = json.loads(os.getenv("ALLOWED_CHATS_EXTERNAL"))
DEBUG = os.getenv("DEBUG")
