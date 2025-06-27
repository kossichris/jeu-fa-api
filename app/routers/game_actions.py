# from fastapi import APIRouter, HTTPException, Depends, status
# from sqlalchemy.orm import Session
# from typing import Dict, Any, Optional
# import logging

# from app.dependencies import get_current_user
# from app.models import User, DBGame, DBPlayer, TurnAction, TurnResult
# from app.database import get_db
# from app.game_logic import fadu_logic, strategy_logic
# from app.schemas import (
#     FaduResponse,
#     GameCreateRequest,
#     DrawCardResponse,
#     StrategyChoice,
#     SacrificeDecision,
#     PhaseTransition
# )
# from app.config import settings

# router = APIRouter()
# logger = logging.getLogger(__name__)

# # Constants
# MIN_PFH_FOR_SACRIFICE = settings.SACRIFICE_COST
# MAX_TURNS = settings.MAX_GAME_TURNS

# @router.post("/create", response_model=FaduResponse)
# async def create_new_game(
#     request: GameCreateRequest,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Crée une nouvelle partie"""
#     try:
#         # Vérification si l'utilisateur a déjà une partie en cours
#         existing_game = db.query(DBGame).filter(
#             (DBGame.player1_id == current_user.id) | (DBGame.player2_id == current_user.id),
#             DBGame.is_completed == False
#         ).first()
        
#         if existing_game:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Vous avez déjà une partie en cours"
#             )
        
#         # Création de la nouvelle partie
#         new_game = DBGame(
#             player1_id=current_user.id,
#             mode=request.mode,
#             room_code=request.room_code if request.mode == "private" else None,
#             current_turn=1,
#             max_turns=MAX_TURNS,
#             current_phase="draw",
#             current_player="player1"
#         )
        
#         db.add(new_game)
#         db.commit()
#         db.refresh(new_game)
        
#         return FaduResponse(
#             success=True,
#             data={
#                 "game_id": new_game.id,
#                 "mode": new_game.mode,
#                 "room_code": new_game.room_code
#             },
#             message="Nouvelle partie créée avec succès"
#         )
#     except HTTPException:
#         raise
#     except Exception as e:
#         db.rollback()
#         logger.exception("Erreur création de partie")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Erreur lors de la création de la partie"
#         )

# @router.post("/{game_id}/cards/draw", response_model=DrawCardResponse)
# async def draw_standard_card(
#     game_id: int,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Tire une carte standard pour le joueur courant"""
#     return await draw_card(game_id, False, current_user, db)

# @router.post("/{game_id}/cards/sacrifice", response_model=DrawCardResponse)
# async def draw_sacrifice_card(
#     game_id: int,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Tire une carte de sacrifice pour le joueur courant"""
#     return await draw_card(game_id, True, current_user, db)

# async def draw_card(
#     game_id: int,
#     is_sacrifice: bool,
#     current_user: User,
#     db: Session
# ):
#     """Fonction helper pour tirer une carte"""
#     try:
#         game = db.query(DBGame).filter(DBGame.id == game_id).first()
#         if not game:
#             raise HTTPException(status_code=404, detail="Partie non trouvée")
        
#         # Vérification que c'est bien le tour de l'utilisateur
#         player_type = "player1" if game.player1_id == current_user.id else "player2"
#         if game.current_player != player_type:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Ce n'est pas votre tour de jouer"
#             )
        
#         # Vérification de la phase
#         if game.current_phase != "draw":
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Vous ne pouvez pas tirer de carte dans cette phase"
#             )
        
#         # Tirage de la carte
#         card_type = "sacrifice" if is_sacrifice else "standard"
#         card = fadu_logic.draw_card(card_type)
        
#         if not card:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Aucune carte disponible"
#             )
        
