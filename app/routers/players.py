# from fastapi import APIRouter, Depends, HTTPException, Query, status
# from fastapi.security import HTTPBearer
# from sqlalchemy import select, func, case
# from sqlalchemy.orm import Session
# from typing import List, Optional, Annotated
# import logging
# import regex
# from datetime import datetime
# from pydantic import BaseModel, Field, validator

# from app.database import get_db
# from app.models import DBPlayer, DBGame
# from app.auth import get_current_admin_user

# router = APIRouter(
#     responses={404: {"description": "Not found"}}
# )

# security = HTTPBearer()
# logger = logging.getLogger(__name__)

# # ----- Schemas -----
# class PlayerBase(BaseModel):
#     name: str = Field(..., min_length=3, max_length=25, example="John Doe")

# class PlayerCreate(PlayerBase):
#     @validator('name')
#     def validate_name(cls, v):
#         v = v.strip().title()
#         if len(v) < 3:
#             raise ValueError("Name too short (min 3 characters)")
#         if not regex.match(r'^[\p{L}\s\-\.\']+$', v):
#             raise ValueError("Only letters, spaces, hyphens, dots and apostrophes allowed")
#         return v

# class PlayerResponse(PlayerBase):
#     id: int
#     created_at: datetime
#     is_active: bool
#     last_played: Optional[datetime] = Field(
#         None, description="Last game played timestamp"
#     )

#     class Config:
#         orm_mode = True
#         json_encoders = {
#             datetime: lambda v: v.isoformat()
#         }

# class PlayerStatsResponse(BaseModel):
#     player_id: int
#     games_played: int
#     wins: int
#     losses: int
#     win_rate: float
#     average_pfh: float
#     last_played: Optional[datetime]
#     average_score: Optional[float]

# class PlayerListResponse(BaseModel):
#     data: List[PlayerResponse]
#     pagination: dict

# class GamePlayersResponse(BaseModel):
#     player1: str
#     player2: str

# # ----- Helper Functions -----
# def validate_player_name(db: Session, name: str, exclude_id: int = None) -> str:
#     """Centralized player name validation"""
#     name = name.strip().title()
#     if len(name) < 3:
#         raise HTTPException(422, "Name too short (min 3 chars)")
#     if not regex.match(r'^[\p{L}\s\-\.\']+$', name):
#         raise HTTPException(422, "Invalid characters in name")
    
#     query = select(DBPlayer).where(DBPlayer.name == name)
#     if exclude_id:
#         query = query.where(DBPlayer.id != exclude_id)
    
#     if db.scalar(query):
#         raise HTTPException(409, "Name already exists")
    
#     return name

# # ----- API Endpoints -----
# @router.post(
#     "/",
#     response_model=PlayerResponse,
#     status_code=status.HTTP_201_CREATED,
#     dependencies=[Depends(get_current_admin_user)],
#     summary="Create a new player"
# )
# async def create_player(
#     player: PlayerCreate, 
#     db: Session = Depends(get_db)
# ):
#     """Create a new player account (admin only)"""
#     try:
#         validated_name = validate_player_name(db, player.name)
#         db_player = DBPlayer(name=validated_name)
#         db.add(db_player)
#         db.commit()
#         db.refresh(db_player)
#         logger.info(f"Player created: {db_player.id}")
#         return db_player
#     except HTTPException:
#         raise
#     except Exception as e:
#         db.rollback()
#         logger.error(f"Player creation failed: {str(e)}")
#         raise HTTPException(500, "Player creation failed")

# @router.get(
#     "/game/players",
#     response_model=GamePlayersResponse,
#     summary="Get players in a game"
# )
# async def get_game_players(
#     game_id: int = Query(..., description="ID of the game"),
#     db: Session = Depends(get_db)
# ):
#     """Get player names for a specific game"""
#     try:
#         game = db.get(DBGame, game_id)
#         if not game:
#             raise HTTPException(404, "Game not found")
        
#         players = db.scalars(
#             select(DBPlayer)
#             .join(DBGamePlayer)
#             .where(DBGamePlayer.game_id == game_id)
#             .order_by(DBGamePlayer.id)
#         ).all()
        
#         return {
#             "player1": players[0].name if len(players) > 0 else "Unknown",
#             "player2": players[1].name if len(players) > 1 else "Waiting..."
#         }
#     except Exception as e:
#         logger.error(f"Error getting game players: {str(e)}")
#         raise HTTPException(500, "Failed to retrieve game players")

