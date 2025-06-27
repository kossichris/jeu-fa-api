# # routers/fadu_router.py
# from fastapi import APIRouter, Depends, HTTPException
# from app.game_logic.fadu_logic import FaduService
# from typing import Dict

# router = APIRouter()
# fadu_service = FaduService()

# @router.post("/draw")
# async def draw_card(card_type: str = 'standard') -> Dict:
#     """Endpoint pour tirer une carte"""
#     card = fadu_service.draw_card(card_type)
#     if not card:
#         raise HTTPException(status_code=400, detail="Impossible de tirer une carte")
#     return card

# @router.post("/sacrifice")
# async def perform_sacrifice(current_pfh: int) -> Dict:
#     """Endpoint pour effectuer un sacrifice"""
#     if current_pfh < 1:
#         raise HTTPException(status_code=400, detail="PFH invalide")
#     return fadu_service.perform_sacrifice(current_pfh)

# @router.get("/probabilities")
# async def get_probabilities() -> Dict:
#     """Récupère les probabilités de tirage"""
#     return fadu_service.get_card_probabilities()

# routers/fadu_router.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, validator
from typing import Dict, Optional, Literal
from enum import Enum

from app.game_logic.fadu_logic import FaduService
from app.database import get_db
from app import models, utils

# Configuration du logger
logger = logging.getLogger(__name__)

# Configuration OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

# Configuration du router
router = APIRouter(
    prefix="/fadu",
    tags=["fadu", "cards"],
    responses={404: {"description": "Not found"}}
)

# Initialisation du service
fadu_service = FaduService()

# Modèles Pydantic pour les requêtes/réponses
class CardType(str, Enum):
    STANDARD = "standard"
    SACRIFICE = "sacrifice"

class DrawCardRequest(BaseModel):
    card_type: CardType = Field(default=CardType.STANDARD, description="Type de carte à tirer")

class DrawCardResponse(BaseModel):
    success: bool
    card: Optional[Dict] = None
    message: str
    card_type: str
    pfh_value: Optional[int] = None
    modifiers: Optional[Dict] = None

class SacrificeRequest(BaseModel):
    current_pfh: int = Field(gt=0, description="PFH actuel du joueur (doit être > 0)")
    
    @validator('current_pfh')
    def validate_pfh(cls, v):
        if v < 14:  # Coût minimum pour un sacrifice
            raise ValueError("PFH insuffisant pour effectuer un sacrifice (minimum 14)")
        return v

class SacrificeResponse(BaseModel):
    success: bool
    sacrifice_cost: int
    remaining_pfh: int
    sacrifice_card: Optional[Dict] = None
    message: str

class ProbabilitiesResponse(BaseModel):
    standard_cards: Dict[str, float]
    sacrifice_cards: Dict[str, float]
    total_cards: int
    last_updated: Optional[str] = None

# Fonction d'authentification
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Récupère l'utilisateur connecté"""
    try:
        payload = utils.decode_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        email = payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide : email manquant",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = db.query(models.User).filter(
            models.User.email == email,
            models.User.is_active == True
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé"
            )
        
        return user
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error authenticating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Erreur d'authentification",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Endpoints
@router.post("/draw", response_model=DrawCardResponse)
async def draw_card(
    request: DrawCardRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> DrawCardResponse:
    """
    Endpoint pour tirer une carte Fadu
    """
    try:
        logger.info(f"User {current_user.email} drawing {request.card_type.value} card")
        
        # Appel du service pour tirer une carte
        card = fadu_service.draw_card(request.card_type.value)
        
        if not card:
            logger.warning(f"Failed to draw card for user {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible de tirer une carte"
            )
        
        logger.info(f"Successfully drew card for user {current_user.email}: {card.get('name', 'Unknown')}")
        
        return DrawCardResponse(
            success=True,
            card=card,
            message="Carte tirée avec succès",
            card_type=request.card_type.value,
            pfh_value=card.get("pfh"),
            modifiers=card.get("modifiers", {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error drawing card for user {current_user.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors du tirage de carte"
        )

@router.post("/sacrifice", response_model=SacrificeResponse)
async def perform_sacrifice(
    request: SacrificeRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> SacrificeResponse:
    """
    Endpoint pour effectuer un sacrifice et obtenir une carte sacrifice
    """
    try:
        logger.info(f"User {current_user.email} performing sacrifice with PFH: {request.current_pfh}")
        
        # Vérification que l'utilisateur a suffisamment de PFH
        if request.current_pfh < 14:  # Coût du sacrifice
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PFH insuffisant pour effectuer un sacrifice (minimum 14)"
            )
        
        # Appel du service pour effectuer le sacrifice
        sacrifice_result = fadu_service.perform_sacrifice(request.current_pfh)
        
        if not sacrifice_result:
            logger.warning(f"Failed to perform sacrifice for user {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible d'effectuer le sacrifice"
            )
        
        logger.info(f"Successfully performed sacrifice for user {current_user.email}")
        
        return SacrificeResponse(
            success=True,
            sacrifice_cost=sacrifice_result.get("cost", 14),
            remaining_pfh=sacrifice_result.get("remaining_pfh", request.current_pfh - 14),
            sacrifice_card=sacrifice_result.get("card"),
            message="Sacrifice effectué avec succès"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error performing sacrifice for user {current_user.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors du sacrifice"
        )

@router.get("/probabilities", response_model=ProbabilitiesResponse)
async def get_probabilities(
    current_user: models.User = Depends(get_current_user)
) -> ProbabilitiesResponse:
    """
    Récupère les probabilités de tirage des cartes Fadu
    """
    try:
        logger.info(f"User {current_user.email} requesting card probabilities")
        
        # Appel du service pour récupérer les probabilités
        probabilities = fadu_service.get_card_probabilities()
        
        if not probabilities:
            logger.warning("No probabilities data available")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Données de probabilités non disponibles"
            )
        
        return ProbabilitiesResponse(
            standard_cards=probabilities.get("standard", {}),
            sacrifice_cards=probabilities.get("sacrifice", {}),
            total_cards=probabilities.get("total_cards", 0),
            last_updated=probabilities.get("last_updated")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting probabilities for user {current_user.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de la récupération des probabilités"
        )

@router.get("/cards/{card_id}")
async def get_card_details(
    card_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Récupère les détails d'une carte spécifique
    """
    try:
        logger.info(f"User {current_user.email} requesting details for card {card_id}")
        
        # Récupération des détails de la carte
        card_details = fadu_service.get_card_by_id(card_id)
        
        if not card_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Carte avec l'ID {card_id} non trouvée"
            )
        
        return {
            "success": True,
            "card": card_details,
            "message": "Détails de la carte récupérés avec succès"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting card details for user {current_user.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de la récupération des détails"
        )

@router.get("/stats")
async def get_fadu_stats(
    current_user: models.User = Depends(get_current_user)
):
    """
    Récupère les statistiques générales des cartes Fadu
    """
    try:
        logger.info(f"User {current_user.email} requesting Fadu stats")
        
        stats = fadu_service.get_fadu_statistics()
        
        return {
            "success": True,
            "stats": stats,
            "message": "Statistiques récupérées avec succès"
        }
        
    except Exception as e:
        logger.error(f"Error getting Fadu stats for user {current_user.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de la récupération des statistiques"
        )