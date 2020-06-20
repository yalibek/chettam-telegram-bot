from sqlalchemy import Column, Integer, BigInteger, String, ForeignKey, DateTime
from sqlalchemy import create_engine, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

from vars import DB_URL, TIMEZONE_CET, TIMEZONE_UTC

# DB stuff
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
    def sanitized_name(self):
        return (
            str(self)
            .replace("\\", "\\\\")
            .replace("`", "\`")
            .replace("*", "\*")
            .replace("_", "\_")
            .replace("{", "\{")
            .replace("}", "\}")
            .replace("[", "\[")
            .replace("]", "\]")
            .replace("(", "\(")
            .replace(")", "\)")
            .replace("#", "\#")
            .replace("+", "\+")
            .replace("-", "\-")
            .replace(".", "\.")
            .replace("!", "\!")
            .replace("&", "\&")
            .replace(">", "\>")
            .replace("<", "\<")
        )

    @property
    def callme(self):
        if self.username:
            return f"@{self.username}"
        else:
            return self.first_name

    def create(self):
        session.add(self)

    def delete(self):
        session.delete(self)

    @staticmethod
    def save():
        session.commit()


class Game(Base):
    __tablename__ = "game"
    id = Column(Integer, primary_key=True)
    updated_at = Column(DateTime)
    chat_id = Column(BigInteger, unique=True)
    chat_type = Column(String)
    timeslot = Column(DateTime)
    players = relationship(
        "Player", secondary=association_table, back_populates="games"
    )

    @property
    def players_list(self):
        return [player.sanitized_name for player in self.players]

    @property
    def players_call(self):
        return [player.callme for player in self.players]

    @property
    def slots(self):
        return len(self.players)

    @property
    def timeslot_cet(self):
        timeslot_utc = TIMEZONE_UTC.localize(self.timeslot)
        return timeslot_utc.astimezone(TIMEZONE_CET)

    def create(self):
        session.add(self)

    def delete(self):
        session.delete(self)

    @staticmethod
    def save():
        session.commit()


# Create tables in DB
Base.metadata.create_all(bind=engine)
