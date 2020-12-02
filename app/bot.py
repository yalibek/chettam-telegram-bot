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
from datetime import datetime as dt

import pytz
import sentry_sdk
from tabulate import tabulate
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import (
    Updater,
    CommandHandler,
    ConversationHandler,
    CallbackQueryHandler,
)

from app.bot_utils import (
    get_status_reply,
    restricted,
    refresh_main_page,
    in_out,
    remove_game_jobs,
    remove_player_and_clean_game,
    schedule_game_notification,
    create_game_and_add_player,
    get_chettam_data,
    hours_keyboard,
    sync_games,
)
from app.utils import (
    logger,
    get_player,
    convert_to_dt,
    get_game,
    slot_status,
    chop,
    get_all_data,
    player_query,
)
from app.vars import (
    DEBUG,
    MAIN_STATE,
    EMOJI,
    TOKEN,
    COMMANDS,
    HOUR_MINUTE_PATTERN,
    HOST,
    PORT,
    APP_URL,
    SENTRY_DSN,
    COMMON_TIMEZONES,
)


def error(update, context):
    """Log Errors caused by Updates."""
    logger().error(f"\nupdate: {update}\nerror: {context.error}\n")


# Command actions
@restricted
@sync_games
def status(update, context):
    """Get games status for current chat"""
    reply = get_status_reply(update)
    update.message.reply_markdown(reply)


@restricted
@sync_games
def slot_in(update, context):
    in_out(update, context, action="in")


@restricted
@sync_games
def slot_out(update, context):
    in_out(update, context, action="out")


@restricted
@sync_games
def all_in_out(update, context):
    args = context.args
    if args and args[0] == "in":
        in_out(update, context, action="in", hard_args=["all"])
    elif args and args[0] == "out":
        in_out(update, context, action="out", hard_args=["all"])


@restricted
@sync_games
def menu(update, context):
    keyboard = [
        [
            InlineKeyboardButton("Set user's timezone", callback_data="user_timezone"),
        ],
        [
            InlineKeyboardButton("Data", callback_data="data"),
        ],
    ]
    update.message.reply_markdown(
        text=f"Menu",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return MAIN_STATE


def user_timezone(update, context):
    """Set current user's timezone"""
    query = update.callback_query
    player = get_player(update)
    keyboard = [
        [InlineKeyboardButton(tz, callback_data=f"TZ_{tz}")] for tz in COMMON_TIMEZONES
    ]
    query.answer()
    query.edit_message_text(
        text=f"Your timezone is {player.timezone}\nSet new timezone:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return MAIN_STATE


def set_user_timezone(update, context):
    query = update.callback_query
    new_tz = re.search("TZ_(.*)", query.data).group(1)
    player = get_player(update)
    player.timezone = new_tz
    player.save()
    query.answer()
    query.edit_message_text(
        text=f"Your TZ was set to {new_tz}",
    )
    return MAIN_STATE


def data(update, context):
    query = update.callback_query
    df = get_all_data(chat_id=update.effective_chat.id)
    table = data_games_played(df)
    query.answer()
    query.edit_message_text(text=f"```\n{table}```", parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END


def data_games_played(df):
    df = df[df["in_queue"] == False]
    df = df[df["expired"] == True]
    uniq_players = df["player_id"].value_counts()
    # TODO: queue
    data_table = [
        [str(player_query(player_id)), count]
        for player_id, count in uniq_players.iteritems()
    ]
    return tabulate(tabular_data=data_table, headers=["Player", "Games played"])


# def data_popular_timeslot(df):
#     uniq_timeslot = df["timeslot"].value_counts()
#     data_table = [[timeslot, count] for timeslot, count in uniq_timeslot.iteritems()]
#     return tabulate(tabular_data=data_table, headers=["Timeslot", "Games played"])


# Conversation actions
@restricted
@sync_games
def chettam(update, context):
    """Entry point for conversation"""
    if context.args:
        slot_in(update, context)
    else:
        reply, keyboard = get_chettam_data(update, context)
        update.message.reply_markdown(
            reply,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return MAIN_STATE


@sync_games
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
    player = get_player(update)
    timeslot = convert_to_dt(timeslot=query.data, timezone=player.timezone_pytz)
    create_game_and_add_player(update, context, player, timeslot)
    return refresh_main_page(update, context, query)


def join(update, context):
    """Join current game"""
    query = update.callback_query
    player = get_player(update)
    game_id = re.search("[0-9]+", query.data).group(0)
    game = get_game(update.effective_chat.id, game_id=game_id)
    game.add_player(player, joined_at=dt.now(pytz.utc))
    return refresh_main_page(update, context, query)


def leave(update, context):
    """Leave current game"""
    query = update.callback_query
    player = get_player(update)
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
    reply = get_status_reply(update)
    query.answer()
    query.edit_message_text(text=reply, parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END


def back(update, context):
    """Back to main page"""
    query = update.callback_query
    return refresh_main_page(update, context, query)


def main():
    """Run bot"""
    updater = Updater(
        TOKEN,
        use_context=True,
    )
    updater.bot.set_my_commands(COMMANDS)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Log all errors
    dp.add_error_handler(error)

    # Handlers
    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(CommandHandler("all", all_in_out))
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
    dp.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("menu", menu)],
            fallbacks=[CommandHandler("menu", menu)],
            states={
                MAIN_STATE: [
                    CallbackQueryHandler(data, pattern="^data$"),
                    CallbackQueryHandler(user_timezone, pattern="^user_timezone$"),
                    CallbackQueryHandler(set_user_timezone, pattern="^TZ_[a-zA-Z\/]+$"),
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
        updater.start_webhook(listen=HOST, port=PORT, url_path=TOKEN)
        updater.bot.set_webhook(APP_URL + TOKEN)

    # Block until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == "__main__":
    sentry_sdk.init(SENTRY_DSN)
    main()
