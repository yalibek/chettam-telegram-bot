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

TODO: change "new_game" callback pattern to Datetime.
TODO: organize "get_chettam_data" buttons.
TODO: cleanup datetime/timeslot stuff.
TODO: implement players' queue tags with class properties???
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


def error(update, context):
    """Log Errors caused by Updates."""
    logger().warning('Update "%s" caused error "%s"', update, context.error)


# Command actions
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


def status(update, context):
    """Get games status for current chat"""
    games = get_all_games(update)
    if games:
        update.message.reply_markdown(slot_status_all(games), reply_to_message_id=None)
    else:
        update.message.reply_text("start a game with /chettam")


def gogo(update, context):
    """Reply with random quote from invite list just for fun"""
    pistol = EMOJI["pistol"]
    invite = random.choice(INVITE)
    update.message.reply_text(f"{invite} {pistol}", reply_to_message_id=None)


def dayoff(update, context):
    """Dayoff messages"""
    context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        quote, author = get_quote()
        reply = f"_{quote}_\n\n — {author}"
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


def cancel(update, context):
    """End current conversation"""
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="cancelled :(")
    return ConversationHandler.END


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
    return FIRST_STAGE


def back(update, context):
    """Back to main page"""
    query = update.callback_query
    return refresh_main_page(update, context, query)


def get_chettam_data(update, context):
    """Reply message and keyboard for entry point"""
    games = get_all_games(update)
    player = context.bot_data["player"]
    pistol = EMOJI["pistol"]
    cross = EMOJI["cross"]
    check = EMOJI["check"]
    party = EMOJI["party"]
    zzz = EMOJI["zzz"]

    keyboard = []
    kb_last_row = [
        InlineKeyboardButton(f"{pistol} New", callback_data="pick_hour"),
    ]
    if games:
        kb_last_row.append(
            InlineKeyboardButton(f"{check} Done", callback_data="status_conv")
        )
        reply = slot_status_all(games)
        for game in games:
            row = []
            time_header = game.timeslot_cet_time
            if player in game.players:
                btn_text = f"{time_header}: {zzz} Leave"
                btn_callback = f"leave_{game.id}"
            elif not game.expired:
                btn_text = f"{time_header}: {pistol} Join"
                btn_callback = f"join_{game.id}"
            btn1 = InlineKeyboardButton(btn_text, callback_data=btn_callback)
            row.append(btn1)

            if (
                game.slots > 1
                and game_timediff(game, minutes=-30)
                and player in game.players
            ):
                btn2 = InlineKeyboardButton(
                    f"{party} Call", callback_data=f"call_{game.id}"
                )
                row.append(btn2)

            keyboard.append(row)
    else:
        kb_last_row.append(
            InlineKeyboardButton(f"{cross} Cancel", callback_data="cancel"),
        )
        reply = "Game doesn't exist."

    keyboard.append(kb_last_row)
    return reply, keyboard


def chettam(update, context):
    """Entry point for conversation"""
    context.bot_data["player"] = get_player(update)
    reply, keyboard = get_chettam_data(update, context)
    update.message.reply_markdown(
        reply, reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return FIRST_STAGE


def join(update, context):
    """Join current game"""
    query = update.callback_query
    player = context.bot_data["player"]
    game_id = re.search("[0-9]+", query.data).group(0)
    game = get_game(update, game_id)
    game.add_player(player, joined_at=dt.now(pytz.utc))
    game.save()
    return refresh_main_page(update, context, query)


def leave(update, context):
    """Leave current game"""
    query = update.callback_query
    player = context.bot_data["player"]
    game_id = re.search("[0-9]+", query.data).group(0)
    game = get_game(update, game_id)
    game.players.remove(player)
    game.save()
    if not game.players:
        game.delete()
    return refresh_main_page(update, context, query)


def hours_keyboard(update):
    """Returns keyboard with timeslots for new game"""
    main_hours = [18, 19, 20, 21, 22, 23, 0, 1]
    main_hours_dt = [convert_to_dt(f"{hour:02d}:00") for hour in main_hours]
    ts_games = get_all_games(update, ts_only=True)
    ts_filtered = [
        timeslot
        for timeslot in main_hours_dt
        if timeslot not in ts_games and timeslot > dt.now(pytz.utc)
    ]
    kb = [
        InlineKeyboardButton(
            f"{ts_dt.astimezone(TIMEZONE_CET).strftime('%H:%M')}",
            callback_data=f"{ts_dt.astimezone(TIMEZONE_CET).strftime('%H:%M')}",
        )
        for ts_dt in ts_filtered
    ]
    return row_list_chunks(kb)


def pick_hour(update, context):
    """Choice of hours"""
    query = update.callback_query
    cross = EMOJI["cross"]
    keyboard = hours_keyboard(update)
    keyboard.append(
        [
            InlineKeyboardButton("« Back", callback_data="back_to_main"),
            InlineKeyboardButton(f"{cross} Cancel", callback_data="cancel"),
        ],
    )
    reply = f"Choose time:"
    query.answer()
    query.edit_message_text(
        text=reply, reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return FIRST_STAGE


def new_game(update, context):
    """Create new game"""
    query = update.callback_query
    player = context.bot_data["player"]
    new_timeslot = convert_to_dt(query.data)
    game = create_game(update.effective_chat, new_timeslot)
    game.add_player(player, joined_at=dt.now(pytz.utc))
    game.save()
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
    dp.add_handler(CommandHandler("start", start))

    if is_dayoff():
        dp.add_handler(MessageHandler(Filters.command, dayoff))
    else:
        dp.add_handler(CommandHandler("status", status))
        dp.add_handler(CommandHandler("gogo", gogo))

        main_conversation = ConversationHandler(
            entry_points=[CommandHandler("chettam", chettam)],
            fallbacks=[CommandHandler("chettam", chettam)],
            states={
                FIRST_STAGE: [
                    CallbackQueryHandler(join, pattern="^join_[0-9]+$"),
                    CallbackQueryHandler(leave, pattern="^leave_[0-9]+$"),
                    CallbackQueryHandler(call, pattern="^call_[0-9]+$",),
                    CallbackQueryHandler(pick_hour, pattern="^pick_hour$"),
                    CallbackQueryHandler(new_game, pattern=HOUR_MINUTE_PATTERN),
                    CallbackQueryHandler(back, pattern="^back_to_main$"),
                    CallbackQueryHandler(status_conv, pattern="^status_conv$"),
                    CallbackQueryHandler(cancel, pattern="^cancel$"),
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