#         # Enregistrement de la carte tirée
#         if player_type == "player1":
#             game.player1_card = card['name']
#             game.player1_card_pfh = card['pfh']
#             if is_sacrifice:
#                 game.player1_sacrifice_card = card['name']
#                 game.player1_sacrifice_card_pfh = card['pfh']
#         else:
#             game.player2_card = card['name']
#             game.player2_card_pfh = card['pfh']
#             if is_sacrifice:
#                 game.player2_sacrifice_card = card['name']
#                 game.player2_sacrifice_card_pfh = card['pfh']
        
#         db.commit()
        
#         return DrawCardResponse(
#             success=True,
#             card=card,
#             message=f"Carte {card_type} tirée avec succès"
#         )
#     except HTTPException:
#         raise
#     except Exception as e:
#         db.rollback()
#         logger.exception("Erreur tirage de carte")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Erreur lors du tirage de carte"
#         )

# @router.post("/{game_id}/strategy", response_model=FaduResponse)
# async def choose_strategy(
#     game_id: int,
#     strategy_data: StrategyChoice,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Enregistre la stratégie choisie par le joueur"""
#     try:
#         game = db.query(DBGame).filter(DBGame.id == game_id).first()
#         if not game:
#             raise HTTPException(status_code=404, detail="Partie non trouvée")
        
#         # Vérification que c'est bien le tour de l'utilisateur
#         player_type = "player1" if game.player1_id == current_user.id else "player2"
#         if game.current_player != player_type:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Ce n'est pas votre tour de jouer"
#             )
        
#         # Vérification de la phase
#         if game.current_phase != "strategy":
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Vous ne pouvez pas choisir de stratégie dans cette phase"
#             )
        
#         # Validation de la stratégie
#         if strategy_data.strategy not in strategy_logic.VALID_STRATEGIES:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=f"Stratégie invalide. Options: {strategy_logic.VALID_STRATEGIES}"
#             )
        
#         # Enregistrement de la stratégie
#         if player_type == "player1":
#             game.player1_strategy = strategy_data.strategy
#         else:
#             game.player2_strategy = strategy_data.strategy
        
#         db.commit()
        
#         return FaduResponse(
#             success=True,
#             data={"strategy": strategy_data.strategy},
#             message="Stratégie enregistrée avec succès"
#         )
#     except HTTPException:
#         raise
#     except Exception as e:
#         db.rollback()
#         logger.exception("Erreur enregistrement stratégie")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Erreur lors de l'enregistrement de la stratégie"
#         )

# @router.post("/{game_id}/sacrifice", response_model=FaduResponse)
# async def decide_sacrifice(
#     game_id: int,
#     decision: SacrificeDecision,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Gère la décision de sacrifice du joueur"""
#     try:
#         game = db.query(DBGame).filter(DBGame.id == game_id).first()
#         if not game:
#             raise HTTPException(status_code=404, detail="Partie non trouvée")
        
#         # Vérification que c'est bien le tour de l'utilisateur
#         player_type = "player1" if game.player1_id == current_user.id else "player2"
#         if game.current_player != player_type:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Ce n'est pas votre tour de jouer"
#             )
        
#         # Vérification de la phase
#         if game.current_phase != "sacrifice":
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Vous ne pouvez pas sacrifier dans cette phase"
#             )
        
#         # Vérification du PFH pour le sacrifice
#         player = db.query(DBPlayer).filter(
#             DBPlayer.id == (game.player1_id if player_type == "player1" else game.player2_id)
#         ).first()
        
#         if decision.sacrifice and player.current_pfh < MIN_PFH_FOR_SACRIFICE:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=f"PFH insuffisant pour sacrifier (minimum {MIN_PFH_FOR_SACRIFICE} requis)"
#             )
        
#         # Enregistrement de la décision
#         if player_type == "player1":
#             game.player1_sacrifice = decision.sacrifice
#             if decision.sacrifice:
#                 player.current_pfh -= MIN_PFH_FOR_SACRIFICE
#         else:
#             game.player2_sacrifice = decision.sacrifice
#             if decision.sacrifice:
#                 player.current_pfh -= MIN_PFH_FOR_SACRIFICE
        
