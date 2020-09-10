from datetime import datetime as dt

from sqlalchemy import Column, Integer, BigInteger, String, ForeignKey, DateTime
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref
from telegram.utils.helpers import escape_markdown

from vars import DB_URL, TIMEZONE_CET, TIMEZONE_UTC

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
    games = relationship("Game", secondary="association", back_populates="players")

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
    chat_id = Column(BigInteger)
    chat_type = Column(String)
    timeslot = Column(DateTime)
    players = relationship("Player", secondary="association", back_populates="games")

    def add_player(self, player, joined_at):
        self.player_game.append(
            Association(game=self, player=player, joined_at=joined_at)
        )

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
    def players_call(self) -> str:
        return ", ".join(player.mention for player in self.players_sorted)

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
