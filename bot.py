#!/usr/bin/env python3.7
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

import sentry_sdk
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    Filters,
)

from utils import *
from vars import *


def restricted(func):
    """Restrict prod bot usage to allowed chats only"""

    def wrapped(update, context, *args, **kwargs):
        if DEBUG or update.effective_chat.id in ALLOWED_CHATS:
            return func(update, context, *args, **kwargs)
        else:
            update.message.reply_text("You're not authorized to use this bot.")

    return wrapped


def error(update, context):
    """Log Errors caused by Updates."""
    logger().warning('Update "%s" caused error "%s"', update, context.error)


# Command actions
@restricted
def start(update, context):
    """Bot start messages"""
    random_sticker = random.choice(
        [
            STICKERS["lenin"],
            STICKERS["racoon"],
            STICKERS["borat"],
            STICKERS["harry"],
            STICKERS["sheikh"],
            STICKERS["pistol_parrot"],
            STICKERS["pistol_duck_left"],
            STICKERS["pistol_duck_right"],
        ]
    )
    update.message.reply_text(
        START_MESSAGE, reply_to_message_id=None,
    )
    update.message.reply_sticker(
        random_sticker, reply_to_message_id=None,
    )


@restricted
def status(update, context):
    """Get games status for current chat"""
    games = get_all_games(update)
    update.message.reply_markdown(slot_status_all(games))


@restricted
def gogo(update, context):
    """Reply with random quote from invite list just for fun"""
    pistol = EMOJI["pistol"]
    invite = random.choice(INVITE)
    update.message.reply_text(f"{invite} {pistol}", reply_to_message_id=None)


def dayoff(update, context):
    """Dayoff messages"""
    try:
        reply = get_quote()
    except:
        reply = "It's dayoff, fool!"
        update.message.reply_sticker(
            STICKERS["hahaclassic"], reply_to_message_id=None,
        )
    update.message.reply_markdown(reply, reply_to_message_id=None)


# Inline keyboard actions
def status_conv(update, context):
    """Get games status for current chat"""
    query = update.callback_query
    games = get_all_games(update)
    query.answer()
    query.edit_message_text(text=slot_status_all(games), parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END


def send_notification(context, chat_id, message, due=0):
    """Send a separate message"""

    def send_msg(context):
        context.bot.send_message(
            context.job.context, text=message, parse_mode=ParseMode.MARKDOWN,
        )

    context.job_queue.run_once(send_msg, due, context=chat_id)


def call(update, context):
    """Mention all players about current game"""
    query = update.callback_query
    game_id = re.search("[0-9]+", query.data).group(0)
    game = get_game(update, game_id)
    time_header = slot_time_header(game)
    query.answer()
    query.edit_message_text(text=slot_status(game), parse_mode=ParseMode.MARKDOWN)
    send_notification(
        context=context,
        chat_id=update.effective_chat.id,
        message=f"*{time_header}*: {game.players_call_active} go go!",
    )
    return ConversationHandler.END


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


def back(update, context):
    """Back to main page"""
    query = update.callback_query
    return refresh_main_page(update, context, query)


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


@restricted
def chettam(update, context):
    """Entry point for conversation"""
    context.bot_data["player"] = get_player(update)
    reply, keyboard = get_chettam_data(update, context)
    update.message.reply_markdown(
        reply, reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return MAIN_STATE


def join(update, context):
    """Join current game"""
    query = update.callback_query
    player = context.bot_data["player"]
    game_id = re.search("[0-9]+", query.data).group(0)
    game = get_game(update, game_id)
    game.add_player(player, joined_at=dt.now(pytz.utc))
    return refresh_main_page(update, context, query)


def leave(update, context):
    """Leave current game"""
    query = update.callback_query
    player = context.bot_data["player"]
    game_id = re.search("[0-9]+", query.data).group(0)
    game = get_game(update, game_id)
    game.remove_player(player)
    if not game.players:
        game.delete()
    return refresh_main_page(update, context, query)


def hours_keyboard(update):
    """Returns keyboard with timeslots for new game"""
    main_hours = [18, 19, 20, 21, 22, 23, 0, 1]
    main_hours_dt = [convert_to_dt(f"{hour:02d}:00") for hour in main_hours]
    ts_games = get_all_games(update, ts_only=True)
    ts_filtered = [
        timeslot.astimezone(TIMEZONE_CET).strftime("%H:%M")
        for timeslot in main_hours_dt
        if timeslot not in ts_games and timeslot > dt.now(pytz.utc)
    ]
    keyboard = [
        InlineKeyboardButton(timeslot_time, callback_data=timeslot_time,)
        for timeslot_time in ts_filtered
    ]
    return row_list_chunks(keyboard)


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
        text=f"{clock} Choose time:", reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return MAIN_STATE


def new_game(update, context):
    """Create new game"""
    query = update.callback_query
    player = context.bot_data["player"]
    timeslot = convert_to_dt(query.data)
    game = create_game(update.effective_chat, timeslot)
    game.add_player(player, joined_at=dt.now(pytz.utc))
    return refresh_main_page(update, context, query)


def main():
    """Run bot"""
    updater = Updater(TOKEN, use_context=True)
    updater.bot.set_my_commands(COMMANDS)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Log all errors
    dp.add_error_handler(error)

    # Handlers
    # dp.add_handler(CommandHandler("start", start))

    if is_dayoff():
        dp.add_handler(MessageHandler(Filters.command, dayoff))
    else:
        dp.add_handler(CommandHandler("status", status))
        dp.add_handler(CommandHandler("gogo", gogo))

        main_conversation = ConversationHandler(
            entry_points=[CommandHandler("chettam", chettam)],
            fallbacks=[CommandHandler("chettam", chettam)],
            states={
                MAIN_STATE: [
                    CallbackQueryHandler(join, pattern="^join_[0-9]+$"),
                    CallbackQueryHandler(leave, pattern="^leave_[0-9]+$"),
                    CallbackQueryHandler(call, pattern="^call_[0-9]+$",),
                    CallbackQueryHandler(pick_hour, pattern="^pick_hour$"),
                    CallbackQueryHandler(new_game, pattern=HOUR_MINUTE_PATTERN),
                    CallbackQueryHandler(back, pattern="^back_to_main$"),
                    CallbackQueryHandler(status_conv, pattern="^status_conv$"),
                ],
            },
        )

        dp.add_handler(main_conversation)

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
