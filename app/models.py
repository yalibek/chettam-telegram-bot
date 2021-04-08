from datetime import datetime as dt, timedelta

import pytz
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    ForeignKey,
    DateTime,
    Boolean,
    ARRAY,
)
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import sessionmaker, relationship, backref
from telegram.utils.helpers import escape_markdown

from app.vars import DB_URL, EMOJI, MAIN_HOURS

# Connect to DB
Base = declarative_base()
engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)
session = Session()


class Generic:
    """Class with generic methods used by all classes"""

    def create(self):
        session.add(self)
        self.save()

    def delete(self):
        session.delete(self)
        self.save()

    @staticmethod
    def save():
        try:
            session.commit()
        except:
            session.rollback()
            raise


class Association(Base, Generic):
    """Many-to-many association table"""

    __tablename__ = "association"
    game_id = Column(Integer, ForeignKey("game.id"), primary_key=True)
    player_id = Column(Integer, ForeignKey("player.id"), primary_key=True)
    joined_at = Column(DateTime)
    in_queue = Column(Boolean, default=False)
    queue_tag = Column(String, default="")
    player = relationship(
        "Player", backref=backref("player_game", cascade="all, delete-orphan")
    )
    game = relationship(
        "Game", backref=backref("player_game", cascade="all, delete-orphan")
    )

    @property
    def is_new(self):
        if dt.utcnow() - self.joined_at < timedelta(minutes=2):
            return EMOJI["fire"]
        else:
            return ""


class Player(Base, Generic):
    __tablename__ = "player"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True)
    username = Column(String, nullable=True)
    first_name = Column(String)
    last_name = Column(String, nullable=True)
    csgo_nickname = Column(String, nullable=True)
    timezone = Column(String, default="Europe/Amsterdam")
    games = relationship("Game", secondary="association", back_populates="players")

    def __str__(self) -> str:
        if self.csgo_nickname:
            return self.csgo_nickname
        elif self.username:
            return self.username
        else:
            return self.first_name

    @property
    def uname_first(self) -> str:
        if self.username:
            return f"{self.username} ({self.first_name})"
        else:
            return self.first_name

    @property
    def mention(self) -> str:
        if self.username:
            return escape_markdown(f"@{self.username}")
        else:
            return f"[{self.first_name}](tg://user?id={self.user_id})"

    @property
    def timezone_pytz(self):
        return pytz.timezone(self.timezone)


class Game(Base, Generic):
    __tablename__ = "game"
    id = Column(Integer, primary_key=True)
    timeslot = Column(DateTime)
    expired = Column(Boolean, default=False)
    players = relationship("Player", secondary="association", back_populates="games")
    chat_id = Column(BigInteger, ForeignKey("chat.id"))

    def add_player(self, player, joined_at):
        self.player_game.append(
            Association(game=self, player=player, joined_at=joined_at)
        )
        self.save()
        self.tag_everyone()

    def remove_player(self, player):
        self.players.remove(player)
        self.save()
        self.tag_everyone()

    def tag_everyone(self):
        """Tag all players with queue tags"""
        for index, assoc in enumerate(self.assoc_sorted):
            tag = ""
            in_queue = False
            if self.slots < 10:
                if index >= 5:
                    tag = "\[_queue_] "
                    in_queue = True
            else:
                if index < 5:
                    tag = "\[_1st_] "
                elif 5 <= index < 10:
                    tag = "\[_2nd_] "
                else:
                    tag = "\[_queue_] "
                    in_queue = True
            assoc.queue_tag = tag
            assoc.in_queue = in_queue
            assoc.save()

    @property
    def timeslot_utc(self) -> dt:
        """'Game.timeslot' stores DateTime object without timezone info.
        That's why we need to convert it back to timezone aware object.
        Use this property instead of 'Game.timeslot' whenever possible."""
        return pytz.utc.localize(self.timeslot)

    @property
    def slots(self) -> int:
        return len(self.players)

    @property
    def assoc_sorted(self) -> list:
        """Sort players by joined_at and return list of associations"""
        return sorted(self.player_game, key=lambda x: x.joined_at)

    @property
    def players_sorted(self) -> list:
        """Return sorted list of names"""
        return [association.player for association in self.assoc_sorted]

    @property
    def players_sorted_active(self) -> list:
        """Return sorted list of names"""
        return [
            association.player
            for association in self.assoc_sorted
            if not association.in_queue
        ]

    @property
    def players_list(self) -> str:
        """Return unnumbered list of players for 1 party with queue or splitted into 2 parties"""
        return "\n".join(
            f"- {assoc.queue_tag}{escape_markdown(str(assoc.player))} {assoc.is_new}"
            for assoc in self.assoc_sorted
        )

    @property
    def players_call_active(self) -> str:
        """Only mention players who are not in queue"""
        return ", ".join(player.mention for player in self.players_sorted_active)


class Chat(Base, Generic):
    __tablename__ = "chat"
    id = Column(BigInteger, primary_key=True)
    chat_type = Column(String)
    title = Column(String)
    timezone = Column(String, default="Europe/Amsterdam")
    days_off = Column(MutableList.as_mutable(ARRAY(String)), default=[])
    main_hours = Column(MutableList.as_mutable(ARRAY(Integer)), default=MAIN_HOURS)
    games = relationship("Game", backref="chat")

    def add_game(self, game):
        self.games.append(game)
        self.save()

    def add_day_off(self, weekday):
        self.days_off.append(weekday)
        self.save()

    def rm_day_off(self, weekday):
        self.days_off.remove(weekday)
        self.save()

    def add_hour(self, hour):
        self.main_hours.append(hour)
        self.save()
        self.reorder_hours()

    def rm_hour(self, hour):
        self.main_hours.remove(hour)
        self.save()

    def reorder_hours(self):
        morning_hours = sorted(i for i in self.main_hours if i < 4)
        day_hours = sorted(i for i in self.main_hours if i > 4)
        self.main_hours = day_hours + morning_hours
        self.save()

    @property
    def timezone_pytz(self):
        return pytz.timezone(self.timezone)


# Create tables in DB
Base.metadata.create_all(bind=engine)
