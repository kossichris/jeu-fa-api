from pydantic import BaseModel, EmailStr, Field
from typing import Union, Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class GameMode(str, Enum):
    """Modes de jeu disponibles"""
    QUICK = "quick"
    PRIVATE = "private" 
    AI = "ai"

class GamePhase(str, Enum):
    """Phases de jeu"""
    DRAW = "draw"
    STRATEGY = "strategy"
    SACRIFICE = "sacrifice"
    BATTLE = "battle"
    RESULTS = "results"

class Strategy(str, Enum):
    """Stratégies disponibles"""
    VIOLENCE = "V"
    COMMERCE = "C"
    GUERRE = "G"

class FaduResponse(BaseModel):
    """Réponse standard de l'API Fadu"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {},
                "message": "Opération réussie"
            }
        }

# Schémas d'authentification
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user_id: int
    username: str

class TokenData(BaseModel):
    email: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# Schémas utilisateur
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Schémas de matchmaking
class MatchmakingRequest(BaseModel):
    user_id: str

class MatchmakingResponse(BaseModel):
    status: str
    opponent: Optional[str] = None
    game_id: Optional[str] = None

# Schémas de jeu
class GameCreateRequest(BaseModel):
    """Requête de création de partie"""
    mode: GameMode = Field(..., description="Mode de jeu")
    room_code: Optional[str] = Field(None, min_length=4, max_length=10, description="Code de salon pour mode privé")
    
    class Config:
        json_schema_extra = {
            "example": {
                "mode": "quick",
                "room_code": None
            }
        }

class CardInfo(BaseModel):
    """Informations d'une carte"""
    name: str
    pfh: int
    description: Optional[str] = None
    type: Optional[str] = None

class DrawCardResponse(BaseModel):
    """Réponse lors du tirage d'une carte"""
    success: bool
    card: CardInfo
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "card": {
                    "name": "Épée de feu",
                    "pfh": 15,
                    "description": "Une épée enflammée",
                    "type": "standard"
                },
                "message": "Carte tirée avec succès"
            }
        }

class StrategyChoice(BaseModel):
    """Choix de stratégie"""
    strategy: Strategy = Field(..., description="Stratégie choisie")
    
    class Config:
        json_schema_extra = {
            "example": {
                "strategy": "V"
            }
        }

class SacrificeDecision(BaseModel):
    """Décision de sacrifice"""
    sacrifice: bool = Field(..., description="Décision de sacrifier ou non")
    
    class Config:
        json_schema_extra = {
            "example": {
                "sacrifice": True
            }
        }

class PlayerInfo(BaseModel):
    """Informations d'un joueur dans une partie"""
    id: int
    username: str
    current_pfh: int
    has_card: bool = False
    has_strategy: bool = False
    sacrifice_decided: bool = False

class GameState(BaseModel):
    """État complet d'une partie"""
    game_id: int
    current_phase: GamePhase
    current_player: str
    current_turn: int
    max_turns: int
    is_completed: bool
    winner: Optional[str] = None
    mode: GameMode
    room_code: Optional[str] = None
    is_my_turn: bool
    my_player_type: str
    can_transition: bool
    player1: PlayerInfo
    player2: Optional[PlayerInfo] = None
    
    # Informations privées du joueur courant
    my_card: Optional[CardInfo] = None
    my_sacrifice_card: Optional[CardInfo] = None
    my_strategy: Optional[Strategy] = None
    my_sacrifice_decision: Optional[bool] = None

class PhaseTransition(BaseModel):
    """Transition de phase"""
    new_phase: GamePhase
    current_player: str
    current_turn: int
    is_completed: bool = False
    winner: Optional[str] = None

class TurnResultInfo(BaseModel):
    """Résultat d'un tour"""
    turn_number: int
    player1_card: str
    player1_strategy: Strategy
    player1_sacrifice: bool
    player1_gains: int
    player1_final_pfh: int
    player2_card: str
    player2_strategy: Strategy
    player2_sacrifice: bool
    player2_gains: int
    player2_final_pfh: int

class GameHistoryResponse(BaseModel):
    """Historique d'une partie"""
    success: bool
    data: Dict[str, Any]
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "game_id": 1,
                    "turns": [],
                    "final_result": {
                        "winner": "player1",
                        "final_scores": {
                            "player1": 100,
                            "player2": 85
                        }
                    }
                },
                "message": "Historique récupéré"
            }
        }

# Schémas d'erreur
class ErrorDetail(BaseModel):
    """Détail d'une erreur"""
    field: Optional[str] = None
    message: str
    code: Optional[str] = None

class ErrorResponse(BaseModel):
    """Réponse d'erreur"""
    success: bool = False
    error: str
    details: Optional[List[ErrorDetail]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "Validation failed",
                "details": [
                    {
                        "field": "mode",
                        "message": "Mode de jeu invalide",
                        "code": "invalid_value"
                    }
                ]
            }
        }