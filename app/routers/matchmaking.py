# # routers/matchmaking.py
# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
# import uuid
# from typing import Dict, List
# from ..database import get_db
# from ..models import DBGame, DBPlayer, BaseModel,  Optional
# from ..schemas import MatchmakingResponse, MatchmakingRequest

# router = APIRouter()

# # File d'attente en mémoire (pourrait être remplacé par Redis en production)
# matchmaking_queue: List[str] = []

# class MatchmakingRequest(BaseModel):
#     user_id: str

# class MatchmakingResponse(BaseModel):
#     status: str
#     opponent: Optional[str] = None
#     game_id: Optional[str] = None

# @router.post(
#     "/matchmaking",
#     response_model=MatchmakingResponse,
#     summary="Join matchmaking queue"
# )
# async def join_matchmaking(
#     request: MatchmakingRequest,
#     db: Session = Depends(get_db)
# ):
#     """
#     Join the matchmaking queue to find an opponent.
#     Returns either:
#     - waiting_for_opponent status
#     - game details when match is found
#     """
#     try:
#         user_id = request.user_id
        
#         # Vérifier si le joueur existe
#         player = db.query(DBPlayer).filter(DBPlayer.id == user_id).first()
#         if not player:
#             raise HTTPException(status_code=404, detail="Player not found")
        
#         # Vérifier si déjà en file d'attente
#         if user_id in matchmaking_queue:
#             return {"status": "already_in_queue"}
        
#         # Ajouter à la file d'attente
#         matchmaking_queue.append(user_id)
        
#         # Vérifier s'il y a assez de joueurs
#         if len(matchmaking_queue) >= 2:
#             player1_id = matchmaking_queue.pop(0)
#             player2_id = matchmaking_queue.pop(0)
            
#             # Récupérer les noms des joueurs
#             player1 = db.query(DBPlayer).get(player1_id)
#             player2 = db.query(DBPlayer).get(player2_id)
            
#             # Créer une nouvelle partie
#             game_id = str(uuid.uuid4())
#             new_game = DBGame(
#                 id=game_id,
#                 status="waiting",
#                 player1_id=player1_id,
#                 player2_id=player2_id
#             )
#             db.add(new_game)
#             db.commit()
            
#             return {
#                 "status": "match_found",
#                 "opponent": player2.name,
#                 "game_id": game_id
#             }
        
#         return {"status": "waiting_for_opponent"}
        
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=str(e))



# routers/matchmaking.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
from typing import Dict, List
import asyncio
from threading import Lock
from ..database import get_db
from ..models import DBGame, DBPlayer
from ..schemas import MatchmakingResponse, MatchmakingRequest

router = APIRouter()

# File d'attente en mémoire avec protection thread-safe
matchmaking_queue: List[str] = []
queue_lock = Lock()

# Dictionnaire pour stocker les réponses en attente (pour gérer l'asynchrone)
pending_matches: Dict[str, Dict] = {}

@router.post(
    "/matchmaking",
    response_model=MatchmakingResponse,
    summary="Join matchmaking queue"
)
async def join_matchmaking(
    request: MatchmakingRequest,
    db: Session = Depends(get_db)
):
    """
    Join the matchmaking queue to find an opponent.
    Returns either:
    - waiting_for_opponent status
    - game details when match is found
    - already_in_queue if user is already waiting
    """
    try:
        user_id = request.user_id
        
        # Vérifier si le joueur existe
        player = db.query(DBPlayer).filter(DBPlayer.id == user_id).first()
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        with queue_lock:
            # Vérifier si déjà en file d'attente
            if user_id in matchmaking_queue:
                return MatchmakingResponse(status="already_in_queue")
            
            # Vérifier s'il y a déjà quelqu'un en attente
            if len(matchmaking_queue) >= 1:
                # Match trouvé !
                opponent_id = matchmaking_queue.pop(0)
                
                # Vérifier que l'adversaire existe toujours
                opponent = db.query(DBPlayer).filter(DBPlayer.id == opponent_id).first()
                if not opponent:
                    # Si l'adversaire n'existe plus, ajouter le joueur actuel à la file
                    matchmaking_queue.append(user_id)
                    return MatchmakingResponse(status="waiting_for_opponent")
                
                # Créer une nouvelle partie
                game_id = str(uuid.uuid4())
                new_game = DBGame(
                    id=game_id,
                    status="waiting",
                    player1_id=opponent_id,  # Le premier en file devient player1
                    player2_id=user_id       # Le nouveau joueur devient player2
                )
                db.add(new_game)
                db.commit()
                
                # Stocker les informations du match pour les deux joueurs
                match_info_player1 = {
                    "status": "match_found",
                    "opponent": player.name,
                    "game_id": game_id,
                    "player_position": 1
                }
                
                match_info_player2 = {
                    "status": "match_found", 
                    "opponent": opponent.name,
                    "game_id": game_id,
                    "player_position": 2
                }
                
                # Stocker pour récupération ultérieure du premier joueur
                pending_matches[opponent_id] = match_info_player1
                
                # Retourner directement au second joueur
                return MatchmakingResponse(
                    status="match_found",
                    opponent=opponent.name,
                    game_id=game_id
                )
            
            else:
                # Ajouter à la file d'attente
                matchmaking_queue.append(user_id)
                return MatchmakingResponse(status="waiting_for_opponent")
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Matchmaking error: {str(e)}")


@router.get(
    "/matchmaking/status/{user_id}",
    response_model=MatchmakingResponse,
    summary="Check matchmaking status"
)
async def check_matchmaking_status(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Check if a match has been found for a user in queue.
    Used for polling by the first player waiting.
    """
    try:
        # Vérifier s'il y a un match en attente
        if user_id in pending_matches:
            match_info = pending_matches.pop(user_id)
            return MatchmakingResponse(**match_info)
        
        with queue_lock:
            # Vérifier si toujours en file d'attente
            if user_id in matchmaking_queue:
                return MatchmakingResponse(status="waiting_for_opponent")
        
        # Pas en file d'attente
        return MatchmakingResponse(status="not_in_queue")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check error: {str(e)}")


@router.delete(
    "/matchmaking/{user_id}",
    summary="Leave matchmaking queue"
)
async def leave_matchmaking(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Remove user from matchmaking queue.
    """
    try:
        with queue_lock:
            if user_id in matchmaking_queue:
                matchmaking_queue.remove(user_id)
                return {"status": "removed_from_queue"}
            
        # Nettoyer les matches en attente aussi
        if user_id in pending_matches:
            pending_matches.pop(user_id)
            
        return {"status": "not_in_queue"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Leave queue error: {str(e)}")


@router.get(
    "/matchmaking/queue/info",
    summary="Get queue information (admin)"
)
async def get_queue_info():
    """
    Get current queue status for debugging/admin purposes.
    """
    with queue_lock:
        return {
            "queue_length": len(matchmaking_queue),
            "users_in_queue": matchmaking_queue.copy(),
            "pending_matches": len(pending_matches)
        }