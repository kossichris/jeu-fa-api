import os
import logging
from typing import Any, Dict, List
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from starlette.middleware.base import BaseHTTPMiddleware

from app.routers import game_actions, players, admin, auth, matchmaking, fadu_router
from app.database import engine, Base
from app.config import Settings
settings = Settings()
from app.auth import get_current_admin_user



# Configuration du logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log", encoding='utf-8') 
    ]
)
logger = logging.getLogger(__name__)

class LogRequestsMiddleware(BaseHTTPMiddleware):
    """Middleware personnalisé pour logger les requêtes"""
    async def dispatch(self, request, call_next):
        start_time = datetime.now()
        response = await call_next(request)
        process_time = (datetime.now() - start_time).total_seconds() * 1000
        
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.2f}ms"
        )
        return response

def create_tables():
    """Crée les tables de la base de données avec vérification"""
    Base.metadata.create_all(bind=engine)
    try:
        if not engine.has_table("players"):  # Vérifie une table clé
            Base.metadata.create_all(bind=engine)
            logger.info("Tables créées avec succès")
        else:
            logger.info("Tables existantes détectées, skip création")
    except Exception as e:
        logger.critical(f"Erreur création tables: {str(e)}", exc_info=True)
        raise

def custom_openapi():
    """Génère une documentation OpenAPI personnalisée"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Jeu Fà API",
        version=settings.API_VERSION,
        description="API officielle du jeu stratégique Fà",
        routes=app.routes,
    )
    
    # Personnalisations supplémentaires
    openapi_schema["info"]["contact"] = {
        "name": "Support Technique",
        "email": "support@fagame.com"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

def get_application() -> FastAPI:
    """Factory pour l'application FastAPI avec configuration avancée"""
    app = FastAPI(
        title=settings.API_TITLE,
        description=settings.API_DESCRIPTION,
        version=settings.API_VERSION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        servers=[{"url": settings.API_BASE_URL, "description": settings.ENVIRONMENT}]
    )
    
    # Middleware CORS configurable
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:4200"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"]
    )
    
    # Middleware de logging
    if settings.ENABLE_REQUEST_LOGGING:
        app.add_middleware(LogRequestsMiddleware)
    
    # Gestion des erreurs globales
    @app.exception_handler(RequestValidationError)
    async def validation_handler(request, exc):
        logger.warning(f"Validation error: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": exc.errors(),
                "body": exc.body,
                "code": "validation_error"
            },
        )
    
    @app.exception_handler(500)
    async def internal_error_handler(request, exc):
        logger.error(f"Internal error: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "code": "server_error",
                "request_id": request.headers.get("X-Request-ID")
            },
        )
    
    # Routers avec protection API
    api_routers = [
        (game_actions.router, "/game", ["game"]),
        (players.router, "/players", ["players"]),
        (auth.router, "/auth", ["auth"]),
        (matchmaking.router, "/matchmaking", ["matchmaking"]),
        (fadu_router.router, "/fadu", ["fadu"])

    ]
    
    for router, prefix, tags in api_routers:
        app.include_router(
            router,
            prefix=f"/api/v1{prefix}",
            tags=tags,
            responses={404: {"description": "Not found"}}
        )
    # app.include_router(
    #     auth.router,
    #     prefix="/api/v1/auth",
    #     tags=["auth"],
    
    # )
    # Router admin protégé
    app.include_router(
        admin.router,
        prefix="/api/v1/admin",
        tags=["admin"],
        dependencies=[Depends(get_current_admin_user)]
    )
    
    # Endpoints système
    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "app": app.title,
            "version": app.version,
            "environment": settings.ENVIRONMENT,
            "docs": f"{settings.API_BASE_URL}/docs",
            "status": "operational"
        }
    
    @app.get("/health", include_in_schema=False)
    async def health():
        """Endpoint de santé complet"""
        db_healthy = False
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                db_healthy = True
        except:
            logger.error("Database health check failed")
        
        return {
            "status": "healthy" if db_healthy else "degraded",
            "services": {
                "database": db_healthy,
                "cache": True,  # À implémenter
                "storage": True  # À implémenter
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # Documentation personnalisée
    app.openapi = custom_openapi
    
    return app

app = get_application()

if __name__ == "__main__":
    # Initialisation
    create_tables()
    
    # Configuration Uvicorn avancée
    uvicorn_config = {
        "app": "app.main:app",
        "host": settings.SERVER_HOST,
        "port": settings.SERVER_PORT,
        "reload": settings.DEBUG,
        "log_level": "debug" if settings.DEBUG else "info",
        "workers": settings.UVICORN_WORKERS or (1 if settings.DEBUG else os.cpu_count()),
        "proxy_headers": True,
        "timeout_keep_alive": 30
    }
    
    if not settings.DEBUG:
        uvicorn_config.update({
            "access_log": False,
            "limit_concurrency": 100,
            "backlog": 2048
        })
    
    uvicorn.run(**uvicorn_config)
print("API_TITLE exists:", hasattr(settings, "API_TITLE"))  # Doit afficher True
print("All settings:", settings.model_dump())  # Affiche toutes les valeurs