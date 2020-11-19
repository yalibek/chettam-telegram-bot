import time
from datetime import datetime as dt, timedelta

import pytz
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode

from utils import (
    is_dayoff,
    get_leetcode_problem,
    get_all_games,
    slot_status_all,
    get_player,
    convert_to_dt,
    get_game,
    utc_to_tz_time,
    game_timediff,
    row_list_chunks,
    slot_time_header,
    create_game,
    get_assoc,
)
from vars import (
    DEBUG,
    ALLOWED_CHATS,
    STICKERS,
    MAIN_STATE,
    EMOJI,
    MAIN_HOURS,
    TIMEZONE_CET,
    USAGE_TEXT,
)


def restricted(func):
    """Restrict prod bot usage to allowed chats only"""

    def wrapped(update, context, *args, **kwargs):
        if DEBUG or update.effective_chat.id in ALLOWED_CHATS:
            if is_dayoff():
                return dayoff(update, context)
            else:
                return func(update, context, *args, **kwargs)
        else:
            update.message.reply_text("You're not authorized to use this bot.")

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
    if games:
        return slot_status_all(games)
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
        reply = slot_status_all(games)
        for game in games:
            if not game.expired:
                btn_row = []

                if player in game.players:
                    btn_text = f"{zzz} Leave"
                    btn_callback = f"leave_{game.id}"
                else:
                    btn_text = f"{pistol} Join"
                    btn_callback = f"join_{game.id}"
                timeslot_cet = utc_to_tz_time(game, "CET")
                btn_row.append(
                    InlineKeyboardButton(
                        f"{timeslot_cet}: {btn_text}", callback_data=btn_callback
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
    main_hours_dt = [convert_to_dt(f"{hour:02d}:00") for hour in MAIN_HOURS]
    ts_games = get_all_games(update, ts_only=True)
    ts_filtered = [
        timeslot.astimezone(TIMEZONE_CET).strftime("%H:%M")
        for timeslot in main_hours_dt
        if timeslot not in ts_games and timeslot > dt.now(pytz.utc)
    ]
    keyboard = [
        InlineKeyboardButton(
            timeslot_time,
            callback_data=timeslot_time,
        )
        for timeslot_time in ts_filtered
    ]
    return row_list_chunks(keyboard)


def in_out(update, context, action):
    if context.args:
        for argv in context.args:
            if argv.isdigit() and int(argv) in MAIN_HOURS:
                timeslot = convert_to_dt(f"{int(argv):02d}:00")
                game = get_game(update.effective_chat.id, timeslot=timeslot)
                player = get_player(update)

                if action == "in":
                    if not game:
                        create_game_and_add_player(update, context, player, timeslot)
                    elif player not in game.players:
                        game.add_player(player, joined_at=dt.now(pytz.utc))

                elif action == "out":
                    if game and player in game.players:
                        remove_player_and_clean_game(context, game, player)

        reply = get_status_reply(update)
        update.message.reply_markdown(reply)
    else:
        update.message.reply_markdown(USAGE_TEXT)


def schedule_game_notification(context, update, game, message, when=0, auto=False):
    """Send a separate message"""

    def send_msg(ctx):
        if auto:
            prefix = "auto"
        else:
            prefix = get_player(update)
        ctx.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"\[_{prefix}_] *{slot_time_header(game)}*: {game.players_call_active} {message}",
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
        game.delete()
        remove_game_jobs(context, game)


def remove_game_jobs(context, game, delay=0):
    """Remove all jobs for given game"""
    time.sleep(delay)
    for job in context.job_queue.jobs():
        if job.name.startswith(f"{game.id}_"):
            job.schedule_removal()
