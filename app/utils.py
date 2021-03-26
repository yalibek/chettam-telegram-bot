import json
import logging
import random
from datetime import datetime as dt, timedelta

import pandas as pd
import pytz
import requests

from app.models import Game, Player, session, Association
from app.vars import (
    EMOJI,
    DAYS_OFF,
    DEBUG,
    LEETCODE_LEVELS,
    COMMON_TIMEZONES,
)


def row_list_chunks(lst, min_row_size=4, row_amount=2) -> list:
    """
    Split given list into {row_amount} of chunks, with first part rounded to upper int.
    example:
        lst = [1,2,3,4,5,6,7] =>> result = [[1,2,3,4],[5,6,7]]
    """
    lst = list(lst)
    lst_size = len(lst)
    if lst_size <= min_row_size:
        return [lst]
    else:
        step = (lst_size // row_amount) + (lst_size % row_amount)
        return [lst[item : item + step] for item in range(0, lst_size, step)]


def sync_player_data(player: Player, user):
    """Updates player's data with Telegram user's data if it has changed"""
    p_data = [player.username, player.first_name, player.last_name]
    u_data = [user.username, user.first_name, user.last_name]
    if p_data != u_data:
        player.username, player.first_name, player.last_name = u_data
        player.save()


def player_query(player_id):
    return session.query(Player).filter_by(id=player_id).first()


def get_player(update) -> Player:
    """Returns Player model for current user"""
    user = update.effective_user
    player = session.query(Player).filter_by(user_id=user.id).first()
    if player:
        sync_player_data(player, user)
    else:
        player = Player(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )
        player.create()
    return player


def convert_to_dt(timeslot, timezone) -> dt:
    """Converts time into datetime object in UTC timezone"""
    time = dt.strptime(timeslot, "%H:%M")
    now = dt.now(tz=timezone)

    is_daytime = now.hour >= 4
    is_night_game = time.hour < 4

    if is_daytime and is_night_game:
        day = now.date() + timedelta(days=1)
    else:
        day = now.date()

    date_time = f"{day} {time.hour}:{time.minute}"
    timeslot_obj = dt.strptime(date_time, "%Y-%m-%d %H:%M")
    timeslot_localized = timezone.localize(timeslot_obj)
    return timeslot_localized.astimezone(pytz.utc)


def create_game(chat, timeslot) -> Game:
    """Creates new game"""
    game = Game(
        timeslot=timeslot,
        chat_id=chat.id,
        chat_type=chat.type,
    )
    game.create()
    return game


def game_timediff(game: Game, hours=0, minutes=0) -> bool:
    """Checks if game is older than given time frame"""
    now = dt.now(pytz.utc)
    timeslot = game.timeslot_utc
    delta = timedelta(hours=hours, minutes=minutes)
    return now - timeslot > delta


def get_game(chat_id, game_id=None, timeslot=None) -> Game:
    """Returns Game model for current chat"""
    if game_id:
        return (
            session.query(Game)
            .filter_by(id=game_id, chat_id=chat_id, expired=False)
            .first()
        )
    elif timeslot:
        return (
            session.query(Game)
            .filter_by(timeslot=timeslot, chat_id=chat_id, expired=False)
            .first()
        )


def get_all_data(chat_id):
    """Returns all data for current chat in form of Pandas DataFrame"""
    query = (
        session.query(Association, Player, Game)
        .join(Player)
        .join(Game)
        .filter(Game.chat_id == chat_id)
        .statement
    )
    return pd.read_sql(query, session.bind)


def get_assoc(game_id, player_id) -> Association:
    """Returns Association model for current game/player pair"""
    return (
        session.query(Association)
        .filter_by(game_id=game_id, player_id=player_id)
        .first()
    )


def get_all_games(update, ts_only=False) -> list:
    """Returns all Game models for current chat"""
    games = (
        session.query(Game)
        .filter_by(chat_id=update.effective_chat.id, expired=False)
        .order_by(Game.timeslot)
        .all()
    )
    if ts_only:
        return [game.timeslot_utc for game in games]
    else:
        return games


def get_time_header(game, timezone):
    """Returns timeslot in given timezone"""
    time = game.timeslot_utc.astimezone(timezone).strftime("%H:%M")
    tz_code = COMMON_TIMEZONES[str(timezone)]
    return f"{time} {tz_code}"


def slot_time_header(game, timezone) -> str:
    """Returns timeslots with timezones for all players in the game"""
    main_tz = timezone
    main_tz_header = get_time_header(game, main_tz)
    secondary_tz = set(player.timezone_pytz for player in game.players_sorted)
    secondary_tz.discard(main_tz)
    if secondary_tz:
        secondary_tz_header = ", ".join(
            get_time_header(game, tz) for tz in secondary_tz
        )
        return f"{main_tz_header} ({secondary_tz_header})"
    else:
        return main_tz_header


def slot_status(game, timezone) -> str:
    """Returns slots data for game"""
    slots = game.slots
    players = game.players_list
    time_header = slot_time_header(game, timezone)
    pistol = EMOJI["pistol"]
    if 5 <= slots < 10:
        reply = f"Full party! {pistol}"
    elif slots >= 10:
        reply = f"5x5! {pistol}{pistol}"
    else:
        reply = ""
    return f"*{time_header}*: {reply}\n{players}"


def slot_status_all(games, timezone) -> str:
    """Returns slots data for all games"""
    return "\n\n".join(slot_status(game, timezone) for game in games)


def is_dayoff() -> bool:
    """Checks if today is cs:go dayoff"""
    if DEBUG:
        # It's never a day off in dev mode
        return False
    else:
        # Day off starts at 4am UTC
        now = dt.now(pytz.utc)
        is_off = now.strftime("%A") in DAYS_OFF
        is_daytime = now.hour >= 4
        return is_off and is_daytime


def logger() -> logging.Logger:
    """Enables logging"""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    return logging.getLogger(__name__)


def chop(word):
    """
    Chops the word by letters
    example:
        "chettam" =>> ["c", "ch", "che", "chet", "chett", "chetta", "chettam"]
    """
    return [word[0 : idx + 1] for idx, i in enumerate(word)]


def get_leetcode_problem() -> str:
    """Returns url to random leetcode problem"""
    response = requests.get(
        url="https://leetcode.com/api/problems/all/",
        headers={"User-Agent": "Python", "Connection": "keep-alive"},
        timeout=10,
    )
    data = json.loads(response.content.decode("utf-8"))
    all_problems = [
        problem
        for problem in data["stat_status_pairs"]
        if not problem["paid_only"] and not problem["stat"]["question__hide"]
    ]
    random_problem = random.choice(all_problems)
    difficulty = LEETCODE_LEVELS[random_problem["difficulty"]["level"]]
    title_slug = random_problem["stat"]["question__title_slug"]
    url = f"https://leetcode.com/problems/{title_slug}"
    submitted = random_problem["stat"]["total_submitted"]
    accepted = random_problem["stat"]["total_acs"]
    acceptance_rate = round(accepted / submitted * 100, 1)
    if acceptance_rate < 40:
        reaction = EMOJI["scream"]
    elif acceptance_rate < 70:
        reaction = EMOJI["suprise"]
    else:
        reaction = EMOJI["thumbsup"]
    return f"{reaction} Only *{acceptance_rate}%* can solve this *{difficulty}* problem!\n\n{url}"