#         db.commit()
        
#         return FaduResponse(
#             success=True,
#             data={"sacrifice": decision.sacrifice},
#             message="Décision de sacrifice enregistrée"
#         )
#     except HTTPException:
#         raise
#     except Exception as e:
#         db.rollback()
#         logger.exception("Erreur décision de sacrifice")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Erreur lors de l'enregistrement de la décision de sacrifice"
#         )

# @router.post("/{game_id}/next-phase", response_model=FaduResponse)
# async def next_phase(
#     game_id: int,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Passe à la phase suivante du jeu"""
#     try:
#         game = db.query(DBGame).filter(DBGame.id == game_id).first()
#         if not game:
#             raise HTTPException(status_code=404, detail="Partie non trouvée")
        
#         # Vérification que l'utilisateur fait partie de la partie
#         if current_user.id not in [game.player1_id, game.player2_id]:
#             raise HTTPException(status_code=403, detail="Vous ne faites pas partie de cette partie")
        
#         # Transition de phase
#         new_phase = game.current_phase
#         new_player = game.current_player
        
#         if game.current_phase == "draw":
#             # On passe à la stratégie si les deux joueurs ont tiré leur carte
#             if game.player1_card and game.player2_card:
#                 new_phase = "strategy"
#                 new_player = "player1"
#             else:
#                 # On alterne entre les joueurs pour le tirage
#                 new_player = "player2" if game.current_player == "player1" else "player1"
                
#         elif game.current_phase == "strategy":
#             # On passe au sacrifice si les deux joueurs ont choisi leur stratégie
#             if game.player1_strategy and game.player2_strategy:
#                 new_phase = "sacrifice"
#                 new_player = "player1"
#             else:
#                 # On alterne entre les joueurs pour la stratégie
#                 new_player = "player2" if game.current_player == "player1" else "player1"
                
#         elif game.current_phase == "sacrifice":
#             # On passe aux résultats si les deux joueurs ont décidé
#             if game.player1_sacrifice is not None and game.player2_sacrifice is not None:
#                 new_phase = "battle"
#                 # Calcul des résultats
#                 result = strategy_logic.calculate_turn_results(game)
                
#                 # Mise à jour des PFH
#                 player1 = db.query(DBPlayer).filter(DBPlayer.id == game.player1_id).first()
#                 player2 = db.query(DBPlayer).filter(DBPlayer.id == game.player2_id).first()
                
#                 player1.current_pfh += result.player1_gains
#                 player2.current_pfh += result.player2_gains
                
#                 # Enregistrement du tour dans l'historique
#                 turn_result = TurnResult(
#                     game_id=game.id,
#                     turn_number=game.current_turn,
#                     player1_card=game.player1_card,
#                     player1_strategy=game.player1_strategy,
#                     player1_sacrifice=game.player1_sacrifice,
#                     player1_gains=result.player1_gains,
#                     player1_final_pfh=player1.current_pfh,
#                     player2_card=game.player2_card,
#                     player2_strategy=game.player2_strategy,
#                     player2_sacrifice=game.player2_sacrifice,
#                     player2_gains=result.player2_gains,
#                     player2_final_pfh=player2.current_pfh
#                 )
#                 db.add(turn_result)
                
#                 new_phase = "results"
#             else:
#                 # On alterne entre les joueurs pour le sacrifice
#                 new_player = "player2" if game.current_player == "player1" else "player1"
                
#         elif game.current_phase == "results":
#             # Préparation du tour suivant ou fin de partie
#             if game.current_turn < game.max_turns and not game.is_completed:
#                 new_phase = "draw"
#                 new_player = "player1"
#                 game.current_turn += 1
                
