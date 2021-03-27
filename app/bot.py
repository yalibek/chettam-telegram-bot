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
import os
import random
import re
import textwrap
import uuid
from datetime import datetime as dt

import pytz
import sentry_sdk
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from emoji import UNICODE_EMOJI, demojize
from tabulate import tabulate
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import (
    Updater,
    CommandHandler,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
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
    USAGE_TEXT,
    USERNAME_COLORS,
    COLORS,
    SECONDARY_STATE,
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
def slot_in_out(update, context):
    lines = [line for line in update.message.text.split("/") if line != ""]
    for line in lines:
        command = line.split()[0]
        args = line.split()[1:]
        if args:
            if command in chop("in"):
                in_out(update, context, action="in", hard_args=args)
            elif command in chop("out"):
                in_out(update, context, action="out", hard_args=args)
        else:
            update.message.reply_markdown(USAGE_TEXT)
            return
    update.message.reply_markdown(get_status_reply(update))


@restricted
@sync_games
def all_in_out(update, context):
    args = context.args
    if args and args[0] == "in":
        in_out(update, context, action="in", hard_args=["all"])
    elif args and args[0] == "out":
        in_out(update, context, action="out", hard_args=["all"])
    update.message.reply_markdown(get_status_reply(update))


@restricted
@sync_games
def menu(update, context):
    keyboard = [
        [InlineKeyboardButton("Set user's nickname", callback_data="user_nickname")],
        [InlineKeyboardButton("Set user's timezone", callback_data="user_timezone")],
        [InlineKeyboardButton("Data", callback_data="data")],
    ]
    update.message.reply_markdown(
        text="Menu",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return MAIN_STATE


def user_timezone(update, context):
    """Set current user's timezone"""
    query = update.callback_query
    player = get_player(update)
    keyboard = [
        [InlineKeyboardButton(f"{tz}, {code}", callback_data=f"TZ_{tz}")]
        for tz, code in COMMON_TIMEZONES.items()
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
    query.edit_message_text(text=f"Your TZ was set to {new_tz}")
    return MAIN_STATE


def user_nickname(update, context):
    query = update.callback_query
    player = get_player(update)
    reply = ""
    if player.csgo_nickname:
        reply += f'Your nickname is "{player.csgo_nickname}"'
    else:
        reply += f"You don't have nickname configured"
    reply += "\nReply to this message with your new nickname (30 chars)"
    query.edit_message_text(text=reply)
    return SECONDARY_STATE


def set_user_nickname(update, context):
    nickname = update.message.text
    sanitized_nickname = nickname.strip().replace("\n", " ")[:30]
    player = get_player(update)
    player.csgo_nickname = sanitized_nickname
    player.save()
    update.message.reply_text(text=f'Your nickname was set to "{sanitized_nickname}"')
    return ConversationHandler.END


import matplotlib.pyplot as plt
import pandas as pd


def data(update, context):
    query = update.callback_query
    df = get_all_data(chat_id=update.effective_chat.id)
    table, graph = data_games_played(df)
    query.edit_message_text(text=f"```\n{table}```", parse_mode=ParseMode.MARKDOWN)
    context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(graph, "rb"))
    os.remove(graph)
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
    # per date
    df["timeslot"] = df["timeslot"].dt.date
    df = df.groupby("timeslot").nunique()
    df["game_id"].plot(
        x="game_id",
        y="Games played",
        title="Games per day",
        figsize=(15, 6),
        rot=45,
        kind="bar",
    )
    graph = f"./temp_{uuid.uuid4().hex}.png"
    plt.tight_layout()
    plt.savefig(graph, dpi=300)
    table = tabulate(tabular_data=data_table, headers=["Player", "Games played"])
    return table, graph


# def data_popular_timeslot(df):
#     uniq_timeslot = df["timeslot"].value_counts()
#     data_table = [[timeslot, count] for timeslot, count in uniq_timeslot.iteritems()]
#     return tabulate(tabular_data=data_table, headers=["Timeslot", "Games played"])


# Conversation actions
@restricted
@sync_games
def chettam(update, context):
    """Entry point for conversation"""
    reply, keyboard = get_chettam_data(update, context)
    update.message.reply_markdown(reply, reply_markup=InlineKeyboardMarkup(keyboard))
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
        ]
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


def get_sticker(update, context):
    """Replies with an image of the forwarded message"""
    msg = update.message
    target_user = msg.forward_from
    if target_user:
        photos = target_user.get_profile_photos().photos
        if photos:
            profile_photo = photos[0][0]
        else:
            profile_photo = None

        font_size = 20
        img_w = 450
        img_h = 80
        padding_l = 30

        wrapped_text = textwrap.fill(text=msg.text, width=25)
        print(wrapped_text)
        for char in wrapped_text:
            if char in UNICODE_EMOJI:
                print(char)
                font_family = "./.fonts/Apple Color Emoji.ttc"
                # wrapped_text = char

        for _ in wrapped_text.split("\n"):
            img_h += font_size + 2

        if img_h > 512:
            msg.reply_text(text="max height reached (512px")
            return

        bg_params = {
            "mode": "RGBA",
            "size": (img_w, img_h),
            "color": COLORS["white"],
        }

        # Create the image
        img = Image.new(**bg_params)
        font_family = "./.fonts/LucidaGrande.ttc"
        font = ImageFont.truetype(font=font_family, size=font_size, index=0)
        font_bold = ImageFont.truetype(font=font_family, size=font_size, index=1)

        # img.paste(im=profile_photo, box=(0, 0))
        r = 25
        x = padding_l + r
        y = 45
        leftUpPoint = (x - r, y - r)
        rightDownPoint = (x + r, y + r)
        user_color = random.choice(list(USERNAME_COLORS.values()))

        draw = ImageDraw.Draw(img)
        draw.ellipse(xy=(leftUpPoint, rightDownPoint), fill=user_color)
        draw.text(
            xy=(padding_l + 2 * r + 20, 20),
            text=target_user.full_name,
            fill=user_color,
            font=font_bold,
            embedded_color=True,
        )
        draw.text(
            xy=(padding_l + 2 * r + 20, 50),
            text=wrapped_text,
            fill=COLORS["black"],
            font=font,
            # font=ImageFont.truetype(font="./.fonts/Apple Color Emoji.ttc", size=20, index=0),
            embedded_color=True,
        )

        # Save an image and send it
        temp_file = f"./temp_{uuid.uuid4().hex}.png"
        img.save(temp_file, dpi=(300, 300), quality=95)
        msg.reply_photo(photo=open(temp_file, "rb"))
        os.remove(temp_file)


def main():
    """Run bot"""
    updater = Updater(token=TOKEN, use_context=True)
    updater.bot.set_my_commands(commands=COMMANDS)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Log all errors
    dp.add_error_handler(callback=error)

    # Handlers
    dp.add_handler(CommandHandler(command="status", callback=status))
    dp.add_handler(CommandHandler(command="all", callback=all_in_out))
    dp.add_handler(
        CommandHandler(command=chop("in") + chop("out"), callback=slot_in_out)
    )
    dp.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler(command=chop("chettam"), callback=chettam)],
            fallbacks=[CommandHandler(command=chop("chettam"), callback=chettam)],
            states={
                MAIN_STATE: [
                    CallbackQueryHandler(callback=join, pattern="^join_[0-9]+$"),
                    CallbackQueryHandler(callback=leave, pattern="^leave_[0-9]+$"),
                    CallbackQueryHandler(callback=call, pattern="^call_[0-9]+$"),
                    CallbackQueryHandler(callback=pick_hour, pattern="^pick_hour$"),
                    CallbackQueryHandler(
                        callback=new_game, pattern=HOUR_MINUTE_PATTERN
                    ),
                    CallbackQueryHandler(callback=back, pattern="^back_to_main$"),
                    CallbackQueryHandler(callback=status_conv, pattern="^status_conv$"),
                ],
            },
        )
    )
    dp.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler(command="menu", callback=menu)],
            fallbacks=[CommandHandler(command="menu", callback=menu)],
            states={
                MAIN_STATE: [
                    CallbackQueryHandler(callback=data, pattern="^data$"),
                    CallbackQueryHandler(
                        callback=user_timezone, pattern="^user_timezone$"
                    ),
                    CallbackQueryHandler(
                        callback=set_user_timezone, pattern="^TZ_[a-zA-Z\/]+$"
                    ),
                    CallbackQueryHandler(
                        callback=user_nickname, pattern="^user_nickname$"
                    ),
                ],
                SECONDARY_STATE: [
                    MessageHandler(
                        filters=Filters.reply & Filters.text & ~Filters.command,
                        callback=set_user_nickname,
                    )
                ],
            },
        )
    )
    dp.add_handler(
        MessageHandler(filters=Filters.text & Filters.forwarded, callback=get_sticker)
    )
    # Start
    if DEBUG:
        # Start the Bot (polling method)
        updater.start_polling()
    else:
        # Set Heroku handlers and start the Bot (webhook method)
        updater.start_webhook(
            listen=HOST,
            port=PORT,
            url_path=TOKEN,
            webhook_url=APP_URL + TOKEN,
        )

    # Block until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == "__main__":
    sentry_sdk.init(SENTRY_DSN)
    main()
