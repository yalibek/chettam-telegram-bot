import time
from datetime import datetime as dt, timedelta

import pytz
import re
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode

from app.utils import (
    is_dayoff,
    get_leetcode_problem,
    get_all_games,
    slot_status_all,
    get_player,
    convert_to_dt,
    get_game,
    game_timediff,
    row_list_chunks,
    slot_time_header,
    create_game,
    get_assoc,
    get_time_header,
)
from app.vars import (
    DEBUG,
    ALLOWED_CHATS_INTERNAL,
    ALLOWED_CHATS_EXTERNAL,
    STICKERS,
    MAIN_STATE,
    EMOJI,
    MAIN_HOURS,
)


def restricted(func):
    """Restrict prod bot usage to allowed chats only"""

    def wrapped(update, context, *args, **kwargs):
        chat_id = update.effective_chat.id
        if DEBUG or chat_id in ALLOWED_CHATS_INTERNAL:
            if is_dayoff():
                return dayoff(update, context)
            else:
                return func(update, context, *args, **kwargs)
        elif chat_id in ALLOWED_CHATS_EXTERNAL:
            return func(update, context, *args, **kwargs)
        else:
            update.message.reply_text(
                f"Your chat id is {chat_id}.\nShare it with bot owner to be authorized."
            )

    return wrapped


def sync_games(func):
    """Checks if games are expired"""

    def wrapped(update, context, *args, **kwargs):
        for game in get_all_games(update):
            if game_timediff(game, hours=1):
                game.expired = True
                game.save()
        return func(update, context, *args, **kwargs)

    return wrapped


def dayoff(update, context):
    """Dayoff messages"""
    try:
        reply = get_leetcode_problem()
    except:
        reply = "It's dayoff, fool!"
        update.message.reply_sticker(
            STICKERS["hahaclassic"],
            reply_to_message_id=None,
        )
    update.message.reply_markdown(reply, reply_to_message_id=None)


def get_status_reply(update):
    games = get_all_games(update)
    player = get_player(update)
    if games:
        return slot_status_all(games, timezone=player.timezone_pytz)
    else:
        return "Create new game with /chettam"


# Conversation helper functions
def get_chettam_data(update, context):
    """Reply message and keyboard for entry point"""
    games = get_all_games(update)
    player = get_player(update)
    pistol = EMOJI["pistol"]
    check = EMOJI["check"]
    party = EMOJI["party"]
    fire = EMOJI["fire"]
    zzz = EMOJI["zzz"]

    keyboard = []
    if games:
        reply = slot_status_all(games, timezone=player.timezone_pytz)
        for game in games:
            btn_row = []

            if player in game.players:
                btn_text = f"{zzz} Leave"
                btn_callback = f"leave_{game.id}"
            else:
                btn_text = f"{pistol} Join"
                btn_callback = f"join_{game.id}"
            btn_row.append(
                InlineKeyboardButton(
                    f"{get_time_header(game, player.timezone_pytz)}: {btn_text}",
                    callback_data=btn_callback,
                )
            )

            if (
                game.slots > 1
                and game_timediff(game, minutes=-30)
                and player in game.players
                and not get_assoc(game.id, player.id).in_queue
            ):
                btn_row.append(
                    InlineKeyboardButton(
                        f"{party} Call", callback_data=f"call_{game.id}"
                    )
                )

            keyboard.append(btn_row)

    else:
        reply = "Create new game below:"

    keyboard.append(
        [
            InlineKeyboardButton(f"{fire} New", callback_data="pick_hour"),
            InlineKeyboardButton(f"{check} Done", callback_data="status_conv"),
        ]
    )
    return reply, keyboard


@sync_games
def refresh_main_page(update, context, query):
    """Reload main page buttons"""
    reply, keyboard = get_chettam_data(update, context)
    query.answer()
    query.edit_message_text(
        reply,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN,
    )
    return MAIN_STATE


