# import logging
# from fastapi import APIRouter, Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
# from sqlalchemy.orm import Session
# from datetime import timedelta, datetime 
# from pydantic import BaseModel, EmailStr, validator
# from app import models, database, utils
# from typing import Optional
# from fastapi import Response
# from app.schemas import Token, UserResponse
# from app.utils import verify_password, hash_password, create_access_token, decode_token
# from ..models import User
# from ..database import get_db
# from app.token_utils import create_access_token, create_refresh_token
# from sqlalchemy.exc import SQLAlchemyError


# logger = logging.getLogger(__name__)


# from app import (
#     models, 
#     schemas,
#     database,
#     utils,
#     auth  # Module pour la gestion JWT
# )

# router = APIRouter(
#     responses={404: {"description": "Not found"}}
    
# )

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

# @router.post("/login", response_model=schemas.Token)
# async def login(
#     response: Response,
#     form_data: OAuth2PasswordRequestForm = Depends(),
#     db: Session = Depends(database.get_db)
# ):
#     # 1. Vérification de l'utilisateur
#     user = db.query(models.User).filter(
#         models.User.email == form_data.username
#     ).first()

#     if not user or not utils.verify_password(form_data.password, user.hashed_password):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Email ou mot de passe incorrect",
#             headers={"WWW-Authenticate": "Bearer"},
#         )

#     # 2. Génération des tokens JWT
#     access_token_expires = timedelta(minutes=30)
#     refresh_token_expires = timedelta(days=7)
    
#     access_token = create_access_token(  # Appel direct sans auth.
#         data={"sub": user.email},
#         expires_delta=access_token_expires
#     )
#     refresh_token = create_refresh_token(  # Appel direct sans auth.
#         data={"sub": user.email},
#         expires_delta=refresh_token_expires
#     )

#     # 3. Configuration des headers CORS
#     response.headers["Access-Control-Allow-Origin"] = "http://localhost:4200"
#     response.headers["Access-Control-Allow-Credentials"] = "true"

#     # 4. Retour de la réponse complète
#     return {
#         "access_token": access_token,
#         "refresh_token": refresh_token,  # Ajout du refresh token
#         "token_type": "bearer",
#         "user_id": user.id,
#         "username": user.username,
#         "expires_at": datetime.utcnow() + access_token_expires  # Date d'expiration
#     }


# class RegisterRequest(BaseModel):
#     username: str
#     email: EmailStr
#     password: str
#     confirm_password: str

#     @validator('username')
#     def validate_username(cls, v):
#         if len(v) < 3 or len(v) > 20:
#             raise ValueError("Le nom d'utilisateur doit contenir entre 3 et 20 caractères")
#         if not v.isalnum() and '_' not in v:
#             raise ValueError("Seuls les caractères alphanumériques et _ sont autorisés")
#         return v

#     @validator('password')
#     def validate_password(cls, v):
#         if len(v) < 8:
#             raise ValueError("Le mot de passe doit contenir au moins 8 caractères")
#         if not any(c.isupper() for c in v):
#             raise ValueError("Le mot de passe doit contenir au moins une majuscule")
#         if not any(c.islower() for c in v):
#             raise ValueError("Le mot de passe doit contenir au moins une minuscule")
#         if not any(c.isdigit() for c in v):
#             raise ValueError("Le mot de passe doit contenir au moins un chiffre")
#         if not any(c in '@$!%*?&' for c in v):
#             raise ValueError("Le mot de passe doit contenir au moins un caractère spécial (@$!%*?&)")
#         return v

#     @validator('confirm_password')
#     def passwords_match(cls, v, values):
#         if 'password' in values and v != values['password']:
#             raise ValueError("Les mots de passe ne correspondent pas")
#         return v

# class RegisterResponse(BaseModel):
#     message: str
#     access_token: str
#     refresh_token: str
#     user_id: int

# import logging
# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlalchemy.exc import SQLAlchemyError, IntegrityError
# from sqlalchemy.orm import Session

# logger = logging.getLogger(__name__)

# @router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
# async def register(
#     user_data: RegisterRequest, 
#     db: Session = Depends(database.get_db)
# ):
#     try:
#         # Vérification de l'unicité dans une transaction
#         with db.begin():
#             existing_user = db.query(models.User).filter(
#                 (models.User.email == user_data.email) | 
#                 (models.User.username == user_data.username)
#             ).first()
            
#             if existing_user:
#                 logger.warning(f"Registration attempt with existing credentials: {user_data.email}")
#                 raise HTTPException(
#                     status_code=status.HTTP_400_BAD_REQUEST,
#                     detail="Email ou nom d'utilisateur déjà utilisé"
#                 )

#             # Création de l'utilisateur
#             hashed_password = utils.hash_password(user_data.password)
#             new_user = models.User(
#                 username=user_data.username,
#                 email=user_data.email,
#                 hashed_password=hashed_password
#             )
#             db.add(new_user)
#             db.flush()  # Génère l'ID sans commit final