#                 # Réinitialisation des cartes et stratégies
#                 game.player1_card = None
#                 game.player1_card_pfh = None
#                 game.player2_card = None
#                 game.player2_card_pfh = None
#                 game.player1_strategy = None
#                 game.player2_strategy = None
#                 game.player1_sacrifice = None
#                 game.player2_sacrifice = None
#                 game.player1_sacrifice_card = None
#                 game.player1_sacrifice_card_pfh = None
#                 game.player2_sacrifice_card = None
#                 game.player2_sacrifice_card_pfh = None
#             else:
#                 # Fin de la partie
#                 game.is_completed = True
#                 if player1.current_pfh > player2.current_pfh:
#                     game.winner = "player1"
#                 elif player2.current_pfh > player1.current_pfh:
#                     game.winner = "player2"
#                 else:
#                     game.winner = "draw"
        
#         # Mise à jour de la partie
#         game.current_phase = new_phase
#         game.current_player = new_player
#         db.commit()
        
#         return FaduResponse(
#             success=True,
#             data={
#                 "new_phase": new_phase,
#                 "current_player": new_player,
#                 "current_turn": game.current_turn,
#                 "is_completed": game.is_completed,
#                 "winner": game.winner if game.is_completed else None
#             },
#             message="Phase mise à jour avec succès"
#         )
#     except HTTPException:
#         raise
#     except Exception as e:
#         db.rollback()
#         logger.exception("Erreur changement de phase")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Erreur lors du changement de phase"
#         )                                            


from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import logging

from app.dependencies import get_current_user
from app.models import User, DBGame, DBPlayer, TurnAction, TurnResult
from app.database import get_db
from app.game_logic.fadu_logic import FaduService
fadu_service = FaduService()
from app.schemas import (
    FaduResponse,
    GameCreateRequest,
    DrawCardResponse,
    StrategyChoice,
    SacrificeDecision,
    PhaseTransition
)
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Constants
MIN_PFH_FOR_SACRIFICE = settings.SACRIFICE_COST
MAX_TURNS = settings.MAX_GAME_TURNS

# Helper functions
def get_player_type(game: DBGame, user: User) -> Optional[str]:
    """Détermine le type de joueur (player1/player2) ou None si non participant"""
    if game.player1_id == user.id:
        return "player1"
    elif game.player2_id == user.id:
        return "player2"
    return None

def verify_game_status(game: DBGame, current_user: User) -> str:
    """Vérifie que la partie est dans un état valide et retourne le type de joueur"""
    if not game:
        raise HTTPException(404, "Partie non trouvée")
    
    if game.is_completed:
        raise HTTPException(400, "Cette partie est terminée")
    
    player_type = get_player_type(game, current_user)
    if not player_type:
        raise HTTPException(403, "Vous ne participez pas à cette partie")
    
    # Vérifier si on attend un joueur 2 (sauf en mode IA)
    if not game.player2_id and game.mode != "ai":
        raise HTTPException(400, "En attente du joueur 2")
    
    return player_type

def can_transition_to_next_phase(game: DBGame, current_phase: str) -> bool:
    """Vérifie si on peut passer à la phase suivante"""
    if current_phase == "draw":
        return bool(game.player1_card and game.player2_card)
    elif current_phase == "strategy":
        return bool(game.player1_strategy and game.player2_strategy)
    elif current_phase == "sacrifice":
        return (game.player1_sacrifice is not None and 
                game.player2_sacrifice is not None)
    return False

