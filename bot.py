#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-

"""
Chettamm telegram bot for csgo guys
TODO: sort players by joined_at
"""

import inspect
import random
import re
from datetime import date

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
        ]
    )
    update.message.reply_text(
        START_MESSAGE, reply_to_message_id=None,
    )
    update.message.reply_sticker(
        random_sticker, reply_to_message_id=None,
    )


def dayoff(update, context):
    """Dayoff messages"""
    try:
        quote, author = get_quote()
        if not author:
            author = "Unknown"
        reply = f"_{quote}_\n\n — {author}"
    except:
        reply = "It's dayoff, fool!"
    update.message.reply_markdown(reply, reply_to_message_id=None)

    # Notify Aseke about his abstinence period
    today = dt.today().date()
    goal = date(2020, 7, 27)
    diff = goal - today
    if diff.days > 0:
        update.message.reply_markdown(
            f"Aseke can't play for {diff.days} more days", reply_to_message_id=None
        )


def status(update, context):
    """Get games status for current chat"""
    games = get_all_games(update)
    if games:
        update.message.reply_markdown(slot_status_all(games), reply_to_message_id=None)
    else:
        update.message.reply_text("start a game with /chettam")


# Inline keyboard actions
def chettam(update, context):
    """Entry point for conversation"""
    random_int = random.randint(0, 100)
    if random_int == 1:
        reply = f"Enjoing the bot? *Buy me a coffee, maybe?*"
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
    """Fallback function to start conversation over"""
    query = update.callback_query
    reply, keyboard = get_chettam_data(update)
    query.answer()
    query.edit_message_text(
        reply,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN,
    )
    return FIRST_STAGE


def get_chettam_data(update):
    """Reply message and keyboard for entry point"""
    games = get_all_games(update)
    pistol = EMOJI["pistol"]
    cross = EMOJI["cross"]
    chart = EMOJI["chart"]

    if games:
        reply = f"{len(games)} game(s) already exist:\n\n{slot_status_all(games)}"
        keyboard = [
            [
                InlineKeyboardButton(
                    f"Game #{i+1} {game.timeslot_cet_time}",
                    callback_data=f"GAME{game.id}.{i+1}",
                )
            ]
            for i, game in enumerate(games)
        ]
    else:
        keyboard = [[]]
        reply = "Game doesn't exist."

    if len(games) < 4:
        kb = [
            InlineKeyboardButton(f"{pistol} New", callback_data="new_game"),
            InlineKeyboardButton(f"{cross} Cancel", callback_data="cancel"),
        ]
    else:
        kb = [
            InlineKeyboardButton(f"{cross} Cancel", callback_data="cancel"),
        ]

    if games:
        kb.insert(
            -1, InlineKeyboardButton(f"{chart} Status", callback_data="status_conv"),
        )

    keyboard.append(kb)
    return reply, keyboard


def selected_game(update, context):
    """Data for selected game"""
    query = update.callback_query
    player = get_player(update)

    g = re.search("GAME([0-9]+)\.([0-9]+)", query.data)
    game_id = g.group(1)
    game_num = g.group(2)
    game = get_game(update, game_id)
    context.bot_data["game"] = game
    context.bot_data["game_num"] = game_num

    pistol = EMOJI["pistol"]
    pencil = EMOJI["pencil"]
    cross = EMOJI["cross"]
    zzz = EMOJI["zzz"]
    party = EMOJI["party"]

    keyboard = [
        [
            InlineKeyboardButton("« Back", callback_data="start_over"),
            InlineKeyboardButton(f"{pencil} Edit", callback_data="edit_existing_game"),
            InlineKeyboardButton(f"{cross} Cancel", callback_data="cancel"),
        ]
    ]
    if player in game.players:
        kb = [
            InlineKeyboardButton(f"{zzz} Leave", callback_data="leave_game"),
        ]
        if game.slots >= 5:
            kb.append(
                InlineKeyboardButton(
                    f"{party} Call everyone", callback_data="call_everyone"
                ),
            )
        keyboard.insert(0, kb)
    elif player not in game.players and game.slots < 10:
        keyboard.insert(
            0, [InlineKeyboardButton(f"{pistol} Join", callback_data="join_game")]
        )

    reply = f"You picked a game:\n\n{slot_status(game)}"
    query.answer()
    query.edit_message_text(
        text=reply,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN,
    )
    return FIRST_STAGE


