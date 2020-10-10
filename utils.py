import logging
from datetime import datetime as dt, timedelta

import inflect
import pytz
import requests

from models import Game, Player, session
from vars import EMOJI, TIMEZONE_CET, TIMEZONE_UTC, CSGO_NICKNAMES


def sync_player_data(player: Player, user):
    """Updates player's data with Telegram user's data if it has changed"""
    p_data = [player.username, player.first_name, player.last_name]
    u_data = [user.username, user.first_name, user.last_name]
    if p_data != u_data:
        player.username, player.first_name, player.last_name = u_data
        player.save()


def get_nickname(user) -> str:
    """Get CG:GO nickname for given user if it exist"""
    try:
        return CSGO_NICKNAMES[user.username]
    except:
        pass


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


def get_reply_for_time_menu(context) -> str:
    """Returns reply message when user picking a time slot"""
    data = context.bot_data
    pencil = EMOJI["pencil"]
    clock = EMOJI["clock"]
    if data["game_action"] == "edit_existing_game":
        game = data["game"]
        game_num = data["game_num"]
        return f"{pencil} Editing game #{game_num} {game.timeslot_cet_time}:"
    else:
        return f"{clock} Choose time:"


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
    game = Game(timeslot=timeslot, chat_id=chat.id, chat_type=chat.type,)
    game.create()
    return game


def update_game(game: Game, timeslot) -> Game:
    """Updates existing game with new timeslot"""
    game.timeslot = timeslot
    game.save()
    return game


def game_timediff(game: Game, hours=0, minutes=0, seconds=0) -> bool:
    """Checks if game wasn't updated for given time frame"""
    now = dt.now(pytz.utc)
    played_at = game.timeslot_utc
    delta = timedelta(hours=hours, minutes=minutes, seconds=seconds)
    return now - played_at > delta


def search_game(update, timeslot) -> Game:
    """Search Game with given timeslot for current chat"""
    return (
        session.query(Game)
        .filter_by(chat_id=update.effective_chat.id, timeslot=timeslot)
        .first()
    )


def get_game(update, game_id) -> Game:
    """Returns Game model for current chat"""
    return (
        session.query(Game)
        .filter_by(chat_id=update.effective_chat.id, id=game_id)
        .first()
    )


def get_all_games(update) -> list:
    """Returns all Game models for current chat"""
    games = (
        session.query(Game)
        .filter_by(chat_id=update.effective_chat.id)
        .order_by(Game.timeslot)
        .all()
    )
    games_list = []
    for game in games:
        if game_timediff(game, hours=2):
            game.delete()
        else:
            games_list.append(game)
    return games_list


def slot_status(game) -> str:
    """Returns slots data for game"""
    slots = game.slots
    timeslot = game.timeslot_cet_time
    timeslot_london = game.timeslot_gbt_time
    players = game.players_list
    pistol = EMOJI["pistol"]
    dizzy = EMOJI["dizzy"]

    if game_timediff(game, minutes=30):
        return f"{dizzy} _{timeslot} expired_\n{players}"
    else:
        if 5 <= slots < 10:
            reply = f"1 full party! {pistol}"
        elif slots >= 10:
            reply = f"5x5! gogo! {pistol}{pistol}"
        else:
            reply = ""
        return f"*{timeslot} ({timeslot_london})*: {pluralize(slots, 'slot')}. {reply}\n{players}"


def slot_status_all(games) -> str:
    """Returns slots data for all games"""
    return "\n\n".join(slot_status(game) for game in games)


def is_dayoff() -> bool:
    """Checks if today is cs:go dayoff"""
    now = dt.now(pytz.utc)
    is_not_night = now.hour >= 3
    is_wed_sun = now.weekday() in [2, 6]
    return is_not_night and is_wed_sun


def logger() -> logging.Logger:
    """Enables logging"""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    return logging.getLogger(__name__)


def get_quote() -> tuple:
    """Get random famous quote"""
    url = "https://api.forismatic.com/api/1.0/"
    response = requests.get(
        url, params={"method": "getQuote", "lang": "en", "format": "json"}
    )
    quote = response.json().get("quoteText")
    author = response.json().get("quoteAuthor")
    if not author:
        author = "Unknown"
    return quote, author


def pluralize(quantity, noun) -> str:
    """Return plural noun for given quantity"""
    p = inflect.engine()
    return p.inflect(f"num({quantity}) plural('{noun}')")
