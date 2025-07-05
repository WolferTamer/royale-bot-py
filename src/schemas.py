from typing import List
from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base (DeclarativeBase):
    pass

class User (Base):
    __tablename__ = "user"

    userid: Mapped[int] = mapped_column(BigInteger,primary_key=True)
    wins: Mapped[int] = mapped_column(default=0)
    gamesplayed: Mapped[int] = mapped_column(default=0)

    games: Mapped[List["Game"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"User(userid={self.userid})"
    
class Game (Base):
    __tablename__ = "game"

    gameid: Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))
    teamtype: Mapped[str] = mapped_column(String(10))
    teamcount: Mapped[int] = mapped_column(default=12)
    autoprogress: Mapped[bool] = mapped_column(default=False)
    progresscooldown: Mapped[int] = mapped_column(default=2000,nullable=True)
    turnCount: Mapped[int] = mapped_column(default=0)
    channel: Mapped[str] = mapped_column(String(18), nullable=True)

    contestants: Mapped[List["Contestant"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan"
    )

    user: Mapped["User"] = relationship(back_populates="games")
    userid: Mapped[int] = mapped_column(BigInteger,ForeignKey("user.userid"))

    def __repr__(self) -> str:
        return f"Game(id={self.gameid}, name={self.name}, teamtype={self.teamtype})"

class Contestant(Base):
    __tablename__ = "contestant"

    name: Mapped[str] = mapped_column(String(50), primary_key=True)
    gameid: Mapped[int] = mapped_column(ForeignKey("game.gameid"), primary_key=True)
    picture: Mapped[str] = mapped_column(String(250))
    userref: Mapped[str] = mapped_column(BigInteger, nullable=True)
    dead: Mapped[bool] = mapped_column(default=False)
    team: Mapped[int] = mapped_column(default=1)

    game: Mapped["Game"] = relationship(back_populates="contestants")

    def __repr__(self) -> str:
        return f"Contestant(name={self.name!r}, game={self.gameid!r}, picture={self.picture!r})"