def get_game_state(game: DBGame, db: Session, current_user: User) -> Dict:
    """Retourne l'état complet du jeu pour le joueur courant"""
    player1 = db.query(DBPlayer).filter(DBPlayer.id == game.player1_id).first()
    player2 = db.query(DBPlayer).filter(DBPlayer.id == game.player2_id).first() if game.player2_id else None
    current_player_type = get_player_type(game, current_user)
    
    # Informations de base toujours visibles
    game_state = {
        "game_id": game.id,  # S'assurer que l'ID est toujours présent
        "current_phase": game.current_phase,
        "current_player": game.current_player,
        "current_turn": game.current_turn,
        "max_turns": game.max_turns,
        "is_completed": game.is_completed,
        "winner": game.winner,
        "mode": game.mode,
        "room_code": game.room_code,
        "is_my_turn": game.current_player == current_player_type,
        "my_player_type": current_player_type,  # Utile pour le client
        "can_transition": can_transition_to_next_phase(game, game.current_phase),
        "player1": {
            "id": player1.id,
            "username": player1.username,
            "current_pfh": player1.current_pfh,
            "has_card": bool(game.player1_card),
            "has_strategy": bool(game.player1_strategy),
            "sacrifice_decided": game.player1_sacrifice is not None
        },
        "player2": {
            "id": player2.id if player2 else None,
            "username": player2.username if player2 else None,
            "current_pfh": player2.current_pfh if player2 else None,
            "has_card": bool(game.player2_card),
            "has_strategy": bool(game.player2_strategy),
            "sacrifice_decided": game.player2_sacrifice is not None
        } if player2 else None
    }
    
    # Informations privées pour le joueur courant
    if current_player_type == "player1":
        if game.player1_card:
            game_state["my_card"] = {
                "name": game.player1_card,
                "pfh": game.player1_card_pfh
            }
        if game.player1_sacrifice_card:
            game_state["my_sacrifice_card"] = {
                "name": game.player1_sacrifice_card,
                "pfh": game.player1_sacrifice_card_pfh
            }
        game_state["my_strategy"] = game.player1_strategy
        game_state["my_sacrifice_decision"] = game.player1_sacrifice
    elif current_player_type == "player2":
        if game.player2_card:
            game_state["my_card"] = {
                "name": game.player2_card,
                "pfh": game.player2_card_pfh
            }
        if game.player2_sacrifice_card:
            game_state["my_sacrifice_card"] = {
                "name": game.player2_sacrifice_card,
                "pfh": game.player2_sacrifice_card_pfh
            }
        game_state["my_strategy"] = game.player2_strategy
        game_state["my_sacrifice_decision"] = game.player2_sacrifice
    
    return game_state

def reset_turn_data(game: DBGame):
    """Remet à zéro les données du tour précédent"""
    game.player1_card = None
    game.player1_card_pfh = None
    game.player2_card = None
    game.player2_card_pfh = None
    game.player1_strategy = None
    game.player2_strategy = None
    game.player1_sacrifice = None
    game.player2_sacrifice = None
    game.player1_sacrifice_card = None
    game.player1_sacrifice_card_pfh = None
    game.player2_sacrifice_card = None
    game.player2_sacrifice_card_pfh = None

