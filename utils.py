import json
import logging
import random
from datetime import datetime as dt, timedelta

import pytz
import requests

from models import Game, Player, session, Association
from vars import (
    EMOJI,
    TIMEZONE_CET,
    TIMEZONE_UTC,
    CSGO_NICKNAMES,
    USER_TIMEZONES,
    DAYS_OFF,
    DEBUG,
    LEETCODE_LEVELS,
)


def row_list_chunks(lst) -> list:
    """
    Split given list into 2 n-sized chunks, with first part rounded to upper int
    example:
        lst = [1,2,3,4,5,6,7] =>> result = [[1,2,3,4],[5,6,7]]
    """
    lst_size = len(lst)
    one_row_size = 4
    if lst_size <= one_row_size:
        n = one_row_size
    else:
        n = (lst_size // 2) + (lst_size % 2)
    result = []
    for i in range(0, lst_size, n):
        result.append(lst[i : i + n])
    return result


def get_nickname(user) -> str:
    """Get CG:GO nickname for given user if it exist"""
    try:
        return CSGO_NICKNAMES[user.username]
    except:
        pass


def sync_player_data(player: Player, user):
    """Updates player's data with Telegram user's data if it has changed"""
    p_data = [player.username, player.first_name, player.last_name]
    u_data = [user.username, user.first_name, user.last_name]
    if p_data != u_data:
        player.username, player.first_name, player.last_name = u_data
        player.save()
    if not player.csgo_nickname:
        player.csgo_nickname = get_nickname(user)


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
            csgo_nickname=get_nickname(user),
        )
        player.create()
    return player


def convert_to_dt(timeslot) -> dt:
    """Converts time into datetime object in UTC timezone"""
    time = dt.strptime(timeslot, "%H:%M")
    date_today = dt.now(pytz.utc).date()

    if time.hour in range(4):
        day = date_today + timedelta(days=1)
    else:
        day = date_today

    date_time = f"{day} {time.hour}:{time.minute}"
    timeslot_obj = dt.strptime(date_time, "%Y-%m-%d %H:%M")
    timeslot_cet = TIMEZONE_CET.localize(timeslot_obj)
    return timeslot_cet.astimezone(TIMEZONE_UTC)


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
        return session.query(Game).filter_by(chat_id=chat_id, id=game_id).first()
    elif timeslot:
        return session.query(Game).filter_by(chat_id=chat_id, timeslot=timeslot).first()


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
        .filter_by(chat_id=update.effective_chat.id)
        .order_by(Game.timeslot)
        .all()
    )
    games_list = []
    for game in games:
        if game_timediff(game, hours=1, minutes=30):
            game.delete()
            continue
        elif game_timediff(game, minutes=30):
            game.expired = True
            game.save()
        games_list.append(game)
    if ts_only:
        return [game.timeslot_utc for game in games_list]
    else:
        return games_list


def slot_time_header(game) -> str:
    timeslot_cet = utc_to_tz_time(game, "CET")
    timeslot_gbt = utc_to_tz_time(game, "Europe/London")
    should_add_gbt_time = False
    for player in game.players:
        if player.username in USER_TIMEZONES:
            should_add_gbt_time = True
            break
    result = timeslot_cet
    if should_add_gbt_time:
        result = f"{timeslot_cet} (UK {timeslot_gbt})"
    return result


def utc_to_tz_time(game, timezone_str) -> str:
    utc_time = game.timeslot_utc
    timezone = pytz.timezone(timezone_str)
    return utc_time.astimezone(timezone).strftime("%H:%M")


def slot_status(game) -> str:
    """Returns slots data for game"""
    slots = game.slots
    time_header = slot_time_header(game)
    players = game.players_list
    pistol = EMOJI["pistol"]
    dizzy = EMOJI["dizzy"]

    if game.expired:
        return f"{dizzy} _{time_header} expired_\n{players}"
    else:
        if 5 <= slots < 10:
            reply = f"Full party! {pistol}"
        elif slots >= 10:
            reply = f"5x5! {pistol}{pistol}"
        else:
            reply = ""
        return f"*{time_header}*: {reply}\n{players}"


def slot_status_all(games) -> str:
    """Returns slots data for all games"""
    return "\n\n".join(slot_status(game) for game in games)


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