# @router.get(
#     "/{player_id}/stats",
#     response_model=PlayerStatsResponse,
#     summary="Get player statistics"
# )
# async def get_player_stats(
#     player_id: int,
#     db: Session = Depends(get_db)
# ):
#     """Get detailed gameplay statistics for a player"""
#     try:
#         stats = db.execute(
#             select(
#                 func.count(DBGamePlayer.id).label("games_played"),
#                 func.sum(case((DBGame.winner_id == player_id, 1), else_=0)).label("wins"),
#                 func.max(DBGame.created_at).label("last_played"),
#                 func.avg(DBGamePlayer.score).label("average_score")
#             )
#             .select_from(DBGamePlayer)
#             .join(DBGame, DBGamePlayer.game_id == DBGame.id)
#             .where(DBGamePlayer.player_id == player_id)
#         ).first()

#         if not stats or stats.games_played == 0:
#             return PlayerStatsResponse(
#                 player_id=player_id,
#                 games_played=0,
#                 wins=0,
#                 losses=0,
#                 win_rate=0,
#                 average_pfh=0,
#                 last_played=None,
#                 average_score=None
#             )

#         return PlayerStatsResponse(
#             player_id=player_id,
#             games_played=stats.games_played,
#             wins=stats.wins,
#             losses=stats.games_played - stats.wins,
#             win_rate=(stats.wins / stats.games_played) * 100 if stats.games_played else 0,
#             average_pfh=0,
#             last_played=stats.last_played,
#             average_score=float(stats.average_score) if stats.average_score else None
#         )
#     except Exception as e:
#         logger.error(f"Stats error for player {player_id}: {str(e)}")
#         raise HTTPException(500, "Failed to calculate stats")

# @router.delete(
#     "/{player_id}",
#     status_code=status.HTTP_204_NO_CONTENT,
#     dependencies=[Depends(get_current_admin_user)],
#     summary="Delete a player"
# )
# async def delete_player(
#     player_id: int,
#     db: Session = Depends(get_db)
# ):
#     """Delete a player account (admin only)"""
#     try:
#         player = db.get(DBPlayer, player_id)
#         if not player:
#             raise HTTPException(404, "Player not found")
        
#         db.delete(player)
#         db.commit()
#         logger.warning(f"Player deleted: {player_id}")
#     except HTTPException:
#         raise
#     except Exception as e:
#         db.rollback()
#         logger.error(f"Player deletion failed: {str(e)}")
#         raise HTTPException(500, "Player deletion failed")    

# @router.get(
#     "/random",
#     response_model=PlayerResponse,
#     summary="Get a random player",
#     responses={
#         404: {"description": "No players available"},
#         500: {"description": "Internal server error"}
#     }
# )
# async def get_random_player(
#     db: Session = Depends(get_db),
#     exclude_current: Optional[int] = Query(
#         None, 
#         description="Player ID to exclude from selection"
#     )
# ):
#     """
#     Retrieve a random active player from the database.
#     Useful for matchmaking when finding random opponents.
#     """
#     try:
#         query = select(DBPlayer)
        
#         if exclude_current:
#             query = query.where(DBPlayer.id != exclude_current)
        
#         # Solution optimale pour différentes bases de données
#         if db.bind.dialect.name == 'postgresql':
#             random_player = db.scalar(query.order_by(func.random()).limit(1))
#         elif db.bind.dialect.name == 'sqlite':
#             random_player = db.scalar(query.order_by(func.random()).limit(1))
#         else:  # MySQL et autres
#             random_player = db.scalar(query.order_by(func.rand()).limit(1))
        
#         if not random_player:
#             logger.warning("No players available for random selection")
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="No active players available"
#             )
            
#         logger.debug(f"Selected random player: {random_player.id}")
#         return random_player
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Random player selection failed: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Failed to select random player"
#         )
#     # Ajouter un endpoint pour rechercher des joueurs
# @router.get(
#     "/search",
#     response_model=List[PlayerResponse],
#     summary="Search players by name"
# )
# async def search_players(
#     query: str = Query(..., min_length=2, description="Search term"),
#     limit: int = Query(10, ge=1, le=50),
#     db: Session = Depends(get_db)
# ):
#     """Fuzzy search for players by name"""
#     try:
#         return db.scalars(
#             select(DBPlayer)
#             .where(DBPlayer.name.ilike(f"%{query}%"))
#             .order_by(
#                 case(
#                     (DBPlayer.name.ilike(f"{query}%"), 0),  # Exact start first
#                     (DBPlayer.name.ilike(f"%{query}%"), 1)   # Then contains
#                 )
#             )
#             .limit(limit)
#         ).all()
#     except Exception as e:
#         logger.error(f"Search failed: {str(e)}")
#         raise HTTPException(500, "Search failed")
    


from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session
from typing import List, Optional, Annotated
import logging
import regex
from datetime import datetime
from pydantic import BaseModel, Field, validator

