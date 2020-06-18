import logging
from datetime import datetime, timedelta

from models import Game, Player, session
from vars import EMOJI


# Updates player's data if it has changed
def sync_player_data(player, user):
    p = [player.username, player.first_name, player.last_name]
    u = [user.username, user.first_name, user.last_name]
    if p != u:
        player.username = user.username
        player.first_name = user.first_name
        player.last_name = user.last_name
        player.save()


# Returns Player model for current user
def get_player(update):
    user = update.effective_user
    player = session.query(Player).filter_by(user_id=user.id).first()
    if player:
        sync_player_data(player, user)
    else:
        player = Player(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )
        player.create()
        player.save()
    return player


# Create new game
def create_game(chat, timeslot):
    game = Game(
        updated_at=datetime.now(),
        timeslot=timeslot,
        chat_id=chat.id,
        chat_type=chat.type,
    )
    game.create()
    game.save()
    return game


# Returns Game model for current chat
def get_game(update, timeslot=None):
    chat = update.effective_chat
    game = session.query(Game).filter_by(chat_id=chat.id).first()
    if game and timeslot:
        # Update timeslot if given
        game.timeslot = timeslot
        game.updated_at = datetime.now()
        game.save()
    elif game and datetime.now() - game.updated_at > timedelta(hours=8):
        # Delete existing game if it wasn't updated for 8 hours
        game.delete()
        game = None
    elif not game and timeslot:
        # Create new game only if new timeslot is given
        game = create_game(chat, timeslot)
    return game


# Returns slots data
def slot_status(game):
    players = "\n".join(f"- {player}" for player in game.players_list)
    slots = game.slots
    timeslot = game.timeslot
    pistol = EMOJI["pistol"]
    if slots == 0:
        reply = f"All slots are available!"
    elif 5 <= slots < 10:
        reply = f"{slots} slot(s). 1 full party! {pistol}"
    elif slots == 10:
        reply = f"10 slots. 2 parties! gogo! {pistol}{pistol}"
    else:
        reply = f"{slots} slot(s) taken."
    return f"*{timeslot}*: {reply}\n{players}"


# Checks if today is cs:go dayoff
def is_dayoff():
    is_not_night = datetime.today().hour >= 6
    is_wed_sun = datetime.today().strftime("%w") in ["3", "7"]
    return is_not_night and is_wed_sun


# Enables logging
def logger():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    return logging.getLogger(__name__)
