import logging
from datetime import datetime as dt, timedelta
from functools import partial, update_wrapper

import pytz

from models import Game, Player, session
from vars import EMOJI, TIMEZONE_CET, TIMEZONE_UTC


# Updates player's data if it has changed
def sync_player_data(player, user):
    p_data = [player.username, player.first_name, player.last_name]
    u_data = [user.username, user.first_name, user.last_name]
    if p_data != u_data:
        player.username, player.first_name, player.last_name = u_data
        player.save()


# Returns Player model for current user
def get_player(update):
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
        player.save()
    return player


# Creates new game
def create_game(chat, timeslot):
    game = Game(
        updated_at=dt.now(pytz.utc),
        timeslot=timeslot,
        chat_id=chat.id,
        chat_type=chat.type,
    )
    game.create()
    game.save()
    return game


# Checks if game wasn't updated for 8+ hours
def game_is_old(game):
    now = dt.now(pytz.utc)
    updated_at = to_utc(game.updated_at)
    played_at = to_utc(game.timeslot)
    delta = timedelta(hours=8)
    return (now - updated_at > delta) or (now - played_at > delta)


# Returns Game model for current chat
def get_game(update, timeslot=None):
    chat = update.effective_chat
    game = session.query(Game).filter_by(chat_id=chat.id).first()

    if timeslot:
        # Convert time into datetime object in UTC timezone
        date_today = dt.now(pytz.utc).date()
        date_time = f"{date_today} {timeslot}"
        timeslot_obj = dt.strptime(date_time, "%Y-%m-%d %H:%M")
        timeslot_cet = to_cet(timeslot_obj)
        timeslot = timeslot_cet.astimezone(TIMEZONE_UTC)

    if game and timeslot:
        # Update timeslot if given
        game.timeslot = timeslot
        game.updated_at = dt.now(pytz.utc)
        game.save()
    elif game and game_is_old(game):
        # Delete existing game if it wasn't updated for 8 hours
        game.delete()
        game = None
    elif not game and timeslot:
        # Create new game only if new timeslot is given
        game = create_game(chat, timeslot)

    return game


# Returns slots data
def slot_status(game):
    players = "\n".join(f"- {player}" for player in game.players_list)
    slots = game.slots
    timeslot = game.timeslot_cet.strftime("%H:%M")
    pistol = EMOJI["pistol"]
    if slots == 0:
        reply = f"All slots are available!"
    elif 5 <= slots < 10:
        reply = f"{slots} slot(s). 1 full party! {pistol}"
    elif slots == 10:
        reply = f"10 slots. 2 parties! gogo! {pistol}{pistol}"
    else:
        reply = f"{slots} slot(s) taken."
    return f"*{timeslot}*: {reply}\n{players}"


# Checks if today is cs:go dayoff
def is_dayoff():
    now = dt.now(pytz.utc)
    is_not_night = now.hour >= 6
    is_wed_sun = now.weekday() in [2, 6]
    return is_not_night and is_wed_sun


# Enables logging
def logger():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    return logging.getLogger(__name__)


# Localize to UTC
def to_utc(date_time):
    return TIMEZONE_UTC.localize(date_time)


# Localize to CET
def to_cet(date_time):
    return TIMEZONE_CET.localize(date_time)


# Hack to pass additional args to any func()
def wrapped_partial(func, *args, **kwargs):
    partial_func = partial(func, *args, **kwargs)
    update_wrapper(partial_func, func)
    return partial_func
