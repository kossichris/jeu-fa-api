# Documentation de l'API

## Table des matières
- [Joueurs (`/players`)](#joueurs-players)
- [Actions de jeu (`/game-actions`)](#actions-de-jeu-game-actions)
- [FADU (`/fadu`)](#fadu-fadu)
- [Matchmaking (`/matchmaking`)](#matchmaking-matchmaking)
- [Administration (`/admin`)](#administration-admin)
- [Authentification (`/auth`)](#authentification-auth)

---

## Joueurs (`/players`)

### POST /
- **Créer un joueur (admin)**
- **Payload** :
```json
{
  "name": "John Doe"
}
```
- **Réponse** :
```json
{
  "id": 1,
  "name": "John Doe",
  "created_at": "2025-06-27T12:00:00",
  "is_active": true,
  "last_played": null
}
```

### GET /game/{game_id}/players
- **Récupérer les joueurs d’une partie**
- **Réponse** :
```json
{
  "player1": "Alice",
  "player2": "Bob"
}
```

### GET /{player_id}/stats
- **Statistiques d’un joueur**
- **Réponse** :
```json
{
  "player_id": 1,
  "games_played": 10,
  "wins": 4,
  "losses": 6,
  "win_rate": 40.0,
  "last_played": "2025-06-27T12:00:00",
  "average_score": 12.5
}
```

### DELETE /{player_id}
- **Supprimer un joueur (admin)**
- **Réponse** :
  - 204 No Content

### GET /random
- **Obtenir un joueur actif aléatoire**
- **Query optionnel** : `exclude_current=int`
- **Réponse** :
```json
{
  "id": 2,
  "name": "Bob",
  "created_at": "2025-06-27T12:00:00",
  "is_active": true,
  "last_played": "2025-06-27T11:00:00"
}
```

### GET /search
- **Recherche de joueurs par nom**
- **Query** : `query=str`, `limit=int`
- **Réponse** :
```json
[
  {
    "id": 1,
    "name": "Alice",
    "created_at": "2025-06-27T12:00:00",
    "is_active": true,
    "last_played": null
  }
]
```

### GET /
- **Liste paginée des joueurs**
- **Query** : `page=int`, `limit=int`, `active_only=bool`
- **Réponse** :
```json
{
  "data": [
    { "id": 1, "name": "Alice", ... }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "total_pages": 5,
    "has_next": true,
    "has_prev": false
  }
}
```

### GET /{player_id}
- **Détail d’un joueur**
- **Réponse** :
```json
{
  "id": 1,
  "name": "Alice",
  "created_at": "2025-06-27T12:00:00",
  "is_active": true,
  "last_played": null
}
```

---

## Actions de jeu (`/game-actions`)

### POST /create
- **Créer une nouvelle partie**
- **Payload** :
```json
{
  "mode": "classic",
  "room_code": "ABC123" // optionnel selon le mode
}
```
- **Réponse** :
```json
{
  "success": true,
  "data": {
    "game_id": 42,
    "game_state": { /* ... */ },
    "mode": "classic",
    "room_code": "ABC123",
    "created_at": "2025-06-27T12:00:00"
  },
  "message": "Nouvelle partie créée avec succès"
}
```

### GET /{game_id}/status
- **Statut d’une partie**
- **Réponse** :
```json
{
  "success": true,
  "data": { /* état complet du jeu */ },
  "message": "État de la partie récupéré"
}
```

### POST /{game_id}/cards/draw
- **Tirer une carte standard**
- **Réponse** :
```json
{
  "success": true,
  "data": {
    "card": { /* ... */ },
    "game_state": { /* ... */ }
  },
  "message": "Carte standard tirée avec succès"
}
```

### POST /{game_id}/cards/sacrifice
- **Tirer une carte sacrifice**
- **Réponse** :
```json
{
  "success": true,
  "data": {
    "card": { /* ... */ },
    "game_state": { /* ... */ }
  },
  "message": "Carte sacrifice tirée avec succès"
}
```

### POST /{game_id}/strategy
- **Choisir une stratégie**
- **Payload** :
```json
{
  "strategy": "aggressive"
}
```
- **Réponse** :
```json
{
  "success": true,
  "data": {
    "strategy": "aggressive",
    "game_state": { /* ... */ }
  },
  "message": "Stratégie enregistrée avec succès"
}
```

### POST /{game_id}/sacrifice
- **Décider d’un sacrifice**
- **Payload** :
```json
{
  "sacrifice": true
}
```
- **Réponse** :
```json
{
  "success": true,
  "data": {
    "sacrifice": true,
    "game_state": { /* ... */ }
  },
  "message": "Décision de sacrifice enregistrée"
}
```

### POST /{game_id}/next-phase
- **Passer à la phase suivante**
- **Réponse** :
```json
{
  "success": true,
  "data": { /* état du jeu après transition */ },
  "message": "Phase suivante atteinte"
}
```

---

## FADU (`/fadu`)

### POST /draw
- **Tirer une carte**
- **Payload** :
```json
{
  "card_type": "standard" // ou "sacrifice"
}
```
- **Réponse** :
```json
{
  "success": true,
  "card": { /* ... */ },
  "message": "Carte tirée avec succès",
  "card_type": "standard",
  "pfh_value": 10,
  "modifiers": {}
}
```

### POST /sacrifice
- **Sacrifice**
- **Payload** :
```json
{
  "current_pfh": 20
}
```
- **Réponse** :
```json
{
  "success": true,
  "sacrifice_cost": 14,
  "remaining_pfh": 6,
  "sacrifice_card": { /* ... */ },
  "message": "Sacrifice effectué avec succès"
}
```

### GET /probabilities
- **Probabilités**
- **Réponse** :
```json
{
  "standard_cards": { "CardA": 0.1 },
  "sacrifice_cards": { "CardB": 0.2 },
  "total_cards": 42,
  "last_updated": "2025-06-27T12:00:00"
}
```

### GET /cards/{card_id}
- **Détail d’une carte**
- **Réponse** :
```json
{
  "success": true,
  "card": { /* ... */ },
  "message": "Détails de la carte récupérés avec succès"
}
```

### GET /stats
- **Statistiques FADU**
- **Réponse** :
```json
{
  "success": true,
  "stats": { /* ... */ },
  "message": "Statistiques récupérées avec succès"
}
```

---

## Matchmaking (`/matchmaking`)

### POST /matchmaking
- **Rejoindre le matchmaking**
- **Payload** :
```json
{
  "user_id": "1"
}
```
- **Réponse** :
```json
{
  "status": "waiting_for_opponent"
}
// ou
{
  "status": "match_found",
  "opponent": "Bob",
  "game_id": "uuid-1234"
}
```

### GET /matchmaking/status/{user_id}
- **Statut du matchmaking**
- **Réponse** :
```json
{
  "status": "waiting_for_opponent"
}
// ou
{
  "status": "match_found",
  "opponent": "Alice",
  "game_id": "uuid-1234"
}
```

### DELETE /matchmaking/{user_id}
- **Quitter le matchmaking**
- **Réponse** :
```json
{
  "status": "removed_from_queue"
}
```

### GET /matchmaking/queue/info
- **Infos sur la file d’attente**
- **Réponse** :
```json
{
  "queue_length": 1,
  "users_in_queue": ["1"],
  "pending_matches": 0
}
```

---

## Administration (`/admin`)

### POST /reset-db
- **Réinitialiser la base (admin)**
- **Header** : `X-API-KEY: <clé admin>`
- **Réponse** :
```json
{
  "message": "Base de données réinitialisée avec succès",
  "tables_recréées": ["users", "games", ...]
}
```

### GET /system-status
- **Statut système**
- **Réponse** :
```json
{
  "status": "ok",
  "environment": "development",
  "database": {
    "connected": true,
    "database_version": "PostgreSQL 14.0",
    "tables": ["users", "games", ...]
  },
  "system": {
    "python_version": "3.11.0",
    "api_version": "1.0.0"
  },
  "ready": true
}
```

---

## Authentification (`/auth`)

### POST /login
- **Connexion**
- **Payload (form-data)** :
  - `username`: email
  - `password`: mot de passe
- **Réponse** :
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "user_id": 1,
  "username": "alice",
  "expires_at": "2025-06-27T13:00:00"
}
```

### POST /register
- **Inscription**
- **Payload** :
```json
{
  "username": "alice",
  "email": "alice@email.com",
  "password": "Password123!",
  "confirm_password": "Password123!"
}
```
- **Réponse** :
```json
{
  "message": "Compte créé avec succès",
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "user_id": 1,
  "player_id": 1,
  "expires_at": "2025-06-27T13:00:00"
}
```

### GET /me
- **Infos utilisateur courant**
- **Header** : `Authorization: Bearer <token>`
- **Réponse** :
```json
{
  "id": 1,
  "username": "alice",
  "email": "alice@email.com",
  "is_active": true,
  "created_at": "2025-06-27T12:00:00"
}
```

### POST /refresh
- **Rafraîchir le token**
- **Payload** :
```json
{
  "refresh_token": "..."
}
```
- **Réponse** :
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "user_id": 1,
  "username": "alice",
  "expires_at": "2025-06-27T13:00:00"
}
```

### POST /logout
- **Déconnexion**
- **Header** : `Authorization: Bearer <token>`
- **Réponse** :
```json
{
  "message": "Déconnexion réussie"
}
```

---

> Pour chaque endpoint, voir le code source pour les paramètres, réponses et statuts détaillés. Cette documentation donne un aperçu global de l’API REST du projet enrichi avec les schémas d'entrée et de sortie.
