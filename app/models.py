from typing import Optional, List, Dict
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Integer, String, JSON, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.database import Base as SQLBase

# Enums
class Strategy(str, Enum):
    SUBMISSION = "V"
    COOPERATION = "C"
    WAR = "G"

# Modèles Pydantic (pour les requêtes/réponses)
class PlayerBase(BaseModel):
    name: str

class PlayerCreate(PlayerBase):
    pass

class Player(PlayerBase):
    id: int
    pfh: int = 100
    model_config = ConfigDict(from_attributes=True)

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class GameBase(BaseModel):
    player1_id: int
    player2_id: int

class GameCreate(GameBase):
    pass

class Game(GameBase):
    id: int
    current_turn: int = 1
    player1_pfh: int = 100
    player2_pfh: int = 100
    player1_consecutive_losses: int = 0
    player2_consecutive_losses: int = 0
    winner_id: Optional[int] = None
    is_completed: bool = False
    turns: List[Dict] = []
    model_config = ConfigDict(from_attributes=True)

class TurnAction(BaseModel):
    player_id: int
    strategy: Strategy
    sacrifice: bool = False

class TurnResult(BaseModel):
    turn_number: int
    player1_pfh: int
    player2_pfh: int
    player1_strategy: Strategy
    player2_strategy: Strategy
    player1_sacrifice: bool
    player2_sacrifice: bool
    player1_fadu: Optional[Dict] = None
    player2_fadu: Optional[Dict] = None
    player1_sacrifice_fadu: Optional[Dict] = None
    player2_sacrifice_fadu: Optional[Dict] = None

# Modèles SQLAlchemy
class DBGamePlayer(SQLBase):
    __tablename__ = "game_players"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"))
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    score: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    player: Mapped["DBPlayer"] = relationship(back_populates="game_participations")
    game: Mapped["DBGame"] = relationship(back_populates="participants")

class DBPlayer(SQLBase):
    __tablename__ = "players"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    pfh: Mapped[int] = mapped_column(Integer, default=100)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    user: Mapped["User"] = relationship(back_populates="players")
    games_as_player1: Mapped[List["DBGame"]] = relationship(
        back_populates="player1",
        foreign_keys="DBGame.player1_id"
    )
    games_as_player2: Mapped[List["DBGame"]] = relationship(
        back_populates="player2",
        foreign_keys="DBGame.player2_id"
    )
    game_participations: Mapped[List["DBGamePlayer"]] = relationship(
        back_populates="player"
    )

class DBGame(SQLBase):
    __tablename__ = "games"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player1_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    player2_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    current_turn: Mapped[int] = mapped_column(Integer, default=1)
    player1_pfh: Mapped[int] = mapped_column(Integer, default=100)
    player2_pfh: Mapped[int] = mapped_column(Integer, default=100)
    player1_consecutive_losses: Mapped[int] = mapped_column(Integer, default=0)
    player2_consecutive_losses: Mapped[int] = mapped_column(Integer, default=0)
    winner_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    turns: Mapped[List[Dict]] = mapped_column(JSON, default=[])
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    player1: Mapped["DBPlayer"] = relationship(
        back_populates="games_as_player1",
        foreign_keys=[player1_id]
    )
    player2: Mapped["DBPlayer"] = relationship(
        back_populates="games_as_player2",
        foreign_keys=[player2_id]
    )
    participants: Mapped[List["DBGamePlayer"]] = relationship(
        back_populates="game"
    )

class User(SQLBase):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    players: Mapped[List["DBPlayer"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )