#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-

"""
Chettamm telegram bot for csgo guys
TODO: добавь еще slot_next_in, чтобы бот создал 2й пати и добавлял туда уже
TODO: Предлагаю когда набирается команда предлагать poll на время игры. 5 из очереди согласные на это время формируют команду
TODO: sort players by joined_at
TODO: 2 parties
TODO: game reminder
"""

import random
from datetime import datetime as dt

import pytz
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    Filters,
)

from functions import get_player, get_game, slot_status, is_dayoff, logger
from vars import (
    DEBUG,
    TOKEN,
    PORT,
    HEROKU_APP,
    EMOJI,
    INVITE,
    HOUR_PATTERN,
    HOUR_MINUTE_PATTERN,
    FIRST_STAGE,
    PARROT_COFFEE,
)


def error(update, context):
    """Log Errors caused by Updates."""
    logger().warning('Update "%s" caused error "%s"', update, context.error)


# Command actions
def dayoff(update, context):
    update.message.reply_text("It's day off, fool!")


def status(update, context):
    game = get_game(update)
    if game:
        update.message.reply_markdown(slot_status(game), reply_to_message_id=None)
    else:
        update.message.reply_text("start a game with /chettam")


def slot_in(update, context):
    player = get_player(update)
    game = get_game(update)
    if game:
        if game.slots < 10:
            if player in game.players:
                status(update, context)
                return
            else:
                game.players.append(player)
                game.updated_at = dt.now(pytz.utc)
                game.save()
                fire = EMOJI["fire"]
                reply = f"{fire} *{player}* joined! {fire}\n\n{slot_status(game)}"
        else:
            reply = f"No more than 10 players allowed."
        update.message.reply_markdown(reply, reply_to_message_id=None)
    else:
        update.message.reply_text("start a game with /chettam")


def slot_out(update, context):
    player = get_player(update)
    game = get_game(update)
    if game:
        if player in game.players:
            game.players.remove(player)
            game.updated_at = dt.now(pytz.utc)
            game.save()
            cry = EMOJI["cry"]
            reply = f"{cry} *{player}* left {cry}\n\n{slot_status(game)}"
        else:
            status(update, context)
            return
        update.message.reply_markdown(reply, reply_to_message_id=None)
    else:
        update.message.reply_text("start a game with /chettam")


