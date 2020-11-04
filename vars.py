import argparse
import json
import os
import random

import pytz
from emoji import emojize


def arg_parse():
    """Parses command line arguments"""
    parser = argparse.ArgumentParser(description="args")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


# Stickers
STICKERS = {
    "coffee_parrot": "CAACAgIAAxkBAAL0iF7r4SfAEYdYrTVkMXYiHXqYEA1cAAL5AgAChmBXDp2WPdbev1lCGgQ",
    "pistol_parrot": "CAACAgIAAxkBAAIJrF8yOnVN-0osZOUFf8Frf0RakGLZAAIMOwAC6VUFGNYFnNP4oeCaGgQ",
    "pistol_duck_left": "CAACAgIAAxkBAAIJr18yOnuVSZ1vAr2mtkPa2CWk2p8AA14AA6quUgRDa8fZOTT8_RoE",
    "pistol_duck_right": "CAACAgIAAxkBAAIJsl8yOn1xC5EcbE6CYNL-EsEt_9wTAAKRAAOqrlIEnpWDdp5WX-caBA",
    "racoon": "CAACAgIAAxkBAAL1cF7t3YatTs3VWK3xR0fbpRPW9vB5AAKMBgAC-gu2CPxnxUG2V7CeGgQ",
    "hahaclassic": "CAACAgIAAxkBAAL1al7t3M55gfj6YTVuJuETd2ZttQY0AAL6AANWnb0KR976l3F0cQEaBA",
    "lenin": "CAACAgIAAxkBAAL1bF7t3V3P7PGfi-AGPfBvuudGFE-BAAKyAQADOKAK3daY89Zw03oaBA",
    "borat": "CAACAgIAAxkBAAL1bl7t3WTXnaw2bDVUAddB91Mc3mY6AAJJCgACLw_wBgX8BGoorU2iGgQ",
    "harry": "CAACAgMAAxkBAAL1cl7t3jZN6_vbGKu3dRQv7J55p9G7AAK3BQACv4yQBCGrZtOhEOmVGgQ",
    "sheikh": "CAACAgIAAxkBAAL1dF7t3mPeoSK1LclyivuIksnN90zqAAL1BQAClvoSBcZ_YHxtJ4JzGgQ",
}

# Emoji
EMOJI = {
    "pistol": emojize(":pistol:", use_aliases=True),
    "knife": emojize(":dagger:", use_aliases=True),
    "axe": emojize(":axe:", use_aliases=True),
    "bolt": emojize(":high_voltage:", use_aliases=True),
    "fire": emojize(":fire:", use_aliases=True),
    "rocket": emojize(":rocket:", use_aliases=True),
    "cross": emojize(":x:", use_aliases=True),
    "pencil": emojize(":pencil:", use_aliases=True),
    "scroll": emojize(":scroll:", use_aliases=True),
    "chart": emojize(":bar_chart:", use_aliases=True),
    "cry": emojize(":cry:", use_aliases=True),
    "zzz": emojize(":zzz:", use_aliases=True),
    "coffee": emojize(":coffee:", use_aliases=True),
    "party": emojize(":party_popper:", use_aliases=True),
    "dizzy": emojize(":dizzy_face:", use_aliases=True),
    "angry": emojize(":angry_face:", use_aliases=True),
    "clock": emojize(":alarm_clock:", use_aliases=True),
    "collision": emojize(":collision:", use_aliases=True),
    "exclamation": emojize(":exclamation:", use_aliases=True),
    "bangbang": emojize(":double_exclamation_mark:", use_aliases=True),
    "dumpling": emojize(":dumpling:", use_aliases=True),
    "tiger": emojize(":tiger2:", use_aliases=True),
    "check": emojize(":white_check_mark:", use_aliases=True),
    "ok": emojize(":ok:", use_aliases=True),
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

# Chettam mating calls
INVITE = [
    "четтам?",
    "че там гоу ма?",
    "чё там, сегодня го?",
    "Че гоу катка?",
    "Че там? Гоу???",
    "Че там?",
    "che tam ? go ?",
    "ну че там?",
    "можно катку",
    "1 Катку может?",
    "Че там, early катка?",
    "Я готов, есть слот?",
    "слот не слот, я готов если что.",
    "Занимаю слот",
    "Слот бар ма?",
    "Наливаю чай",
    "ехала!",
    "го го",
    "GOGO!",
    "го седня, надо инет затестить новый",
    "Че там плов будет?",
    "Гоу сегодня мираж катать?",
    "иферно и вертиго сегодня",
    "Я короче сегодня занимаю слот на инферно за СТ на Б",
    "прицел на уровне головы держу всегда.",
    "дроп скиньте",
    "Кто катает",
    "Мышку надо опробовать",
    "kto ewe ho4et join?",
    "sobiraus’ sei4as katnut’",
    "Я фейсит поставил миллион лет назад",
    "Интернет поставил",
    "Я сегодня как раз звезду солью",
    "По разам шыгасынба",
    "Гоу вечерком на банане доски красить?",
    "Келеci «Пирожковая» аялдамасы",
    "пирожки распечатал",
]

# Action triggers
BCOM = [
    f"Top party: Highly rated by recent gamers ({round(random.uniform(7, 10), 1)})!",
    f"Good for gamers - they rate the party {round(random.uniform(7, 10), 1)} for five-person plays!",
    "Last booked 1 hour ago on our chat!",
    "Booked 4 times in the last 6 hours on our chat!",
    "Limited-time deal!",
    "Only 1 slot left on our chat!",
    "2 other people looked for your slot in the last 10 minutes!",
    "FREE cancellation!",
    "One of our bestsellers in CS:GO!",
    "Gamers consistently rate the party as excellent!",
]

DAYS_OFF = ["Wednesday", "Sunday"]

# Commands
COMMANDS = [
    ("chettam", "create new game or join existing one"),
    ("status", "show current status"),
    ("gogo", "say random invite"),
]

COMMANDS_NAMES_ONLY = [command[0] for command in COMMANDS]

# Commands string for START_MESSAGE
COMMANDS_DESCR = "\n".join(
    f"/{command} - {description}" for command, description in COMMANDS
)

# Reply to /start command
START_MESSAGE = f"""
Hi, this is a bot for chettam guys! {EMOJI["pistol"]}
{", ".join(DAYS_OFF)} are days off.

{COMMANDS_DESCR}
"""

# Timezones
TIMEZONE_CET = pytz.timezone("CET")
TIMEZONE_UTC = pytz.timezone("UTC")

# Converstion states
MAIN_STATE, SECONDARY_STATE = range(2)

# Patterns
HOUR_PATTERN = "^(0[0-9]|1[0-9]|2[0-3])$"
HOUR_MINUTE_PATTERN = "^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$"

# App variables
HEROKU_APP = "https://chettam-telegram-bot.herokuapp.com/"
PORT = int(os.environ.get("PORT", "8443"))

if arg_parse().debug:
    # dev vars
    DEBUG = True
    TOKEN = os.getenv("TOKEN_DEBUG")
    DB_URL = os.getenv("HEROKU_POSTGRESQL_COPPER_URL")
    SENTRY_DSN = os.getenv("SENTRY_DSN_DEBUG")
else:
    # prod vars
    DEBUG = False
    TOKEN = os.getenv("TOKEN")
    DB_URL = os.getenv("DATABASE_URL")
    SENTRY_DSN = os.getenv("SENTRY_DSN")
    ALLOWED_CHATS = json.loads(os.getenv("ALLOWED_CHATS"))