from app.database import get_db
from app.models import DBPlayer, DBGame, DBGamePlayer
from app.auth import get_current_admin_user

router = APIRouter(
    responses={404: {"description": "Not found"}}
)

security = HTTPBearer()
logger = logging.getLogger(__name__)

# ----- Schemas -----
class PlayerBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=25, example="John Doe")

class PlayerCreate(PlayerBase):
    @validator('name')
    def validate_name(cls, v):
        v = v.strip().title()
        if len(v) < 3:
            raise ValueError("Name too short (min 3 characters)")
        if not regex.match(r'^[\p{L}\s\-\.\']+$', v):
            raise ValueError("Only letters, spaces, hyphens, dots and apostrophes allowed")
        return v

class PlayerResponse(PlayerBase):
    id: int
    created_at: datetime
    is_active: bool
    last_played: Optional[datetime] = Field(
        None, description="Last game played timestamp"
    )

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PlayerStatsResponse(BaseModel):
    player_id: int
    games_played: int
    wins: int
    losses: int
    win_rate: float
    last_played: Optional[datetime]
    average_score: Optional[float]

class PlayerListResponse(BaseModel):
    data: List[PlayerResponse]
    pagination: dict

class GamePlayersResponse(BaseModel):
    player1: str
    player2: str

# ----- Helper Functions -----
def validate_player_name(db: Session, name: str, exclude_id: int = None) -> str:
    """Centralized player name validation"""
    name = name.strip().title()
    if len(name) < 3:
        raise HTTPException(422, "Name too short (min 3 chars)")
    if not regex.match(r'^[\p{L}\s\-\.\']+$', name):
        raise HTTPException(422, "Invalid characters in name")
    
    query = select(DBPlayer).where(DBPlayer.name == name)
    if exclude_id:
        query = query.where(DBPlayer.id != exclude_id)
    
    if db.scalar(query):
        raise HTTPException(409, "Name already exists")
    
    return name

def check_player_exists(db: Session, player_id: int) -> DBPlayer:
    """Check if player exists and return it"""
    player = db.get(DBPlayer, player_id)
    if not player:
        raise HTTPException(404, "Player not found")
    return player

# ----- API Endpoints -----
@router.post(
    "/",
    response_model=PlayerResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_admin_user)],
    summary="Create a new player"
)
async def create_player(
    player: PlayerCreate, 
    db: Session = Depends(get_db)
):
    """Create a new player account (admin only)"""
    try:
        validated_name = validate_player_name(db, player.name)
        db_player = DBPlayer(name=validated_name)
        db.add(db_player)
        db.commit()
        db.refresh(db_player)
        logger.info(f"Player created: {db_player.id}")
        return db_player
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Player creation failed: {str(e)}")
        raise HTTPException(500, "Player creation failed")