def join_game(update, context):
    query = update.callback_query
    player = get_player(update)
    game = get_game(update)
    game.updated_at = dt.now(pytz.utc)
    game.players.append(player)
    game.save()
    fire = EMOJI["fire"]
    reply = f"{fire} *{player}* joined! {fire}\n\n{slot_status(game)}"
    query.answer()
    query.edit_message_text(text=reply, parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END


def leave_game(update, context):
    query = update.callback_query
    player = get_player(update)
    game = get_game(update)
    game.players.remove(player)
    game.updated_at = dt.now(pytz.utc)
    game.save()
    cry = EMOJI["cry"]
    reply = f"{cry} *{player}* left {cry}\n\n{slot_status(game)}"
    query.answer()
    query.edit_message_text(text=reply, parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END


# Inline keyboard actions
def get_chettam_data(update):
    game = get_game(update)
    player = get_player(update)
    pistol = EMOJI["pistol"]
    pencil = EMOJI["pencil"]
    chart = EMOJI["chart"]
    cross = EMOJI["cross"]
    zzz = EMOJI["zzz"]
    if game:
        reply = f"Game already exist:\n\n{slot_status(game)}"
        keyboard = [
            [
                InlineKeyboardButton(f"{pencil} Edit", callback_data="game"),
                InlineKeyboardButton(f"{chart} Status", callback_data="status_conv"),
                InlineKeyboardButton(f"{cross} Cancel", callback_data="cancel"),
            ]
        ]
        if player in game.players:
            keyboard.insert(
                0, [InlineKeyboardButton(f"{zzz} Leave", callback_data="leave_game")]
            )
        elif player not in game.players and game.slots < 10:
            keyboard.insert(
                0, [InlineKeyboardButton(f"{pistol} Join", callback_data="join_game")]
            )
    else:
        reply = "Game doesn't exist."
        keyboard = [
            [
                InlineKeyboardButton(f"{pistol} New game", callback_data="game"),
                InlineKeyboardButton(f"{cross} Cancel", callback_data="cancel"),
            ]
        ]
    return reply, keyboard


def chettam(update, context):
    random_int = random.randint(0, 200)
    if random_int == 1:
        reply = f"Enjoing the bot? *Buy me a coffee.*"
        update.message.reply_markdown(reply, reply_to_message_id=None)
        update.message.reply_sticker(
            PARROT_COFFEE, reply_to_message_id=None,
        )
    reply, keyboard = get_chettam_data(update)
    update.message.reply_markdown(
        reply, reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return FIRST_STAGE


def start_over(update, context):
    query = update.callback_query
    reply, keyboard = get_chettam_data(update)
    query.answer()
    query.edit_message_text(
        reply,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN,
    )
    return FIRST_STAGE


def pick_hour(update, context):
    query = update.callback_query
    cross = EMOJI["cross"]
    keyboard = [
        [
            InlineKeyboardButton("20:xx", callback_data="20"),
            InlineKeyboardButton("21:xx", callback_data="21"),
            InlineKeyboardButton("22:xx", callback_data="22"),
            InlineKeyboardButton("23:xx", callback_data="23"),
            InlineKeyboardButton("+", callback_data="more_hours"),
        ],
        [
            InlineKeyboardButton("« Back", callback_data="start_over"),
            InlineKeyboardButton(f"{cross} Cancel", callback_data="cancel"),
        ],
    ]
    query.answer()
    query.edit_message_text(
        text="Choose time:", reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return FIRST_STAGE


def more_hours(update, context):
    query = update.callback_query
    cross = EMOJI["cross"]
    keyboard = [
        [
            InlineKeyboardButton(f"{hour}:xx", callback_data=hour)
            for hour in range(16, 20)
        ],
        [
            InlineKeyboardButton(f"{hour}:xx", callback_data=hour)
            for hour in range(20, 24)
        ],
        [
            InlineKeyboardButton(f"{hour:02d}:xx", callback_data=f"{hour:02d}")
            for hour in range(0, 4)
        ],
        [
            InlineKeyboardButton("« Back", callback_data="back_to_hours"),
            InlineKeyboardButton(f"{cross} Cancel", callback_data="cancel"),
        ],
    ]
    query.answer()
    query.edit_message_text(
        text="Choose time:", reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return FIRST_STAGE


def pick_minute(update, context):
    query = update.callback_query
    hour = query.data
    cross = EMOJI["cross"]
    keyboard = [
        [
            InlineKeyboardButton(f"{hour}:00", callback_data=f"{hour}:00"),
            InlineKeyboardButton(f"{hour}:15", callback_data=f"{hour}:15"),
            InlineKeyboardButton(f"{hour}:30", callback_data=f"{hour}:30"),
            InlineKeyboardButton(f"{hour}:45", callback_data=f"{hour}:45"),
        ],
        [
            InlineKeyboardButton("« Back", callback_data="back_to_hours"),
            InlineKeyboardButton(f"{cross} Cancel", callback_data="cancel"),
        ],
    ]
    query.answer()
    query.edit_message_text(
        text="Choose time:", reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return FIRST_STAGE


def new_game(update, context):
    query = update.callback_query
    invite = random.choice(INVITE)
    fire = EMOJI["fire"]
    game = get_game(update, timeslot=query.data)
    player = get_player(update)
    game.players.append(player)
    game.updated_at = dt.now(pytz.utc)
    game.save()
    query.answer()
    query.edit_message_text(
        text=f"{fire} {invite}\n\n{slot_status(game)}", parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END


def status_conv(update, context):
    query = update.callback_query
    game = get_game(update)
    query.answer()
    query.edit_message_text(text=slot_status(game), parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END


def cancel(update, context):
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="cancelled :(")
    return ConversationHandler.END


def main():
    """Run bot"""
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Log all errors
    dp.add_error_handler(error)

    # Handlers
    if is_dayoff():
        dp.add_handler(MessageHandler(Filters.command, dayoff))
    else:
        dp.add_handler(CommandHandler("slot_in", slot_in))
        dp.add_handler(CommandHandler("slot_out", slot_out))
        dp.add_handler(CommandHandler("status", status))

        chettam_conversation = ConversationHandler(
            entry_points=[CommandHandler("chettam", chettam)],
            states={
                FIRST_STAGE: [
                    CallbackQueryHandler(pick_hour, pattern="^game$"),
                    CallbackQueryHandler(pick_hour, pattern="^back_to_hours$"),
                    CallbackQueryHandler(more_hours, pattern="^more_hours$"),
                    CallbackQueryHandler(pick_minute, pattern=HOUR_PATTERN),
                    CallbackQueryHandler(new_game, pattern=HOUR_MINUTE_PATTERN),
                    CallbackQueryHandler(join_game, pattern="^join_game$"),
                    CallbackQueryHandler(leave_game, pattern="^leave_game$"),
                    CallbackQueryHandler(status_conv, pattern="^status_conv$"),
                    CallbackQueryHandler(start_over, pattern="^start_over$"),
                    CallbackQueryHandler(cancel, pattern="^cancel$"),
                ],
            },
            fallbacks=[CommandHandler("chettam", chettam)],
        )

        dp.add_handler(chettam_conversation)

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
    main()