#             # Création du joueur associé
#             new_player = models.DBPlayer(
#                 name=user_data.username,
#                 user_id=new_user.id,
#                 pfh=100,
#                 is_active=True
#             )
#             db.add(new_player)

#         # Génération des tokens après succès de la transaction
#         access_token = utils.create_access_token(data={"sub": new_user.email})
#         refresh_token = utils.create_refresh_token(data={"sub": new_user.email})

#         logger.info(f"New user registered successfully: {new_user.email} (ID: {new_user.id})")

#         return {
#             "message": "Compte créé avec succès",
#             "access_token": access_token,
#             "refresh_token": refresh_token,
#             "user_id": new_user.id,
#             "player_id": new_player.id
#         }

#     except IntegrityError as e:
#         db.rollback()
#         logger.error(f"Database integrity error during registration: {str(e)}", exc_info=True)
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Violation de contrainte de base de données"
#         )
        
#     except SQLAlchemyError as e:
#         db.rollback()
#         logger.error(f"Database error during registration: {str(e)}", exc_info=True)
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Erreur lors de la création du compte"
#         )
        
#     except Exception as e:
#         db.rollback()
#         logger.critical(f"Unexpected error during registration: {str(e)}", exc_info=True)
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Erreur inattendue lors de la création du compte"
#         )

# @router.get("/me", response_model=UserResponse)
# async def get_current_user(
#     token: str = Depends(oauth2_scheme),
#     db: Session = Depends(get_db)
# ):
#     try:
#         # Décodage du token
#         payload = decode_token(token)
#         email = payload.get("sub")
        
#         if not email:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Token invalide : email manquant",
#                 headers={"WWW-Authenticate": "Bearer"},
#             )

#         # Récupération de l'utilisateur
#         user = db.query(User).filter(User.email == email).first()
#         if not user:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Utilisateur non trouvé",
#             )

#         return user

#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail=f"Erreur d'authentification : {str(e)}",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
# @router.post("/refresh", response_model=schemas.Token)
# async def refresh_token(
#     refresh_request: schemas.RefreshTokenRequest,
#     db: Session = Depends(get_db)
# ):
#     payload = utils.verify_refresh_token(refresh_request.refresh_token)
#     if not payload:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Refresh token invalide ou expiré",
#         )
    
#     email = payload.get("sub")
#     user = db.query(models.User).filter(models.User.email == email).first()
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Utilisateur non trouvé",
#         )
    
#     access_token_expires = timedelta(minutes=30)
#     new_refresh_token_expires = timedelta(days=7)
    
#     return {
#         "access_token": utils.create_access_token(
#             data={"sub": user.email},
#             expires_delta=access_token_expires
#         ),
#         "refresh_token": utils.create_refresh_token(
#             data={"sub": user.email},
#             expires_delta=new_refresh_token_expires
#         ),
#         "token_type": "bearer",
#         "expires_at": datetime.utcnow() + access_token_expires
#     }


import logging
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from datetime import timedelta, datetime
from pydantic import BaseModel, EmailStr, validator
from typing import Optional

from app import models, database, utils, schemas
from app.database import get_db

# Configuration du logger
logger = logging.getLogger(__name__)

# Configuration du router
router = APIRouter(
    #prefix="/auth",
    tags=["authentication"],
    responses={404: {"description": "Not found"}}
)

# Configuration OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

# Modèles Pydantic pour les requêtes
class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirm_password: str

    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3 or len(v) > 20:
            raise ValueError("Le nom d'utilisateur doit contenir entre 3 et 20 caractères")
        if not v.replace('_', '').isalnum():
            raise ValueError("Seuls les caractères alphanumériques et _ sont autorisés")
        return v

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères")
        if not any(c.isupper() for c in v):
            raise ValueError("Le mot de passe doit contenir au moins une majuscule")
        if not any(c.islower() for c in v):
            raise ValueError("Le mot de passe doit contenir au moins une minuscule")
        if not any(c.isdigit() for c in v):
            raise ValueError("Le mot de passe doit contenir au moins un chiffre")
        if not any(c in '@$!%*?&' for c in v):
            raise ValueError("Le mot de passe doit contenir au moins un caractère spécial (@$!%*?&)")
        return v

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError("Les mots de passe ne correspondent pas")
        return v

