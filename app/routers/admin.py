from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy import text
from sqlalchemy.orm import Session
import logging
from typing import Dict, Any
import sys

from app.database import get_db, engine
from app.models import SQLBase
from app.config import settings

router = APIRouter(
   
)

# Configuration de la sécurité
API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_api_key(api_key: str = Security(api_key_header)) -> str:
    """Valide la clé API pour les routes protégées"""
    if api_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Clé API invalide"
        )
    return api_key

@router.post("/reset-db", dependencies=[Security(get_api_key)])
def reset_database(db: Session = Depends(get_db)):
    """
    Réinitialise complètement la base de données (pour le développement)
    
    Attention: Cette opération supprime toutes les données!
    """
    try:
        logging.warning("Début de la réinitialisation de la base de données")
        
        # Ajout d'une vérification de l'environnement
        if settings.ENVIRONMENT == "production":
            raise HTTPException(
                status_code=403,
                detail="Opération non autorisée en production"
            )
        
        SQLBase.metadata.drop_all(bind=engine)
        SQLBase.metadata.create_all(bind=engine)
        
        logging.warning("Réinitialisation de la base de données terminée avec succès")
        return {
            "message": "Base de données réinitialisée avec succès",
            "tables_recréées": sorted(SQLBase.metadata.tables.keys())
        }
    except Exception as e:
        logging.error(f"Échec de la réinitialisation: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur lors de la réinitialisation: {str(e)}"
        )

@router.get("/system-status")
def system_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Vérifie l'état complet du système
    
    Retourne:
    - Statut de l'API
    - Connexion à la base de données
    - Version de la base de données
    - Statistiques de base
    """
    db_status = {"connected": False}
    
    try:
        # Test de connexion à la base de données
        db.execute(text("SELECT 1"))
        db_status.update({
            "connected": True,
            "database_version": str(db.execute(text("SELECT version()")).scalar()),
            "tables": sorted(SQLBase.metadata.tables.keys())
        })
    except Exception as e:
        logging.error(f"Erreur de connexion à la base: {str(e)}")
        db_status["error"] = str(e)

    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "system": {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "api_version": settings.API_VERSION
        },
        "ready": db_status["connected"]
    }