#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-

"""
Chettamm telegram bot for csgo guys
TODO: добавь еще slot_next_in, чтобы бот создал 2й пати и добавлял туда уже
TODO: Предлагаю когда набирается команда предлагать poll на время игры. 5 из очереди согласные на это время формируют команду
TODO: sort players by joined_at
TODO: 2 parties
TODO: logging
TODO: refactor!!!
TODO: comments!!!
"""

import random

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
    random_sticker = random.choice(
        [
            STICKERS["lenin"],
            STICKERS["racoon"],
            STICKERS["borat"],
            STICKERS["harry"],
            STICKERS["sheikh"],
        ]
    )
    update.message.reply_text(
        START_MESSAGE, reply_to_message_id=None,
    )
    update.message.reply_sticker(
        random_sticker, reply_to_message_id=None,
    )


def dayoff(update, context):
    try:
        quote, author = get_quote()
        if not author:
            author = "Unknown"
        reply = f"_{quote}_\n\n — {author}"
    except:
        reply = "It's dayoff, fool!"
    update.message.reply_markdown(reply, reply_to_message_id=None)


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


def slot_in_conv(update, context):
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


def slot_out_conv(update, context):
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
    party = EMOJI["party"]
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
            kb = [
                InlineKeyboardButton(f"{zzz} Leave", callback_data="leave_game"),
            ]
            if game.slots >= 5:
                kb.insert(
                    1,
                    InlineKeyboardButton(
                        f"{party} Call everyone", callback_data="call_players"
                    ),
                )
            keyboard.insert(0, kb)
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
    random_int = random.randint(0, 100)
    if random_int == 1:
        reply = f"Enjoing the bot? *Buy me a coffee, maybe?.*"
        parrot = STICKERS["coffee_parrot"]
        update.message.reply_markdown(reply, reply_to_message_id=None)
        update.message.reply_sticker(
            parrot, reply_to_message_id=None,
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
            InlineKeyboardButton(
                f"{hour}:{minutes:02d}", callback_data=f"{hour}:{minutes:02d}"
            )
            for minutes in range(0, 60, 15)
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


def alert_game(context, game):
    """Send the alarm message."""
    job = context.job
    timediff = to_utc(game.timeslot).minute - dt.now(pytz.utc).minute
    players = ", ".join(game.players_call)
    reply = f"{players} game starts in {timediff} min(s)!"
    if players:
        context.bot.send_message(job.context, text=reply)


def set_time_alert(update, context, alert, due, game):
    # Set time alert
    chat_id = update.effective_chat.id
    if "job" in context.chat_data:
        old_job = context.chat_data["job"]
        old_job.schedule_removal()

    # Hack to pass additional args to alert()
    partial_alert = wrapped_partial(alert, game=game)
    new_job = context.job_queue.run_once(partial_alert, due, context=chat_id)
    context.chat_data["job"] = new_job


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
    # if to_utc(game.timeslot) > dt.now(pytz.utc):
    #     due = to_utc(game.timeslot) - timedelta(minutes=5)
    #     set_time_alert(update, context, alert_game, due, game)
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


def alert_players(context, game):
    """Send the alarm message."""
    job = context.job
    players = [p.callme for p in game.players]
    timeslot = game.timeslot_cet.strftime("%H:%M")
    reply = f"*{timeslot}*: {', '.join(players)} go go!"
    context.bot.send_message(job.context, text=reply, parse_mode=ParseMode.MARKDOWN)


def call_players(update, context):
    query = update.callback_query
    game = get_game(update)
    query.answer()
    query.edit_message_text(text=slot_status(game), parse_mode=ParseMode.MARKDOWN)
    set_time_alert(update, context, alert_players, 0, game)
    return ConversationHandler.END


def main():
    """Run bot"""
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Log all errors
    dp.add_error_handler(error)

    # Handlers
    dp.add_handler(CommandHandler("start", start))

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
                    CallbackQueryHandler(
                        new_game,
                        pattern=HOUR_MINUTE_PATTERN,
                        pass_job_queue=True,
                        pass_chat_data=True,
                    ),
                    CallbackQueryHandler(slot_in_conv, pattern="^join_game$"),
                    CallbackQueryHandler(slot_out_conv, pattern="^leave_game$"),
                    CallbackQueryHandler(
                        call_players,
                        pattern="^call_players$",
                        pass_job_queue=True,
                        pass_chat_data=True,
                    ),
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
    sentry_sdk.init(SENTRY_DSN)
    main()