class RegisterResponse(BaseModel):
    message: str
    access_token: str
    refresh_token: str
    token_type: str
    user_id: int
    player_id: Optional[int] = None
    expires_at: datetime

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# Endpoints
@router.post("/login", response_model=schemas.Token)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authentification d'un utilisateur existant
    """
    try:
        # Vérification de l'utilisateur
        user = db.query(models.User).filter(
            models.User.email == form_data.username
        ).first()

        if not user or not utils.verify_password(form_data.password, user.hashed_password):
            logger.warning(f"Failed login attempt for email: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Génération des tokens JWT
        access_token_expires = timedelta(minutes=30)
        refresh_token_expires = timedelta(days=7)
        
        access_token = utils.create_access_token(
            data={"sub": user.email, "user_id": user.id},
            expires_delta=access_token_expires
        )
        refresh_token = utils.create_refresh_token(
            data={"sub": user.email, "user_id": user.id},
            expires_delta=refresh_token_expires
        )

        # Configuration des headers CORS
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:4200"
        response.headers["Access-Control-Allow-Credentials"] = "true"

        logger.info(f"Successful login for user: {user.email} (ID: {user.id})")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username,
            "expires_at": datetime.utcnow() + access_token_expires
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: RegisterRequest, 
    db: Session = Depends(get_db)
):
    """
    Inscription d'un nouvel utilisateur
    """
    try:
        # Vérification de l'unicité
        existing_user = db.query(models.User).filter(
            (models.User.email == user_data.email) | 
            (models.User.username == user_data.username)
        ).first()
        
        if existing_user:
            logger.warning(f"Registration attempt with existing credentials: {user_data.email}")
            if existing_user.email == user_data.email:
                detail = "Cette adresse email est déjà utilisée"
            else:
                detail = "Ce nom d'utilisateur est déjà pris"
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail
            )

        # Création de l'utilisateur dans une transaction
        try:
            # Hashage du mot de passe
            hashed_password = utils.hash_password(user_data.password)
            
            # Création de l'utilisateur
            new_user = models.User(
                username=user_data.username,
                email=user_data.email,
                hashed_password=hashed_password,
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            db.add(new_user)
            db.flush()  # Pour obtenir l'ID de l'utilisateur

            # Création du joueur associé
            new_player = models.DBPlayer(
                name=user_data.username,
                user_id=new_user.id,
                pfh=100,  # PFH initial
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            db.add(new_player)
            db.commit()  # Validation de la transaction

            # Génération des tokens
            access_token_expires = timedelta(minutes=30)
            refresh_token_expires = timedelta(days=7)
            
            access_token = utils.create_access_token(
                data={"sub": new_user.email, "user_id": new_user.id},
                expires_delta=access_token_expires
            )
            refresh_token = utils.create_refresh_token(
                data={"sub": new_user.email, "user_id": new_user.id},
                expires_delta=refresh_token_expires
            )

            logger.info(f"New user registered successfully: {new_user.email} (ID: {new_user.id})")

            return RegisterResponse(
                message="Compte créé avec succès",
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                user_id=new_user.id,
                player_id=new_player.id,
                expires_at=datetime.utcnow() + access_token_expires
            )

        except IntegrityError as e:
            db.rollback()
            logger.error(f"Database integrity error during registration: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email ou nom d'utilisateur déjà utilisé"
            )

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error during registration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la création du compte"
        )
    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error during registration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur inattendue lors de la création du compte"
        )

@router.get("/me", response_model=schemas.UserResponse)
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Récupération des informations de l'utilisateur connecté
    """
    try:
        # Décodage du token
        payload = utils.decode_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        email = payload.get("sub")
        user_id = payload.get("user_id")
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide : informations manquantes",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Récupération de l'utilisateur avec ses relations
        user = db.query(models.User).filter(
            models.User.email == email,
            models.User.is_active == True
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé ou inactif",
            )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Erreur d'authentification",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/refresh", response_model=schemas.Token)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Renouvellement des tokens d'authentification
    """
    try:
        # Vérification du refresh token
        payload = utils.verify_refresh_token(refresh_request.refresh_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token invalide ou expiré",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        email = payload.get("sub")
        user_id = payload.get("user_id")
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token invalide : informations manquantes",
            )

        # Vérification de l'utilisateur
        user = db.query(models.User).filter(
            models.User.email == email,
            models.User.is_active == True
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé ou inactif",
            )
        
        # Génération de nouveaux tokens
        access_token_expires = timedelta(minutes=30)
        refresh_token_expires = timedelta(days=7)
        
        new_access_token = utils.create_access_token(
            data={"sub": user.email, "user_id": user.id},
            expires_delta=access_token_expires
        )
        new_refresh_token = utils.create_refresh_token(
            data={"sub": user.email, "user_id": user.id},
            expires_delta=refresh_token_expires
        )

        logger.info(f"Tokens refreshed for user: {user.email}")

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username,
            "expires_at": datetime.utcnow() + access_token_expires
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du renouvellement du token"
        )

@router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Déconnexion de l'utilisateur
    Note: Dans cette implémentation, nous invalidons simplement côté client
    Pour une vraie invalidation, il faudrait une blacklist de tokens
    """
    try:
        # Vérification du token pour s'assurer qu'il est valide
        payload = utils.decode_token(token)
        if payload:
            email = payload.get("sub")
            logger.info(f"User logged out: {email}")
        
        return {"message": "Déconnexion réussie"}
    
    except Exception as e:
        logger.warning(f"Logout attempt with invalid token: {str(e)}")
        return {"message": "Déconnexion réussie"}  # On retourne succès même si le token est invalide