def pick_hour(update, context):
    """Choice of hours"""
    query = update.callback_query
    data = context.bot_data
    if query.data in ["new_game", "edit_existing_game"]:
        data["game_action"] = query.data

    if data["game_action"] == "new_game":
        callback = "start_over"
    elif data["game_action"] == "edit_existing_game":
        game = data["game"]
        game_num = data["game_num"]
        callback = f"GAME{game.id}.{game_num}"

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
            InlineKeyboardButton("« Back", callback_data=callback),
            InlineKeyboardButton(f"{cross} Cancel", callback_data="cancel"),
        ],
    ]
    reply = get_reply_for_time_menu(context)
    query.answer()
    query.edit_message_text(
        text=reply, reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return FIRST_STAGE


def more_hours(update, context):
    """Additional choice of hours"""
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
    reply = get_reply_for_time_menu(context)
    query.answer()
    query.edit_message_text(
        text=reply, reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return FIRST_STAGE


def pick_minute(update, context):
    """Choice of minutes"""
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
    reply = get_reply_for_time_menu(context)
    query.answer()
    query.edit_message_text(
        text=reply, reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return FIRST_STAGE


def new_edit_game(update, context):
    """Create new game or edit an existing game"""
    query = update.callback_query
    data = context.bot_data
    action = data["game_action"]
    player = get_player(update)
    new_timeslot = convert_to_dt(query.data)

    if action == "edit_existing_game":
        game = data["game"]
        num = data["game_num"]
        old_ts = game.timeslot_cet_time
        new_ts = new_timeslot.astimezone(TIMEZONE_CET).strftime("%H:%M")

        if game.players and old_ts != new_ts:
            game = update_game(game, new_timeslot)
            message = inspect.cleandoc(
                f"""
                {game.players_call} warning!\n
                Timeslot changed by {player.mention}:
                Game #{num} {old_ts} -> *{new_ts}*
                """
            )
            set_time_alert(update, context, alert_message, message, 0)
            logger().info(
                'User "%s" edited timeslot "%s" -> "%s" for chat "%s"',
                player,
                old_ts,
                new_ts,
                game.chat_id,
            )
    elif action == "new_game":
        game = create_game(update.effective_chat, new_timeslot)
        logger().info(
            'User "%s" created new game "%s" for chat "%s"',
            player,
            game.timeslot,
            game.chat_id,
        )

    game.players.append(player)
    game.updated_at = dt.now(pytz.utc)
    game.save()

    fire = EMOJI["fire"]
    invite = random.choice(INVITE)
    query.answer()
    query.edit_message_text(
        text=f"{fire} {invite}\n\n{slot_status(game)}", parse_mode=ParseMode.MARKDOWN
    )
    context.bot_data.update()
    return ConversationHandler.END


def slot_in(update, context):
    """Join current game"""
    query = update.callback_query
    player = get_player(update)
    game = context.bot_data["game"]
    game.updated_at = dt.now(pytz.utc)
    game.players.append(player)
    game.save()
    fire = EMOJI["fire"]
    reply = f"{fire} *{player}* joined! {fire}\n\n{slot_status(game)}"
    query.answer()
    query.edit_message_text(text=reply, parse_mode=ParseMode.MARKDOWN)
    logger().info(
        'User "%s" joined a game "%s" for chat "%s"',
        player,
        game.timeslot,
        game.chat_id,
    )
    return ConversationHandler.END


def slot_out(update, context):
    """Leave current game"""
    query = update.callback_query
    player = get_player(update)
    game = context.bot_data["game"]
    game.players.remove(player)
    game.updated_at = dt.now(pytz.utc)
    game.save()
    cry = EMOJI["cry"]
    if game.players:
        reply = f"{cry} *{player}* left {cry}\n\n{slot_status(game)}"
    else:
        game.delete()
        reply = (
            f"{cry} *{player}* left {cry}\n\nGame {game.timeslot_cet_time} was deleted."
        )
    query.answer()
    query.edit_message_text(text=reply, parse_mode=ParseMode.MARKDOWN)
    logger().info(
        'User "%s" left a game "%s" for chat "%s"', player, game.timeslot, game.chat_id,
    )
    return ConversationHandler.END


def status_conv(update, context):
    """Get games status for current chat"""
    query = update.callback_query
    games = get_all_games(update)
    query.answer()
    query.edit_message_text(text=slot_status_all(games), parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END


def call_everyone(update, context):
    """Mention all players about current game"""
    query = update.callback_query
    game = context.bot_data["game"]
    query.answer()
    query.edit_message_text(text=slot_status(game), parse_mode=ParseMode.MARKDOWN)
    message = f"*{game.timeslot_cet_time}*: {game.players_call} go go!"
    set_time_alert(update, context, alert_message, message, 0)
    return ConversationHandler.END


def cancel(update, context):
    """End current conversation"""
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="cancelled :(")
    return ConversationHandler.END


def alert_message(context, message):
    """Alert used by bot jobs"""
    job = context.job
    context.bot.send_message(job.context, text=message, parse_mode=ParseMode.MARKDOWN)


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
        dp.add_handler(CommandHandler("status", status))

        chettam_conversation = ConversationHandler(
            entry_points=[CommandHandler("chettam", chettam)],
            states={
                FIRST_STAGE: [
                    CallbackQueryHandler(pick_hour, pattern="^new_game$"),
                    CallbackQueryHandler(pick_hour, pattern="^edit_existing_game$"),
                    CallbackQueryHandler(selected_game, pattern="^GAME[0-9]+\.[0-9]+$"),
                    CallbackQueryHandler(pick_hour, pattern="^back_to_hours$"),
                    CallbackQueryHandler(more_hours, pattern="^more_hours$"),
                    CallbackQueryHandler(pick_minute, pattern=HOUR_PATTERN),
                    CallbackQueryHandler(
                        new_edit_game,
                        pattern=HOUR_MINUTE_PATTERN,
                        pass_job_queue=True,
                        pass_chat_data=True,
                    ),
                    CallbackQueryHandler(slot_in, pattern="^join_game$"),
                    CallbackQueryHandler(slot_out, pattern="^leave_game$"),
                    CallbackQueryHandler(
                        call_everyone,
                        pattern="^call_everyone$",
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
