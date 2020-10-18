#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-

"""
Kostyli i Velosipedy™ BV presents

Chettamm telegram bot for csgo guys.
It helps players to schedule their cs:go games and join them.

Main functionality is run under chettam() function.
It uses inline keyboard buttons inside conversation mode.

In development run bot.py with --debug flag

TODO: implement players' queue tags with class properties.
TODO: game.has_expired? add possibility to delete expired game; prevent from joining an expired game.
TODO: don't allow game creation for timeslot earlier than current time.
TODO: implement unique timeslot for a Game. Current implementation only adds player to existing
      game if timeslot is same. However if game is edited, 2 games can have same timeslot.
"""

import inspect
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


# Inline keyboard actions
def chettam(update, context):
    """Entry point for conversation"""
    context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
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
    player = get_player(update)
    pistol = EMOJI["pistol"]
    cross = EMOJI["cross"]
    chart = EMOJI["chart"]

    if games:
        reply = f"{pluralize(len(games), 'game')} already exist:\n\n{slot_status_all(games)}"
        keyboard = []
        for i, game in enumerate(games):
            time_header = slot_time_header(game)
            button_text = f"{time_header}"
            if player in game.players:
                button_text += " [You joined]"
            keyboard.append(
                [
                    InlineKeyboardButton(
                        button_text, callback_data=f"GAME{game.id}.{i + 1}",
                    )
                ]
            )
    else:
        keyboard = [[]]
        reply = "Game doesn't exist."

    if len(games) < 10:
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

    kb_row1 = []
    kb_row2 = [
        InlineKeyboardButton("« Back", callback_data="start_over"),
        InlineKeyboardButton(f"{cross} Cancel", callback_data="cancel"),
    ]

    if player in game.players:
        kb_row1 = [
            InlineKeyboardButton(f"{zzz} Leave", callback_data="leave_game"),
        ]
        if game.slots >= 3 and game_timediff(game, minutes=-30):
            kb_row1.append(
                InlineKeyboardButton(
                    f"{party} Call everyone", callback_data="call_everyone"
                ),
            )
        kb_row2.insert(
            1,
            InlineKeyboardButton(f"{pencil} Edit", callback_data="edit_existing_game"),
        )
    elif player not in game.players and game.slots < 20:
        kb_row1 = [InlineKeyboardButton(f"{pistol} Join", callback_data="join_game")]

    keyboard = [kb_row1, kb_row2]

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

    # Different callback data for "Back" button based on context
    if data["game_action"] == "new_game":
        callback = "start_over"
    elif data["game_action"] == "edit_existing_game":
        game = data["game"]
        game_num = data["game_num"]
        callback = f"GAME{game.id}.{game_num}"

    cross = EMOJI["cross"]
    keyboard = [
        [
            InlineKeyboardButton("20:00", callback_data="20:00"),
            InlineKeyboardButton("21:00", callback_data="21:00"),
            InlineKeyboardButton("22:00", callback_data="22:00"),
            InlineKeyboardButton("23:00", callback_data="23:00"),
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
            InlineKeyboardButton(f"{hour}:00", callback_data=f"{hour}:00")
            for hour in range(16, 20)
        ],
        [
            InlineKeyboardButton(f"{hour}:00", callback_data=f"{hour}:00")
            for hour in range(20, 24)
        ],
        [
            InlineKeyboardButton(f"{hour:02d}:00", callback_data=f"{hour:02d}:00")
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

    fire = EMOJI["fire"]
    dumpling = EMOJI["dumpling"]
    exclamation = EMOJI["exclamation"]
    invite = random.choice(INVITE)

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
            reply = "Game was edited"
            message = inspect.cleandoc(
                f"""
                {exclamation} {game.players_call_all} warning!\n
                Timeslot changed by {player.mention}:
                Game #{num} {old_ts} -> *{new_ts}*
                """
            )
            send_notification(
                context=context, chat_id=update.effective_chat.id, message=message,
            )
            logger().info(
                'User "%s" edited timeslot "%s" -> "%s" for chat "%s"',
                player,
                old_ts,
                new_ts,
                game.chat_id,
            )
        else:
            reply = "Timeslot wasn't changed"
    else:
        game = search_game(update, new_timeslot)
        if action == "new_game" and not game:
            game = create_game(update.effective_chat, new_timeslot)
            reply = None
            logger().info(
                'User "%s" created new game "%s" for chat "%s"',
                player,
                game.timeslot,
                game.chat_id,
            )
        elif game:
            reply = f"{fire} *{player}* joined! {fire}"

        if player not in game.players:
            game.add_player(player, joined_at=dt.now(pytz.utc))
            game.save()

    if reply:
        t = f"{reply}\n\n{slot_status(game)}"
    else:
        t = slot_status(game)
    query.answer()
    query.edit_message_text(text=t, parse_mode=ParseMode.MARKDOWN)
    context.bot_data.update()
    last_slot_notification(update, context, game)
    return ConversationHandler.END


def slot_in(update, context):
    """Join current game"""
    query = update.callback_query
    player = get_player(update)
    game = context.bot_data["game"]

    game.add_player(player, joined_at=dt.now(pytz.utc))
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
    last_slot_notification(update, context, game)
    return ConversationHandler.END


def slot_out(update, context):
    """Leave current game"""
    query = update.callback_query
    player = get_player(update)
    data = context.bot_data
    game = data["game"]
    game_num = data["game_num"]
    game.players.remove(player)
    game.save()
    cry = EMOJI["cry"]
    if game.players:
        reply = f"{cry} *{player}* left {cry}\n\n{slot_status(game)}"
    else:
        game.delete()
        reply = f"{cry} *{player}* left {cry}\n\nGame #{game_num} {game.timeslot_cet_time} was deleted."
    query.answer()
    query.edit_message_text(text=reply, parse_mode=ParseMode.MARKDOWN)
    logger().info(
        'User "%s" left a game "%s" for chat "%s"', player, game.timeslot, game.chat_id,
    )
    last_slot_notification(update, context, game)
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
    time_header = slot_time_header(game)
    query.answer()
    query.edit_message_text(text=slot_status(game), parse_mode=ParseMode.MARKDOWN)
    send_notification(
        context=context,
        chat_id=update.effective_chat.id,
        message=f"*{time_header}*: {game.players_call_active} go go!",
    )
    return ConversationHandler.END


def last_slot_notification(update, context, game):
    """Notify about last slot"""
    if game.slots == 4 or game.slots == 9:
        random_call = random.choice(BCOM)
        send_notification(
            context=context,
            chat_id=update.effective_chat.id,
            message=f"*{game.timeslot_cet_time}*: {random_call}",
        )


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


# EXPERIMENTAL
# EXPERIMENTAL
# EXPERIMENTAL
# EXPERIMENTAL
# EXPERIMENTAL
# EXPERIMENTAL
# EXPERIMENTAL
# EXPERIMENTAL
# EXPERIMENTAL
# EXPERIMENTAL


def chettam_v2(update, context):
    """Entry point for conversation"""
    context.bot_data["player"] = get_player(update)
    reply, keyboard = get_chettam_v2_data(update, context)
    update.message.reply_markdown(
        reply, reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return FIRST_STAGE


def get_chettam_v2_data(update, context):
    """Reply message and keyboard for entry point"""
    games = get_all_games(update)
    player = context.bot_data["player"]
    pistol = EMOJI["pistol"]
    cross = EMOJI["cross"]
    chart = EMOJI["chart"]
    party = EMOJI["party"]
    zzz = EMOJI["zzz"]

    kb = [
        InlineKeyboardButton(f"{pistol} New", callback_data="new_game"),
    ]

    if games:
        kb.append(InlineKeyboardButton(f"{chart} Status", callback_data="status_conv"))
        reply = slot_status_all(games)
        keyboard = []
        for game in games:
            time_header = game.timeslot_cet_time
            if player in game.players:
                btn_text = f"{time_header}: {zzz} Leave"
                btn_callback = f"leave_{game.id}"
            else:
                btn_text = f"{time_header}: {pistol} Join"
                btn_callback = f"join_{game.id}"
            btn1 = InlineKeyboardButton(btn_text, callback_data=btn_callback)

            if game.slots >= 1:
                btn2 = InlineKeyboardButton(
                    f"{party} Call", callback_data=f"call_{game.id}"
                )
            keyboard.append([btn1, btn2])
    else:
        keyboard = [[]]
        kb.append(InlineKeyboardButton(f"{cross} Cancel", callback_data="cancel"),)
        reply = "Game doesn't exist."

    keyboard.append(kb)
    return reply, keyboard


def chettam_v2_slot_in(update, context):
    """Join current game"""
    query = update.callback_query
    player = context.bot_data["player"]
    game_id = re.search("[0-9]+", query.data).group(0)
    game = get_game(update, game_id)
    game.add_player(player, joined_at=dt.now(pytz.utc))
    game.save()
    return refresh_main_page(update, context, query)


def chettam_v2_slot_out(update, context):
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
    main_hours = [18, 19, 20, 21, 22, 23, 0, 1]
    main_hours_dt = [convert_to_dt(f"{hour:02d}:00") for hour in main_hours]
    ts_games = get_all_games(update, ts_only=True)
    ts_filtered = [ts for ts in main_hours_dt if ts not in ts_games]
    kb = [
        InlineKeyboardButton(
            f"{ts_dt.astimezone(TIMEZONE_CET).strftime('%H:%M')}",
            callback_data=f"{ts_dt.astimezone(TIMEZONE_CET).strftime('%H:%M')}",
        )
        for ts_dt in ts_filtered
    ]
    return row_list_chunks(kb)


def chettam_v2_pick_hour(update, context):
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


def chettam_v2_call_everyone(update, context):
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


def chettam_v2_new_game(update, context):
    """Create new game or edit an existing game"""
    query = update.callback_query
    player = context.bot_data["player"]
    new_timeslot = convert_to_dt(query.data)
    game = create_game(update.effective_chat, new_timeslot)
    game.add_player(player, joined_at=dt.now(pytz.utc))
    game.save()
    return refresh_main_page(update, context, query)


def refresh_main_page(update, context, query):
    reply, keyboard = get_chettam_v2_data(update, context)
    query.answer()
    query.edit_message_text(
        reply,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN,
    )
    return FIRST_STAGE


def chettam_v2_back_to_main(update, context):
    query = update.callback_query
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

    if not is_dayoff():
        dp.add_handler(MessageHandler(Filters.command, dayoff))
    else:
        dp.add_handler(CommandHandler("status", status))
        dp.add_handler(CommandHandler("gogo", gogo))

        chettam_conversation = ConversationHandler(
            entry_points=[CommandHandler("chettam", chettam)],
            states={
                FIRST_STAGE: [
                    CallbackQueryHandler(pick_hour, pattern="^new_game$"),
                    CallbackQueryHandler(pick_hour, pattern="^edit_existing_game$"),
                    CallbackQueryHandler(selected_game, pattern="^GAME[0-9]+\.[0-9]+$"),
                    CallbackQueryHandler(pick_hour, pattern="^back_to_hours$"),
                    CallbackQueryHandler(more_hours, pattern="^more_hours$"),
                    # CallbackQueryHandler(pick_minute, pattern=HOUR_PATTERN),
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
        join_conversation = ConversationHandler(
            entry_points=[CommandHandler("chettam_v2", chettam_v2)],
            states={
                FIRST_STAGE: [
                    CallbackQueryHandler(chettam_v2_slot_in, pattern="^join_[0-9]+$"),
                    CallbackQueryHandler(chettam_v2_slot_out, pattern="^leave_[0-9]+$"),
                    CallbackQueryHandler(
                        chettam_v2_call_everyone, pattern="^call_[0-9]+$",
                    ),
                    CallbackQueryHandler(chettam_v2_pick_hour, pattern="^new_game$"),
                    CallbackQueryHandler(
                        chettam_v2_new_game, pattern=HOUR_MINUTE_PATTERN
                    ),
                    CallbackQueryHandler(
                        chettam_v2_back_to_main, pattern="^back_to_main$"
                    ),
                    CallbackQueryHandler(status_conv, pattern="^status_conv$"),
                    CallbackQueryHandler(cancel, pattern="^cancel$"),
                ],
            },
            fallbacks=[CommandHandler("chettam_v2", chettam_v2)],
        )

        dp.add_handler(chettam_conversation)
        dp.add_handler(join_conversation)

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