# API Endpoints
@router.post("/create", response_model=FaduResponse)
async def create_new_game(
    request: GameCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crée une nouvelle partie"""
    try:
        # Vérification si l'utilisateur a déjà une partie en cours
        existing_game = db.query(DBGame).filter(
            (DBGame.player1_id == current_user.id) | (DBGame.player2_id == current_user.id),
            DBGame.is_completed == False
        ).first()
        
        if existing_game:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vous avez déjà une partie en cours"
            )
        
        # Création de la nouvelle partie
        new_game = DBGame(
            player1_id=current_user.id,
            mode=request.mode,
            room_code=request.room_code if request.mode == "private" else None,
            current_turn=1,
            max_turns=MAX_TURNS,
            current_phase="draw",
            current_player="player1"
        )
        
        db.add(new_game)
        db.commit()
        db.refresh(new_game)
        
        # Récupérer l'état complet du jeu
        game_state = get_game_state(new_game, db, current_user)
        
        # Ajouter explicitement l'ID de la partie au niveau racine pour faciliter l'accès côté client
        response_data = {
            "game_id": new_game.id,  # ID explicite au niveau racine
            "game_state": game_state,  # État complet du jeu
            # Informations supplémentaires utiles
            "mode": new_game.mode,
            "room_code": new_game.room_code,
            "created_at": new_game.created_at.isoformat() if hasattr(new_game, 'created_at') else None
        }
        
        return FaduResponse(
            success=True,
            data=response_data,
            message="Nouvelle partie créée avec succès"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Erreur création de partie")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la création de la partie"
        )

@router.get("/{game_id}/status", response_model=FaduResponse)
async def get_game_status(
    game_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère l'état actuel de la partie"""
    try:
        game = db.query(DBGame).filter(DBGame.id == game_id).first()
        player_type = verify_game_status(game, current_user)
        
        game_state = get_game_state(game, db, current_user)
        
        return FaduResponse(
            success=True,
            data=game_state,
            message="État de la partie récupéré"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Erreur récupération statut de partie")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération du statut"
        )

@router.post("/{game_id}/cards/draw", response_model=FaduResponse)
async def draw_standard_card(
    game_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Tire une carte standard pour le joueur courant"""
    return await draw_card(game_id, False, current_user, db)

@router.post("/{game_id}/cards/sacrifice", response_model=FaduResponse)
async def draw_sacrifice_card(
    game_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Tire une carte de sacrifice pour le joueur courant"""
    return await draw_card(game_id, True, current_user, db)

async def draw_card(
    game_id: int,
    is_sacrifice: bool,
    current_user: User,
    db: Session
):
    """Fonction helper pour tirer une carte"""
    try:
        game = db.query(DBGame).filter(DBGame.id == game_id).first()
        player_type = verify_game_status(game, current_user)
        
        # Vérification que c'est bien le tour de l'utilisateur
        if game.current_player != player_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce n'est pas votre tour de jouer"
            )
        
        # Vérification de la phase
        if game.current_phase != "draw":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vous ne pouvez pas tirer de carte dans cette phase"
            )
        
        # Vérifier si le joueur a déjà sa carte principale (si on tire une carte de sacrifice)
        if is_sacrifice:
            has_main_card = (game.player1_card if player_type == "player1" else game.player2_card)
            if not has_main_card:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Vous devez d'abord tirer votre carte principale"
                )
        
        # Vérifier si le joueur a déjà tiré cette carte
        if player_type == "player1":
            already_drawn = (game.player1_sacrifice_card if is_sacrifice else game.player1_card)
        else:
            already_drawn = (game.player2_sacrifice_card if is_sacrifice else game.player2_card)
        
        if already_drawn:
            card_type = "sacrifice" if is_sacrifice else "standard"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Vous avez déjà tiré votre carte {card_type}"
            )
        
        # Tirage de la carte
        card_type = "sacrifice" if is_sacrifice else "standard"
        card = fadu_service.draw_card(card_type)
        
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucune carte disponible"
            )
        
        # Enregistrement de la carte tirée
        if player_type == "player1":
            if is_sacrifice:
                game.player1_sacrifice_card = card['name']
                game.player1_sacrifice_card_pfh = card['pfh']
            else:
                game.player1_card = card['name']
                game.player1_card_pfh = card['pfh']
        else:
            if is_sacrifice:
                game.player2_sacrifice_card = card['name']
                game.player2_sacrifice_card_pfh = card['pfh']
            else:
                game.player2_card = card['name']
                game.player2_card_pfh = card['pfh']
        
        db.commit()
        
        game_state = get_game_state(game, db, current_user)
        
        return FaduResponse(
            success=True,
            data={
                "card": card,
                "game_state": game_state
            },
            message=f"Carte {card_type} tirée avec succès"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Erreur tirage de carte")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du tirage de carte"
        )

