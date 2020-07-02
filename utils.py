import logging
from datetime import datetime as dt, timedelta
from functools import partial, update_wrapper

import pytz
import requests

from models import Game, Player, session
from vars import EMOJI, TIMEZONE_CET, TIMEZONE_UTC


# Updates player's data if it has changed
def sync_player_data(player: Player, user):
    p_data = [player.username, player.first_name, player.last_name]
    u_data = [user.username, user.first_name, user.last_name]
    if p_data != u_data:
        player.username, player.first_name, player.last_name = u_data
        player.save()


# Returns Player model for current user
def get_player(update) -> Player:
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


# Converts time into datetime object in UTC timezone
def convert_to_dt(timeslot) -> dt:
    time = dt.strptime(timeslot, "%H:%M")
    date_today = dt.now(pytz.utc).date()

    if time.hour in range(4):
        day = date_today + timedelta(days=1)
    else:
        day = date_today

    date_time = f"{day} {time.hour}:{time.minute}"
    timeslot_obj = dt.strptime(date_time, "%Y-%m-%d %H:%M")
    timeslot_cet = to_cet(timeslot_obj)
    return timeslot_cet.astimezone(TIMEZONE_UTC)


# Creates new game
def create_game(chat, timeslot) -> Game:
    game = Game(
        updated_at=dt.now(pytz.utc),
        timeslot=timeslot,
        chat_id=chat.id,
        chat_type=chat.type,
    )
    game.create()
    game.save()
    return game


# Updates existing game with new timeslot
def update_game(game: Game, timeslot) -> Game:
    game.timeslot = timeslot
    game.updated_at = dt.now(pytz.utc)
    game.save()
    return game


# Checks if game wasn't updated for 8+ hours
def game_is_old(game: Game) -> bool:
    now = dt.now(pytz.utc)
    updated_at = to_utc(game.updated_at)
    played_at = to_utc(game.timeslot)
    delta = timedelta(hours=8)
    return (now - updated_at > delta) or (now - played_at > delta)


# Returns Game model for current chat
def get_game(update, game_id) -> Game:
    return (
        session.query(Game)
        .filter_by(chat_id=update.effective_chat.id, id=game_id)
        .first()
    )


# Returns all Game models for current chat
def get_all_games(update) -> list:
    games = (
        session.query(Game)
        .filter_by(chat_id=update.effective_chat.id)
        .order_by(Game.id)
        .all()
    )
    games_list = []
    for game in games:
        if game_is_old(game):
            game.delete()
        else:
            games_list.append(game)
    return games_list


# Returns slots data for game
def slot_status(game) -> str:
    players = "\n".join(f"- {player}" for player in game.players_list)
    slots = game.slots
    timeslot = game.timeslot_cet_time
    pistol = EMOJI["pistol"]
    if slots == 0:
        reply = f"All slots are available!"
    elif 5 <= slots < 10:
        reply = f"{slots} slot(s). 1 full party! {pistol}"
    elif slots == 10:
        reply = f"10 slots. 2 parties! gogo! {pistol}{pistol}"
    else:
        reply = f"{slots} slot(s) taken."
    if players:
        return f"*{timeslot}*: {reply}\n{players}"
    else:
        return f"*{timeslot}*: {reply}"


# Returns slots data for all games
def slot_status_all(games) -> str:
    return "\n\n".join(slot_status(game) for game in games)


# Checks if today is cs:go dayoff
def is_dayoff() -> bool:
    now = dt.now(pytz.utc)
    is_not_night = now.hour >= 3
    is_wed_sun = now.weekday() in [2, 6]
    return is_not_night and is_wed_sun


# Enables logging
def logger() -> logging.Logger:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    return logging.getLogger(__name__)


# Localize to UTC
def to_utc(date_time) -> dt:
    return TIMEZONE_UTC.localize(date_time)


# Localize to CET
def to_cet(date_time) -> dt:
    return TIMEZONE_CET.localize(date_time)


# Hack to pass additional args to any func()
def wrapped_partial(func, *args, **kwargs) -> partial:
    partial_func = partial(func, *args, **kwargs)
    update_wrapper(partial_func, func)
    return partial_func


# Set time alert
def set_time_alert(update, context, alert, message, due):
    if "job" in context.chat_data:
        old_job = context.chat_data["job"]
        old_job.schedule_removal()

    partial_alert = wrapped_partial(alert, message=message)
    new_job = context.job_queue.run_once(
        partial_alert, due, context=update.effective_chat.id
    )
    context.chat_data["job"] = new_job


# Get random famous quote
def get_quote() -> tuple:
    url = "https://api.forismatic.com/api/1.0/"
    response = requests.get(
        url, params={"method": "getQuote", "lang": "en", "format": "json"}
    )
    quote = response.json().get("quoteText")
    author = response.json().get("quoteAuthor")
    return quote, author