def hours_keyboard(update):
    """Returns keyboard with timeslots for new game"""
    player = get_player(update)
    timezone = player.timezone_pytz
    main_hours_dt = [
        convert_to_dt(timeslot=f"{hour:02d}:00", timezone=timezone)
        for hour in MAIN_HOURS
    ]
    ts_games = get_all_games(update, ts_only=True)
    ts_filtered = [
        timeslot.astimezone(timezone).strftime("%H:%M")
        for timeslot in main_hours_dt
        if timeslot not in ts_games and timeslot > dt.now(timezone)
    ]
    keyboard = [
        InlineKeyboardButton(timeslot_time, callback_data=timeslot_time)
        for timeslot_time in ts_filtered
    ]
    return row_list_chunks(keyboard)


def in_out(update, context, action, hard_args=None):
    """Ugliest function of them all"""
    args = hard_args if hard_args else context.args
    if args:
        player = get_player(update)
        if args[0].lower() == "all":
            for game in get_all_games(update):
                if action == "in" and player not in game.players:
                    game.add_player(player, joined_at=dt.now(pytz.utc))

                elif action == "out" and player in game.players:
                    remove_player_and_clean_game(context, game, player)
        else:
            filtered_args = expand_hours(
                argv
                for argv in args
                if re.search("^[0-9]+-[0-9]+$", argv) or re.search("^[0-9]+$", argv)
            )
            for argv in filtered_args:
                timeslot = convert_to_dt(
                    timeslot=f"{int(argv):02d}:00",
                    timezone=player.timezone_pytz,
                )
                game = get_game(update.effective_chat.id, timeslot=timeslot)

                if action == "in":
                    if not game and timeslot > dt.now(pytz.utc):
                        create_game_and_add_player(update, context, player, timeslot)
                    elif game and player not in game.players:
                        game.add_player(player, joined_at=dt.now(pytz.utc))

                elif action == "out":
                    if game and player in game.players:
                        remove_player_and_clean_game(context, game, player)


def expand_hours(hours_list):
    """18-21 -> [18, 19, 20, 21]"""
    result = []
    for hour in hours_list:
        if re.search("^[0-9]+-[0-9]+$", hour):
            hour_pair = hour.split("-")
            hours_indexes = {hour: idx for idx, hour in enumerate(MAIN_HOURS)}
            first_hour = int(hour_pair[0])
            first_hour_index = hours_indexes.get(first_hour)
            last_hour = int(hour_pair[1])
            last_hour_index = hours_indexes.get(last_hour)
            if (
                first_hour in MAIN_HOURS
                and last_hour in MAIN_HOURS
                and first_hour_index < last_hour_index
            ):
                result.extend(MAIN_HOURS[first_hour_index : last_hour_index + 1])
        else:
            if int(hour) in MAIN_HOURS:
                result.append(int(hour))
    return set(result)


def schedule_game_notification(context, update, game, message, when=0, auto=False):
    """Send a separate message"""
    player = get_player(update)
    tz = player.timezone_pytz

    def send_msg(ctx):
        if auto:
            prefix = "auto"
        else:
            prefix = player
        ctx.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"\[_{prefix}_] *{slot_time_header(game, timezone=tz)}*: {game.players_call_active} {message}",
            parse_mode=ParseMode.MARKDOWN,
        )

    context.job_queue.run_once(send_msg, when=when, name=f"{game.id}_{when}")


def create_game_and_add_player(update, context, player, timeslot):
    """Self-explanatory"""
    game = create_game(update.effective_chat, timeslot)
    game.add_player(player, joined_at=dt.now(pytz.utc))
    for minutes in [5]:
        schedule_game_notification(
            context=context,
            update=update,
            game=game,
            message=f"game starts in {minutes} mins!",
            when=game.timeslot_utc - timedelta(minutes=minutes),
            auto=True,
        )


def remove_player_and_clean_game(context, game, player):
    """Remove player and, if no players left, delete the game with the jobs"""
    game.remove_player(player)
    if not game.players:
        game.expired = True
        remove_game_jobs(context, game)


def remove_game_jobs(context, game, delay=0):
    """Remove all jobs for given game"""
    time.sleep(delay)
    for job in context.job_queue.jobs():
        if job.name.startswith(f"{game.id}_"):
            job.schedule_removal()
