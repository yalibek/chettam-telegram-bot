import argparse
import json
import os

import pytz
from emoji import emojize


def arg_parse():
    """Parses command line arguments"""
    parser = argparse.ArgumentParser(description="args")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


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

USER_TIMEZONES = {
    "timuber": "Europe/London",
    "sduwnik": "Europe/London",
    "anchik12345": "Europe/London",
}

# CS:GO nicknames
CSGO_NICKNAMES = {
    "aman_utemuratov": "amanchik",
    "rbektemirov": "iceman",
    "DaurenMuratov": "Paradox",
    # "macaskar": "macaskar",
    "JustLiveKZ": "JustLiveKZ",
    "mrserzhan": "gPaKoH",
    "madrobothere": "madrobot",
    "sduwnik": "bekzattt",
    "ideamod": "aim_morty",
    "omniscient_otter": "snoepdoggo",
    # "sanzhar_satybaldiyev": "sanzhar_satybaldiyev",
    "FreeUserName": "AWK",
    "timazhum": "TimaZhumTTV",
    "askhatish": "askhatish",
    "datbayev": "megido",
    "Raimundoo": "Raimundo",
    "timuber": "xx",
    "alibekxo": "uber eats",
    # "narikbi": "narikbi",
    # "kaskabayev": "kaskabayev",
    "umriyaev": "kingler_s",
    "rjlth": "Юрист",
    "tabdulin": "tabdulin",
    "dakzh": "dake2020",
    # "kushibayev": "kushibayev",
    "msagimbekov": "Məké",
    "anchik12345": "monster",
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
\t\t/in 21 22
\t\t/i 22 20 0
\t\t/out 23
\t\t/ou 23 22
\t\t/o 20 1

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
    ("in", "join with argumnets"),
    ("out", "leave with argumnets"),
    ("data", "get all player data"),
]

MAIN_HOURS = [18, 19, 20, 21, 22, 23, 0, 1]

# Timezones
TIMEZONE_CET = pytz.timezone("CET")
TIMEZONE_UTC = pytz.timezone("UTC")

# Converstion states
MAIN_STATE, SECONDARY_STATE = range(2)

# Patterns
HOUR_MINUTE_PATTERN = "^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$"

# App variables
APP_URL = os.getenv("APP_URL")
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8443"))

if arg_parse().debug:
    # dev vars
    DEBUG = True
    TOKEN = os.getenv("TOKEN_DEBUG")
    DB_URL = os.getenv("HEROKU_POSTGRESQL_COPPER_URL")
    SENTRY_DSN = os.getenv("SENTRY_DSN_DEBUG")
    ALLOWED_CHATS = ""
else:
    # prod vars
    DEBUG = False
    TOKEN = os.getenv("TOKEN")
    DB_URL = os.getenv("DATABASE_URL")
    SENTRY_DSN = os.getenv("SENTRY_DSN")
    ALLOWED_CHATS = json.loads(os.getenv("ALLOWED_CHATS"))
