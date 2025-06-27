from pydantic_settings import BaseSettings
from pydantic import Field, PostgresDsn
from typing import Optional
from typing import List
from pydantic import field_validator
import json


class Settings(BaseSettings):
    # Configuration de l'application
    ENVIRONMENT: str = Field(
        default="development",
        env="ENVIRONMENT",
        description="Environnement d'exécution (development|production)"
    )
    
    DEBUG: bool = Field(
        default=False,
        env="DEBUG",
        description="Mode debug"
    )
    
    # Configuration de la base de données
    DATABASE_URL: PostgresDsn = Field(
        default="postgresql://fa_user:fagame2025@localhost:5432/fa_game_db",
        env="DATABASE_URL"
    )
    
    DB_POOL_SIZE: int = Field(
        default=5,
        env="DB_POOL_SIZE",
        ge=1,
        le=20
    )
    
    DB_MAX_OVERFLOW: int = Field(
        default=10,
        env="DB_MAX_OVERFLOW",
        ge=0
    )
    
    # Configuration du jeu
    MAX_GAME_TURNS: int = Field(
        default=20,
        env="MAX_GAME_TURNS",
        ge=10,
        le=100
    )
    
    INITIAL_PFH: int = Field(
        default=100,
        env="INITIAL_PFH",
        ge=1
    )
    
    SACRIFICE_COST: int = Field(
        default=14,
        env="SACRIFICE_COST",
        ge=1
    )
    API_TITLE: str = Field(
        default="Jeu Fa API", 
        env="API_TITLE",
        description="Titre de l'API"
    )
    
    API_DESCRIPTION: str = Field(
        default="API pour le jeu stratégique Fà",
        env="API_DESCRIPTION"
    )
    
    API_VERSION: str = Field(
        default="1.0.0",
        env="API_VERSION"
    )
    API_BASE_URL: str = Field(
        default="http://localhost:8000",
        env="API_BASE_URL",
        description="URL de base de l'API"
    )
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost",
            "http://localhost:3000",
            "http://127.0.0.1",
            "http://127.0.0.1:3000",
        ],
        env="CORS_ORIGINS",
        description="Liste des origines autorisées pour CORS"
    )

    @field_validator('CORS_ORIGINS', mode='before')
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                # Essai de parsing JSON d'abord
                return json.loads(v)
            except json.JSONDecodeError:
                # Fallback: séparation par virgules
                return [origin.strip() for origin in v.split(",")]
        return v
    
    ENABLE_REQUEST_LOGGING: bool = Field(
        default=True,
        env="ENABLE_REQUEST_LOGGING",
        description="Active/désactive le logging des requêtes HTTP"
    )
    # Sécurité
    ALGORITHM: str = Field(default="HS256", description="Algorithme de chiffrement JWT")
    SECRET_KEY: str = Field(
        default="(&9(hwLZv(I5LgoMB0fGuppzjBTRBNa*Jb)nJjU(Ch=jZuwRO(Q6ywIeOhl%j&PD",
        min_length=32,
        description="Clé secrète pour les tokens JWT"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
    RESET_TOKEN_EXPIRE_HOURS: int = Field(default=24)
    # Ajoutez ces nouvelles configurations
    REFRESH_SECRET_KEY: str = "3MPHBImV+Nhd25xxCefwGIEOXE7D2)ec!aNTXyOsiF(d4oK7_uGQgc5-"  # Doit être différente de SECRET_KEY
    
    class Config:
        env_file = ".env"
    
  
    
    ADMIN_API_KEY: str = Field(
        default="changeme",
        env="ADMIN_API_KEY",
        min_length=16
    )
    
    # Logging
    LOG_LEVEL: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"
    )
    

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Autorise les variables supplémentaires sans erreur
        extra = "ignore"

settings = Settings()