@router.post("/{game_id}/strategy", response_model=FaduResponse)
async def choose_strategy(
    game_id: int,
    strategy_data: StrategyChoice,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enregistre la stratégie choisie par le joueur"""
    try:
        game = db.query(DBGame).filter(DBGame.id == game_id).first()
        player_type = verify_game_status(game, current_user)
        
        # Vérification que c'est bien le tour de l'utilisateur
        if game.current_player != player_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce n'est pas votre tour de jouer"
            )
        
        # Vérification de la phase
        if game.current_phase != "strategy":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vous ne pouvez pas choisir de stratégie dans cette phase"
            )
        
        # Validation de la stratégie
        if strategy_data.strategy not in strategy_logic.VALID_STRATEGIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stratégie invalide. Options: {strategy_logic.VALID_STRATEGIES}"
            )
        
        # Vérifier que le joueur a sa carte principale
        has_main_card = (game.player1_card if player_type == "player1" else game.player2_card)
        if not has_main_card:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vous devez avoir tiré votre carte principale"
            )
        
        # Enregistrement de la stratégie
        if player_type == "player1":
            if game.player1_strategy:
                raise HTTPException(400, "Vous avez déjà choisi votre stratégie")
            game.player1_strategy = strategy_data.strategy
        else:
            if game.player2_strategy:
                raise HTTPException(400, "Vous avez déjà choisi votre stratégie")
            game.player2_strategy = strategy_data.strategy
        
        db.commit()
        
        game_state = get_game_state(game, db, current_user)
        
        return FaduResponse(
            success=True,
            data={
                "strategy": strategy_data.strategy,
                "game_state": game_state
            },
            message="Stratégie enregistrée avec succès"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Erreur enregistrement stratégie")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'enregistrement de la stratégie"
        )

@router.post("/{game_id}/sacrifice", response_model=FaduResponse)
async def decide_sacrifice(
    game_id: int,
    decision: SacrificeDecision,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Gère la décision de sacrifice du joueur"""
    try:
        game = db.query(DBGame).filter(DBGame.id == game_id).first()
        player_type = verify_game_status(game, current_user)
        
        # Vérification que c'est bien le tour de l'utilisateur
        if game.current_player != player_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce n'est pas votre tour de jouer"
            )
        
        # Vérification de la phase
        if game.current_phase != "sacrifice":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vous ne pouvez pas décider de sacrifice dans cette phase"
            )
        
        # Vérifier que le joueur n'a pas déjà décidé
        current_decision = (game.player1_sacrifice if player_type == "player1" 
                          else game.player2_sacrifice)
        if current_decision is not None:
            raise HTTPException(400, "Vous avez déjà pris votre décision de sacrifice")
        
        # Récupération du joueur pour vérifier le PFH
        player = db.query(DBPlayer).filter(
            DBPlayer.id == (game.player1_id if player_type == "player1" else game.player2_id)
        ).first()
        
        # Vérification du PFH pour le sacrifice (mais on ne débite pas encore)
        if decision.sacrifice and player.current_pfh < MIN_PFH_FOR_SACRIFICE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"PFH insuffisant pour sacrifier (minimum {MIN_PFH_FOR_SACRIFICE} requis)"
            )
        
        # Enregistrement de la décision (sans débiter le PFH)
        if player_type == "player1":
            game.player1_sacrifice = decision.sacrifice
        else:
            game.player2_sacrifice = decision.sacrifice
        
        db.commit()
        
        game_state = get_game_state(game, db, current_user)
        
        return FaduResponse(
            success=True,
            data={
                "sacrifice": decision.sacrifice,
                "game_state": game_state
            },
            message="Décision de sacrifice enregistrée"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Erreur décision de sacrifice")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'enregistrement de la décision de sacrifice"
        )

