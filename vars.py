import argparse
import os

import pytz
from emoji import emojize


# Parses command line arguments
def arg_parse():
    parser = argparse.ArgumentParser(description="args")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


# Emojis
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
    "можно катку.",
    "1 Катку может?",
    "Че там, early катка?",
    "Я готов, есть слот?",
    "слот не слот, я готов если что.",
    "Занимаю слот.",
    "Слот бар ма?",
    "Наливаю чай.",
    "ехала!",
    "го го.",
    "++",
    "GOGO!",
    "го седня, надо инет затестить новый.",
    "Че там плов будет?",
    "Гоу сегодня мираж катать?",
    "иферно и вертиго сегодня.",
    "Я короче сегодня занимаю слот на инферно за СТ на Б.",
    "Uninstalling CS:GO...",
    "прицел на уровне головы держу всегда.",
    "дроп скиньте.",
    "Кто катает.",
    "Мышку надо опробовать.",
]

# Timezones
TIMEZONE_CET = pytz.timezone("CET")
TIMEZONE_UTC = pytz.timezone("UTC")

# Stages
FIRST_STAGE, SECOND_STAGE = range(2)

# Patterns
HOUR_PATTERN = "^(0[0-9]|1[0-9]|2[0-3])$"
HOUR_MINUTE_PATTERN = "^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$"

# App variables
HEROKU_APP = "https://chettam-telegram-bot.herokuapp.com/"
PORT = int(os.environ.get("PORT", "8443"))

if arg_parse().debug:
    DEBUG = True
    TOKEN = os.getenv("TOKEN_DEBUG")
    DB_URL = os.getenv("HEROKU_POSTGRESQL_COPPER_URL")
else:
    DEBUG = False
    TOKEN = os.getenv("TOKEN")
    DB_URL = os.getenv("DATABASE_URL")
