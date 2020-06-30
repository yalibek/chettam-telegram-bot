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


# Class for user
class Player(Base):
    __tablename__ = "player"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True)
    username = Column(String, nullable=True)
    first_name = Column(String)
    last_name = Column(String, nullable=True)
    games = relationship("Game", secondary=association_table, back_populates="players")

    def __str__(self):
        if self.username:
            return f"{self.username}"
        elif self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        else:
            return f"{self.first_name}"

    @property
    def mention(self):
        if self.username:
            return f"@{self.username}"
        else:
            return f"[{self.first_name}](tg://user?id={self.user_id})"

    def create(self):
        session.add(self)
        session.commit()

    def delete(self):
        session.delete(self)
        session.commit()

    @staticmethod
    def save():
        session.commit()


# Class for unique game per chat
class Game(Base):
    __tablename__ = "game"
    id = Column(Integer, primary_key=True)
    updated_at = Column(DateTime)
    chat_id = Column(BigInteger)
    chat_type = Column(String)
    timeslot = Column(DateTime)
    players = relationship(
        "Player", secondary=association_table, back_populates="games"
    )

    @property
    def players_list(self):
        return [escape_markdown(str(player)) for player in self.players]

    @property
    def players_call(self):
        return ", ".join(player.mention for player in self.players)

    @property
    def slots(self):
        return len(self.players)

    @property
    def timeslot_cet(self):
        timeslot_utc = TIMEZONE_UTC.localize(self.timeslot)
        return timeslot_utc.astimezone(TIMEZONE_CET)

    @property
    def timeslot_cet_time(self):
        return self.timeslot_cet.strftime("%H:%M")

    def create(self):
        session.add(self)
        session.commit()

    def delete(self):
        session.delete(self)
        session.commit()

    @staticmethod
    def save():
        session.commit()


# Create tables in DB
Base.metadata.create_all(bind=engine)
