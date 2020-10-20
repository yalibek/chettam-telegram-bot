from datetime import datetime as dt

from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    ForeignKey,
    DateTime,
    Boolean,
)
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref
from telegram.utils.helpers import escape_markdown

from vars import DB_URL, TIMEZONE_UTC

# Connect to DB
Base = declarative_base()
engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)
session = Session()


class Association(Base):
    """Many-to-many association table"""

    __tablename__ = "association"
    game_id = Column(Integer, ForeignKey("game.id"), primary_key=True)
    player_id = Column(Integer, ForeignKey("player.id"), primary_key=True)
    joined_at = Column(DateTime)
    player = relationship(
        "Player", backref=backref("player_game", cascade="all, delete-orphan")
    )
    game = relationship(
        "Game", backref=backref("player_game", cascade="all, delete-orphan")
    )


class Generic:
    """Class with generic methods used by both Player and Game classes"""

    def create(self):
        session.add(self)
        self.save()

    def delete(self):
        session.delete(self)
        self.save()

    @staticmethod
    def save():
        session.commit()


class Player(Base, Generic):
    """Class for user"""

    __tablename__ = "player"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True)
    username = Column(String, nullable=True)
    first_name = Column(String)
    last_name = Column(String, nullable=True)
    csgo_nickname = Column(String, nullable=True)
    games = relationship("Game", secondary="association", back_populates="players")

    def __str__(self) -> str:
        if self.csgo_nickname:
            return self.csgo_nickname
        elif self.username:
            return self.username
        else:
            return self.first_name

    @property
    def mention(self) -> str:
        if self.username:
            return escape_markdown(f"@{self.username}")
        else:
            return f"[{self.first_name}](tg://user?id={self.user_id})"


class Game(Base, Generic):
    """Class for unique game per chat"""

    __tablename__ = "game"
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger)
    chat_type = Column(String)
    timeslot = Column(DateTime)
    expired = Column(Boolean, default=False)
    players = relationship("Player", secondary="association", back_populates="games")

    def add_player(self, player, joined_at):
        self.player_game.append(
            Association(game=self, player=player, joined_at=joined_at)
        )

    @property
    def timeslot_utc(self) -> dt:
        """'Game.timeslot' stores DateTime object without timezone info.
        That's why we need to convert it back to timezone aware object.
        Use this property instead of 'Game.timeslot' whenever possible."""
        return TIMEZONE_UTC.localize(self.timeslot)

    @property
    def slots(self) -> int:
        return len(self.players)

    @property
    def players_sorted(self) -> list:
        """Sort players by joined_at and return list of names"""
        sorted_association = sorted(self.player_game, key=lambda x: x.joined_at)
        return [association.player for association in sorted_association]

    @property
    def players_list(self) -> str:
        """Return unnumbered list of players for 1 party with queue or splitted into 2 parties"""
        players = [escape_markdown(str(uname)) for uname in self.players_sorted]
        if self.slots < 10:
            appendix1 = ""
            appendix2 = "\[_queue_] "
        else:
            appendix1 = "\[_1st_] "
            appendix2 = "\[_2nd_] "
        return "\n".join(
            f"- {appendix1}{player_name}"
            if index < 5
            else f"- {appendix2}{player_name}"
            if 5 <= index < 10
            else f"- \[_queue_] {player_name}"
            for index, player_name in enumerate(players)
        )

    @property
    def players_call_active(self) -> str:
        """Only mention players who are not in queue"""
        if self.slots < 10:
            active_players = self.players_sorted[:5]
        else:
            active_players = self.players_sorted[:10]
        return ", ".join(player.mention for player in active_players)


# Create tables in DB
Base.metadata.create_all(bind=engine)