@router.get(
    "/game/{game_id}/players",
    response_model=GamePlayersResponse,
    summary="Get players in a game"
)
async def get_game_players(
    game_id: int,
    db: Session = Depends(get_db)
):
    """Get player names for a specific game"""
    try:
        game = db.get(DBGame, game_id)
        if not game:
            raise HTTPException(404, "Game not found")
        
        players_query = db.scalars(
            select(DBPlayer)
            .join(DBGamePlayer)
            .where(DBGamePlayer.game_id == game_id)
            .order_by(DBGamePlayer.id)
        )
        
        players_list = list(players_query.all()) if players_query else []
        
        return GamePlayersResponse(
            player1=players_list[0].name if len(players_list) > 0 else "Unknown",
            player2=players_list[1].name if len(players_list) > 1 else "Waiting..."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting game players: {str(e)}")
        raise HTTPException(500, "Failed to retrieve game players")

@router.get(
    "/{player_id}/stats",
    response_model=PlayerStatsResponse,
    summary="Get player statistics"
)
async def get_player_stats(
    player_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed gameplay statistics for a player"""
    try:
        # Vérifier que le joueur existe
        check_player_exists(db, player_id)
        
        stats = db.execute(
            select(
                func.count(DBGamePlayer.id).label("games_played"),
                func.sum(case((DBGame.winner_id == player_id, 1), else_=0)).label("wins"),
                func.max(DBGame.created_at).label("last_played"),
                func.avg(DBGamePlayer.score).label("average_score")
            )
            .select_from(DBGamePlayer)
            .join(DBGame, DBGamePlayer.game_id == DBGame.id)
            .where(DBGamePlayer.player_id == player_id)
        ).first()

        if not stats or stats.games_played == 0:
            return PlayerStatsResponse(
                player_id=player_id,
                games_played=0,
                wins=0,
                losses=0,
                win_rate=0.0,
                last_played=None,
                average_score=None
            )

        wins = stats.wins or 0
        games_played = stats.games_played or 0
        losses = games_played - wins
        win_rate = (wins / games_played) * 100 if games_played > 0 else 0.0

        return PlayerStatsResponse(
            player_id=player_id,
            games_played=games_played,
            wins=wins,
            losses=losses,
            win_rate=round(win_rate, 2),
            last_played=stats.last_played,
            average_score=round(float(stats.average_score), 2) if stats.average_score else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stats error for player {player_id}: {str(e)}")
        raise HTTPException(500, "Failed to calculate stats")

@router.delete(
    "/{player_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin_user)],
    summary="Delete a player"
)
async def delete_player(
    player_id: int,
    db: Session = Depends(get_db)
):
    """Delete a player account (admin only)"""
    try:
        player = db.get(DBPlayer, player_id)
        if not player:
            raise HTTPException(404, "Player not found")
        
        db.delete(player)
        db.commit()
        logger.warning(f"Player deleted: {player_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Player deletion failed: {str(e)}")
        raise HTTPException(500, "Player deletion failed")    

@router.get(
    "/random",
    response_model=PlayerResponse,
    summary="Get a random player",
    responses={
        404: {"description": "No players available"},
        500: {"description": "Internal server error"}
    }
)
async def get_random_player(
    db: Session = Depends(get_db),
    exclude_current: Optional[int] = Query(
        None, 
        description="Player ID to exclude from selection"
    )
):
    """
    Retrieve a random active player from the database.
    Useful for matchmaking when finding random opponents.
    """
    try:
        query = select(DBPlayer).where(DBPlayer.is_active == True)
        
        if exclude_current:
            query = query.where(DBPlayer.id != exclude_current)
        
        # Solution optimale pour différentes bases de données
        if db.bind.dialect.name == 'postgresql':
            random_player = db.scalar(query.order_by(func.random()).limit(1))
        elif db.bind.dialect.name == 'sqlite':
            random_player = db.scalar(query.order_by(func.random()).limit(1))
        else:  # MySQL et autres
            random_player = db.scalar(query.order_by(func.rand()).limit(1))
        
        if not random_player:
            logger.warning("No players available for random selection")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active players available"
            )
            
        logger.debug(f"Selected random player: {random_player.id}")
        return random_player
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Random player selection failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to select random player"
        )

@router.get(
    "/search",
    response_model=List[PlayerResponse],
    summary="Search players by name"
)
async def search_players(
    query: str = Query(..., min_length=2, description="Search term"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
    db: Session = Depends(get_db)
):
    """Fuzzy search for players by name"""
    try:
        search_term = query.strip()
        if len(search_term) < 2:
            raise HTTPException(400, "Search term must be at least 2 characters")
            
        players = db.scalars(
            select(DBPlayer)
            .where(
                DBPlayer.name.ilike(f"%{search_term}%"),
                DBPlayer.is_active == True
            )
            .order_by(
                case(
                    (DBPlayer.name.ilike(f"{search_term}%"), 0),  # Exact start first
                    (DBPlayer.name.ilike(f"%{search_term}%"), 1)   # Then contains
                ),
                DBPlayer.name
            )
            .limit(limit)
        ).all()
        
        logger.debug(f"Found {len(players)} players for search '{search_term}'")
        return players
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed for query '{query}': {str(e)}")
        raise HTTPException(500, "Search failed")

@router.get(
    "/",
    response_model=PlayerListResponse,
    summary="List all players with pagination"
)
async def list_players(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    active_only: bool = Query(True, description="Show only active players"),
    db: Session = Depends(get_db)
):
    """List players with pagination support"""
    try:
        offset = (page - 1) * limit
        
        query = select(DBPlayer)
        if active_only:
            query = query.where(DBPlayer.is_active == True)
        
        # Get total count
        total_query = select(func.count(DBPlayer.id))
        if active_only:
            total_query = total_query.where(DBPlayer.is_active == True)
        total = db.scalar(total_query)
        
        # Get players for current page
        players = db.scalars(
            query.order_by(DBPlayer.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        
        total_pages = (total + limit - 1) // limit  # Ceiling division
        
        return PlayerListResponse(
            data=players,
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to list players: {str(e)}")
        raise HTTPException(500, "Failed to retrieve players")

@router.get(
    "/{player_id}",
    response_model=PlayerResponse,
    summary="Get player by ID"
)
async def get_player(
    player_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific player by ID"""
    try:
        player = check_player_exists(db, player_id)
        return player
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get player {player_id}: {str(e)}")
        raise HTTPException(500, "Failed to retrieve player")