@router.post("/{game_id}/next-phase", response_model=FaduResponse)
async def next_phase(
    game_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Passe à la phase suivante du jeu"""
    try:
        game = db.query(DBGame).filter(DBGame.id == game_id).first()
        player_type = verify_game_status(game, current_user)
        
        current_phase = game.current_phase
        
        # Vérifier si on peut passer à la phase suivante
        if not can_transition_to_next_phase(game, current_phase):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible de passer à la phase suivante, tous les joueurs n'ont pas terminé"
            )
        
        # Logique de transition selon la phase actuelle
        if current_phase == "draw":
            game.current_phase = "strategy"
            game.current_player = "player1"
            
        elif current_phase == "strategy":
            game.current_phase = "sacrifice"
            game.current_player = "player1"
            
        elif current_phase == "sacrifice":
            # Calculer les résultats du tour
            await process_battle_phase(game, db)
            game.current_phase = "results"
            
        elif current_phase == "results":
            # Préparer le tour suivant ou terminer la partie
            if game.current_turn < game.max_turns and not game.is_completed:
                # Tour suivant
                game.current_turn += 1
                game.current_phase = "draw"
                game.current_player = "player1"
                reset_turn_data(game)
            else:
                # Terminer la partie
                await finalize_game(game, db)
        
        db.commit()
        
        game_state = get_game_state(game, db, current_user)
        
        return FaduResponse(
            success=True,
            data=game_state,
            message="Phase mise à jour avec succès"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Erreur changement de phase")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du changement de phase"
        )

async def process_battle_phase(game: DBGame, db: Session):
    """Traite la phase de bataille et calcule les résultats"""
    try:
        # Récupération des joueurs
        player1 = db.query(DBPlayer).filter(DBPlayer.id == game.player1_id).first()
        player2 = db.query(DBPlayer).filter(DBPlayer.id == game.player2_id).first()
        
        # Débiter le PFH pour les sacrifices
        sacrifice_cost_p1 = MIN_PFH_FOR_SACRIFICE if game.player1_sacrifice else 0
        sacrifice_cost_p2 = MIN_PFH_FOR_SACRIFICE if game.player2_sacrifice else 0
        
        # Vérifications finales des PFH
        if game.player1_sacrifice and player1.current_pfh < sacrifice_cost_p1:
            raise HTTPException(400, "Joueur 1: PFH insuffisant pour le sacrifice")
        if game.player2_sacrifice and player2.current_pfh < sacrifice_cost_p2:
            raise HTTPException(400, "Joueur 2: PFH insuffisant pour le sacrifice")
        
        # Débiter les coûts de sacrifice
        player1.current_pfh -= sacrifice_cost_p1
        player2.current_pfh -= sacrifice_cost_p2
        
        # Calcul des résultats avec la logique de stratégie
        result = strategy_logic.calculate_turn_results(game)
        
        # Application des gains
        player1.current_pfh += result.player1_gains
        player2.current_pfh += result.player2_gains
        
        # S'assurer que les PFH ne descendent pas en dessous de 0
        player1.current_pfh = max(0, player1.current_pfh)
        player2.current_pfh = max(0, player2.current_pfh)
        
        # Enregistrement du résultat du tour
        turn_result = TurnResult(
            game_id=game.id,
            turn_number=game.current_turn,
            player1_card=game.player1_card,
            player1_strategy=game.player1_strategy,
            player1_sacrifice=game.player1_sacrifice,
            player1_gains=result.player1_gains,
            player1_final_pfh=player1.current_pfh,
            player2_card=game.player2_card,
            player2_strategy=game.player2_strategy,
            player2_sacrifice=game.player2_sacrifice,
            player2_gains=result.player2_gains,
            player2_final_pfh=player2.current_pfh
        )
        db.add(turn_result)
        
        logger.info(f"Tour {game.current_turn} calculé - P1: {result.player1_gains} PFH, P2: {result.player2_gains} PFH")
        
    except Exception as e:
        logger.exception("Erreur lors du calcul des résultats")
        raise

async def finalize_game(game: DBGame, db: Session):
    """Finalise la partie et détermine le gagnant"""
    try:
        player1 = db.query(DBPlayer).filter(DBPlayer.id == game.player1_id).first()
        player2 = db.query(DBPlayer).filter(DBPlayer.id == game.player2_id).first()
        
        # Détermination du gagnant
        if player1.current_pfh > player2.current_pfh:
            game.winner = "player1"
        elif player2.current_pfh > player1.current_pfh:
            game.winner = "player2"
        else:
            game.winner = "draw"
        
        game.is_completed = True
        
        logger.info(f"Partie {game.id} terminée - Gagnant: {game.winner}")
        
    except Exception as e:
        logger.exception("Erreur lors de la finalisation")
        raise