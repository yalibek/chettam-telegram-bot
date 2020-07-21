from datetime import datetime as dt

import pytz
from sqlalchemy import Column, Integer, BigInteger, String, ForeignKey, DateTime
from sqlalchemy import create_engine, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from telegram.utils.helpers import escape_markdown

from vars import DB_URL, TIMEZONE_CET, TIMEZONE_UTC

# Connect to DB
Base = declarative_base()
engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)
session = Session()


# Many-to-many association table
association_table = Table(
    "association",
    Base.metadata,
    Column("player_id", Integer, ForeignKey("player.id")),
    Column("game_id", Integer, ForeignKey("game.id")),
)


class Generic:
    """Class with generic methods used by both Player and Game classes"""

    def create(self):
        session.add(self)
        session.commit()

    def delete(self):
        session.delete(self)
        session.commit()

    def save(self):
        self.updated_at = dt.now(pytz.utc)
        session.commit()


class Player(Base, Generic):
    """Class for user"""

    __tablename__ = "player"
    id = Column(Integer, primary_key=True)
    updated_at = Column(DateTime, default=dt.now(pytz.utc))
    user_id = Column(BigInteger, unique=True)
    username = Column(String, nullable=True)
    first_name = Column(String)
    last_name = Column(String, nullable=True)
    games = relationship("Game", secondary=association_table, back_populates="players")

    def __str__(self) -> str:
        if self.username:
            return f"{self.username}"
        elif self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        else:
            return f"{self.first_name}"

    @property
    def mention(self) -> str:
        if self.username:
            return f"@{self.username}"
        else:
            return f"[{self.first_name}](tg://user?id={self.user_id})"


class Game(Base, Generic):
    """Class for unique game per chat"""

    __tablename__ = "game"
    id = Column(Integer, primary_key=True)
    updated_at = Column(DateTime, default=dt.now(pytz.utc))
    chat_id = Column(BigInteger)
    chat_type = Column(String)
    timeslot = Column(DateTime)
    players = relationship(
        "Player", secondary=association_table, back_populates="games"
    )

    @property
    def players_list(self) -> list:
        p = sorted(self.players, key=lambda player: player.updated_at)
        return [escape_markdown(str(player)) for player in p]

    @property
    def players_call(self) -> str:
        return ", ".join(escape_markdown(player.mention) for player in self.players)

    @property
    def slots(self) -> int:
        return len(self.players)

    @property
    def timeslot_utc(self) -> dt:
        return TIMEZONE_UTC.localize(self.timeslot)

    @property
    def timeslot_cet(self) -> dt:
        return self.timeslot_utc.astimezone(TIMEZONE_CET)

    @property
    def timeslot_cet_time(self) -> str:
        return self.timeslot_cet.strftime("%H:%M")


# Create tables in DB
Base.metadata.create_all(bind=engine)
