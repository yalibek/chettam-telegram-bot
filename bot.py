#!/usr/bin/env python3.9
# -*- coding: utf-8 -*-

"""
Kostyli i Velosipedy™ BV presents

Chettamm telegram bot for csgo guys.
It helps players to schedule their cs:go games and join them.
Version: 2.0

Main functionality is run under chettam() function.
It uses inline keyboard buttons inside conversation mode.

In development run bot.py with --debug flag
"""

import re
import time

import sentry_sdk
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import (
    Updater,
    CommandHandler,
    ConversationHandler,
    CallbackQueryHandler,
)

from utils import *
from vars import *


# Functions
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
        reply = get_quote()
    except:
        reply = "It's dayoff, fool!"
        update.message.reply_sticker(
            STICKERS["hahaclassic"],
            reply_to_message_id=None,
        )
    update.message.reply_markdown(reply, reply_to_message_id=None)


def error(update, context):
    """Log Errors caused by Updates."""
    logger().error(f"\nupdate: {update}\nerror: {context.error}\n")


# Command actions
@restricted
def status(update, context):
    """Get games status for current chat"""
    games = get_all_games(update)
    update.message.reply_markdown(slot_status_all(games))


@restricted
def slot_in(update, context):
    in_out(update, context, action="in")


@restricted
def slot_out(update, context):
    in_out(update, context, action="out")


# Conversation actions
@restricted
def chettam(update, context):
    """Entry point for conversation"""
    if context.args:
        slot_in(update, context)
    else:
        context.bot_data["player"] = get_player(update)
        reply, keyboard = get_chettam_data(update, context)
        update.message.reply_markdown(
            reply,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return MAIN_STATE


def pick_hour(update, context):
    """Choice of hours"""
    query = update.callback_query
    check = EMOJI["check"]
    clock = EMOJI["clock"]
    keyboard = hours_keyboard(update)
    keyboard.append(
        [
            InlineKeyboardButton("« Back", callback_data="back_to_main"),
            InlineKeyboardButton(f"{check} Done", callback_data="status_conv"),
        ],
    )
    query.answer()
    query.edit_message_text(
        text=f"{clock} Choose time:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return MAIN_STATE


def new_game(update, context):
    """Create new game"""
    query = update.callback_query
    player = context.bot_data["player"]
    timeslot = convert_to_dt(query.data)
    create_game_and_add_player(update, context, player, timeslot)
    return refresh_main_page(update, context, query)


def join(update, context):
    """Join current game"""
    query = update.callback_query
    player = context.bot_data["player"]
    game_id = re.search("[0-9]+", query.data).group(0)
    game = get_game(update.effective_chat.id, game_id=game_id)
    game.add_player(player, joined_at=dt.now(pytz.utc))
    return refresh_main_page(update, context, query)


def leave(update, context):
    """Leave current game"""
    query = update.callback_query
    player = context.bot_data["player"]
    game_id = re.search("[0-9]+", query.data).group(0)
    game = get_game(update.effective_chat.id, game_id=game_id)
    remove_player_and_clean_game(context, game, player)
    return refresh_main_page(update, context, query)


def call(update, context):
    """Mention all players about current game"""
    query = update.callback_query
    game_id = re.search("[0-9]+", query.data).group(0)
    game = get_game(update.effective_chat.id, game_id=game_id)
    query.answer()
    query.edit_message_text(text=slot_status(game), parse_mode=ParseMode.MARKDOWN)
    schedule_game_notification(
        context=context,
        update=update,
        game=game,
        message="go go!",
    )
    remove_game_jobs(context, game, delay=0.1)
    return ConversationHandler.END


def status_conv(update, context):
    """Get games status for current chat"""
    query = update.callback_query
    games = get_all_games(update)
    query.answer()
    query.edit_message_text(text=slot_status_all(games), parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END


def back(update, context):
    """Back to main page"""
    query = update.callback_query
    return refresh_main_page(update, context, query)


# Conversation helper functions
def get_chettam_data(update, context):
    """Reply message and keyboard for entry point"""
    games = get_all_games(update)
    player = context.bot_data["player"]
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

        status(update, context)


def schedule_game_notification(context, update, game, message, when=0, auto=False):
    """Send a separate message"""

    def send_msg(ctx):
        if auto:
            prefix = "auto"
        else:
            prefix = ctx.bot_data["player"]
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


def main():
    """Run bot"""
    updater = Updater(TOKEN, use_context=True)
    updater.bot.set_my_commands(COMMANDS)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Log all errors
    dp.add_error_handler(error)

    # Handlers
    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(CommandHandler(chop("in"), slot_in))
    dp.add_handler(CommandHandler(chop("out"), slot_out))
    dp.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler(chop("chettam"), chettam)],
            fallbacks=[CommandHandler(chop("chettam"), chettam)],
            states={
                MAIN_STATE: [
                    CallbackQueryHandler(join, pattern="^join_[0-9]+$"),
                    CallbackQueryHandler(leave, pattern="^leave_[0-9]+$"),
                    CallbackQueryHandler(
                        call,
                        pattern="^call_[0-9]+$",
                    ),
                    CallbackQueryHandler(pick_hour, pattern="^pick_hour$"),
                    CallbackQueryHandler(new_game, pattern=HOUR_MINUTE_PATTERN),
                    CallbackQueryHandler(back, pattern="^back_to_main$"),
                    CallbackQueryHandler(status_conv, pattern="^status_conv$"),
                ],
            },
        )
    )

    # Start
    if DEBUG:
        # Start the Bot (polling method)
        updater.start_polling()
    else:
        # Set Heroku handlers and start the Bot (webhook method)
        updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN)
        updater.bot.set_webhook(HEROKU_APP + TOKEN)

    # Block until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == "__main__":
    sentry_sdk.init(SENTRY_DSN)
    main()
