import json
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from ..websocket_manager import (
    websocket_manager, 
    ConnectionType, 
    WSMessageType, 
    create_ws_message
)
from ..database import get_db
from ..models import DBPlayer, DBGame, User

logger = logging.getLogger(__name__)
router = APIRouter()

# Explanation of the player_websocket function:

@router.websocket("/ws/player/{player_id}")
async def player_websocket(
    websocket: WebSocket,
    player_id: int,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for individual player connections.

    This function manages a WebSocket connection for a specific player, identified by `player_id`.
    The main responsibilities of this function are:

    1. Accept the WebSocket connection from the client.
    2. Validate that the player with the given `player_id` exists in the database.
       - If the player does not exist, it sends an error message and closes the connection.
    3. Register the WebSocket connection with the application's WebSocket manager, associating it with the player.
    4. Send a welcome message to the player upon successful connection.
    5. Enter a loop to continuously receive and process messages from the client:
       - Each message is expected to be JSON. If the message is not valid JSON, an error is sent back.
       - For each valid message, it delegates handling to the `handle_player_message` function, which processes the message according to its type.
       - If the client disconnects, the loop breaks.
       - Any unexpected errors are logged and an error message is sent to the client.
    6. When the connection is closed or an error occurs, the WebSocket is unregistered from the WebSocket manager in the `finally` block.

    This endpoint enables real-time, bidirectional communication between the server and a specific player client.
    """

    try:
        # Accept the connection first
        await websocket.accept()
        
        # Validate player exists
        db = next(get_db())
        player = db.query(DBPlayer).filter(DBPlayer.id == player_id).first()
        if not player:
            await websocket.send_text(json.dumps({
                "type": "error",
                "data": {"message": "Player not found"},
                "timestamp": datetime.utcnow().isoformat()
            }))
            await websocket.close()
            return
        
        # Connect to WebSocket manager
        await websocket_manager.connect(
            websocket, 
            ConnectionType.PLAYER, 
            player_id,
            {"player_name": player.name}
        )
        
        # Send welcome message
        welcome_msg = create_ws_message(
            WSMessageType.PLAYER_CONNECT,
            {
                "player_id": player_id,
                "player_name": player.name,
                "message": "Connected successfully"
            }
        )
        await websocket_manager.send_personal_message(websocket, welcome_msg)
        
        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                await handle_player_message(websocket, player_id, message, db)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                error_msg = create_ws_message(
                    WSMessageType.ERROR,
                    {"message": "Invalid JSON format"}
                )
                await websocket_manager.send_personal_message(websocket, error_msg)
            except Exception as e:
                logger.error(f"Error handling player message: {e}")
                error_msg = create_ws_message(
                    WSMessageType.ERROR,
                    {"message": "Internal server error"}
                )
                await websocket_manager.send_personal_message(websocket, error_msg)
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket_manager.disconnect(websocket)

# This defines a WebSocket endpoint for game-specific connections.
# When a client connects to ws://<host>/websocket/ws/game/{game_id}?player_id=<player_id>,
# this async function is called. It receives:
#   - websocket: the WebSocket connection object
#   - game_id: the ID of the game (from the URL path)
#   - player_id: the ID of the player (from the query parameter)
@router.websocket("/websocket/ws/game/{game_id}")
async def game_websocket(
    websocket: WebSocket,
    game_id: int,
    player_id: int
):
    """WebSocket endpoint for game-specific connections"""
    try:
        await websocket.accept()
        
        # Validate game and player
        db = next(get_db())
        game = db.query(DBGame).filter(DBGame.id == game_id).first()
        if not game:
            await websocket.send_text(json.dumps({
                "type": "error",
                "data": {"message": "Game not found"},
                "timestamp": datetime.utcnow().isoformat()
            }))
            await websocket.close()
            return
        
        # Check if player is part of this game
        if game.player1_id != player_id and game.player2_id != player_id:
            await websocket.send_text(json.dumps({
                "type": "error",
                "data": {"message": "Player not part of this game"},
                "timestamp": datetime.utcnow().isoformat()
            }))
            await websocket.close()
            return
        
        # Connect to WebSocket manager
        await websocket_manager.connect(
            websocket,
            ConnectionType.GAME,
            game_id,
            {"player_id": player_id, "game_id": game_id}
        )
        
        # Send game state
        game_state = {
            "game_id": game_id,
            "current_turn": game.current_turn,
            "player1_pfh": game.player1_pfh,
            "player2_pfh": game.player2_pfh,
            "is_completed": game.is_completed,
            "winner_id": game.winner_id
        }
        
        game_msg = create_ws_message(
            WSMessageType.GAME_STATE_UPDATE,
            game_state
        )
        await websocket_manager.send_personal_message(websocket, game_msg)
        
        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle game-specific messages
                await handle_game_message(websocket, game_id, player_id, message, db)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                error_msg = create_ws_message(
                    WSMessageType.ERROR,
                    {"message": "Invalid JSON format"}
                )
                await websocket_manager.send_personal_message(websocket, error_msg)
            except Exception as e:
                logger.error(f"Error handling game message: {e}")
                error_msg = create_ws_message(
                    WSMessageType.ERROR,
                    {"message": "Internal server error"}
                )
                await websocket_manager.send_personal_message(websocket, error_msg)
    
    except Exception as e:
        logger.error(f"Game WebSocket error: {e}")
    finally:
        await websocket_manager.disconnect(websocket)
# This function defines a WebSocket endpoint for matchmaking at the route "/websocket/ws/matchmaking".
# When a client connects to this endpoint, the following steps occur:
#
# 1. The server accepts the WebSocket connection.
# 2. The connection is registered with the websocket_manager under the "MATCHMAKING" connection type.
# 3. A welcome message is sent to the client, indicating a successful connection to matchmaking.
# 4. The server enters a loop to continuously listen for incoming messages from the client:
#    - Each message is expected to be a JSON string, which is parsed.
#    - The parsed message is passed to the handle_matchmaking_message function for further processing.
#    - If the client disconnects (WebSocketDisconnect), the loop breaks and cleanup occurs.
#    - If the message is not valid JSON, an error message is sent back to the client.
#    - If any other exception occurs, an internal server error message is sent and the error is logged.
# 5. When the connection is closed or an error occurs, the server ensures the client is disconnected from the websocket_manager.

@router.websocket("/websocket/ws/matchmaking")
async def matchmaking_websocket(websocket: WebSocket):
    """WebSocket endpoint for matchmaking"""
    try:
        await websocket.accept()
        
        # Connect to WebSocket manager
        await websocket_manager.connect(websocket, ConnectionType.MATCHMAKING)
        
        # Send welcome message
        welcome_msg = create_ws_message(
            WSMessageType.MATCHMAKING_STATUS,
            {"message": "Connected to matchmaking"}
        )
        await websocket_manager.send_personal_message(websocket, welcome_msg)
        
        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle matchmaking messages
                await handle_matchmaking_message(websocket, message)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                error_msg = create_ws_message(
                    WSMessageType.ERROR,
                    {"message": "Invalid JSON format"}
                )
                await websocket_manager.send_personal_message(websocket, error_msg)
            except Exception as e:
                logger.error(f"Error handling matchmaking message: {e}")
                error_msg = create_ws_message(
                    WSMessageType.ERROR,
                    {"message": "Internal server error"}
                )
                await websocket_manager.send_personal_message(websocket, error_msg)
    
    except Exception as e:
        logger.error(f"Matchmaking WebSocket error: {e}")
    finally:
        await websocket_manager.disconnect(websocket)

@router.websocket("/websocket/ws/test")
async def websocket_test(websocket: WebSocket):
    print("websocket_test")
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except Exception:
        await websocket.close()

async def handle_player_message(websocket: WebSocket, player_id: int, 
                               message: Dict[str, Any], db: Session):
    """Handle incoming messages from player WebSocket"""
    message_type = message.get("type")
    data = message.get("data", {})
    
    if message_type == "ping":
        # Respond to ping
        pong_msg = create_ws_message(WSMessageType.PONG, {"player_id": player_id})
        await websocket_manager.send_personal_message(websocket, pong_msg)
    
    elif message_type == "player_action":
        # Handle player action (strategy submission, etc.)
        action = data.get("action")
        game_id = data.get("game_id")
        
        if action and game_id:
            # Process the action
            await process_player_action(player_id, game_id, action, db)
    
    else:
        # Unknown message type
        error_msg = create_ws_message(
            WSMessageType.ERROR,
            {"message": f"Unknown message type: {message_type}"}
        )
        await websocket_manager.send_personal_message(websocket, error_msg)

async def handle_game_message(websocket: WebSocket, game_id: int, player_id: int,
                             message: Dict[str, Any], db: Session):
    """Handle incoming messages from game WebSocket"""
    message_type = message.get("type")
    data = message.get("data", {})
    
    if message_type == "ping":
        # Respond to ping
        pong_msg = create_ws_message(WSMessageType.PONG, {
            "game_id": game_id,
            "player_id": player_id
        })
        await websocket_manager.send_personal_message(websocket, pong_msg)
    
    elif message_type == "turn_action":
        # Handle turn action submission
        strategy = data.get("strategy")
        sacrifice = data.get("sacrifice", False)
        
        if strategy:
            await process_turn_action(game_id, player_id, strategy, sacrifice, db)
    
    else:
        # Unknown message type
        error_msg = create_ws_message(
            WSMessageType.ERROR,
            {"message": f"Unknown message type: {message_type}"}
        )
        await websocket_manager.send_personal_message(websocket, error_msg)

async def handle_matchmaking_message(websocket: WebSocket, message: Dict[str, Any]):
    """Handle incoming messages from matchmaking WebSocket"""
    message_type = message.get("type")
    data = message.get("data", {})
    
    if message_type == "ping":
        # Respond to ping
        pong_msg = create_ws_message(WSMessageType.PONG, {"matchmaking": True})
        await websocket_manager.send_personal_message(websocket, pong_msg)
    
    elif message_type == "join_queue":
        # Handle joining matchmaking queue
        player_id = data.get("player_id")
        if player_id:
            # This would integrate with your existing matchmaking logic
            # For now, just acknowledge
            ack_msg = create_ws_message(
                WSMessageType.MATCHMAKING_JOIN,
                {"player_id": player_id, "status": "joined"}
            )
            await websocket_manager.send_personal_message(websocket, ack_msg)
    
    else:
        # Unknown message type
        error_msg = create_ws_message(
            WSMessageType.ERROR,
            {"message": f"Unknown message type: {message_type}"}
        )
        await websocket_manager.send_personal_message(websocket, error_msg)

async def process_player_action(player_id: int, game_id: int, action: str, db: Session):
    """Process a player action"""
    # This would integrate with your game logic
    # For now, just log the action
    logger.info(f"Player {player_id} performed action {action} in game {game_id}")
    
    # Notify other players in the game
    action_msg = create_ws_message(
        WSMessageType.PLAYER_ACTION,
        {
            "player_id": player_id,
            "game_id": game_id,
            "action": action
        }
    )
    await websocket_manager.send_to_game(game_id, action_msg)

async def process_turn_action(game_id: int, player_id: int, strategy: str, 
                             sacrifice: bool, db: Session):
    """Process a turn action submission"""
    # This would integrate with your turn processing logic
    # For now, just log the action
    logger.info(f"Player {player_id} submitted strategy {strategy} with sacrifice {sacrifice} in game {game_id}")
    
    # Notify other players in the game
    turn_msg = create_ws_message(
        WSMessageType.TURN_ACTION,
        {
            "game_id": game_id,
            "player_id": player_id,
            "strategy": strategy,
            "sacrifice": sacrifice
        }
    )
    await websocket_manager.send_to_game(game_id, turn_msg)

# HTTP endpoint to get WebSocket connection info (for debugging)
@router.get("/websocket/ws/connections")
async def get_connection_info():
    """Get information about current WebSocket connections"""
    return websocket_manager.get_connection_info()

@router.websocket("/ws/online-players")
async def online_players_websocket(websocket: WebSocket):
    """WebSocket endpoint for monitoring online players"""
    try:
        await websocket.accept()
        
        # Connect to WebSocket manager
        await websocket_manager.connect(websocket, ConnectionType.MATCHMAKING)
        
        # Send initial online players list
        online_players = await get_online_players_list()
        welcome_msg = create_ws_message(
            WSMessageType.ONLINE_PLAYERS_UPDATE,
            {
                "online_players": online_players,
                "total_count": len(online_players),
                "message": "Connected to online players monitor"
            }
        )
        await websocket_manager.send_personal_message(websocket, welcome_msg)
        
        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle online players monitoring messages
                await handle_online_players_message(websocket, message)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                error_msg = create_ws_message(
                    WSMessageType.ERROR,
                    {"message": "Invalid JSON format"}
                )
                await websocket_manager.send_personal_message(websocket, error_msg)
            except Exception as e:
                logger.error(f"Error handling online players message: {e}")
                error_msg = create_ws_message(
                    WSMessageType.ERROR,
                    {"message": "Internal server error"}
                )
                await websocket_manager.send_personal_message(websocket, error_msg)
    
    except Exception as e:
        logger.error(f"Online players WebSocket error: {e}")
    finally:
        await websocket_manager.disconnect(websocket)

async def handle_online_players_message(websocket: WebSocket, message: Dict[str, Any]):
    """Handle incoming messages from online players monitoring WebSocket"""
    message_type = message.get("type")
    data = message.get("data", {})
    
    if message_type == "ping":
        # Respond to ping
        pong_msg = create_ws_message(WSMessageType.PONG, {"online_players_monitor": True})
        await websocket_manager.send_personal_message(websocket, pong_msg)
    
    elif message_type == "refresh_online_players":
        # Send updated online players list
        online_players = await get_online_players_list()
        update_msg = create_ws_message(
            WSMessageType.ONLINE_PLAYERS_UPDATE,
            {
                "online_players": online_players,
                "total_count": len(online_players),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        await websocket_manager.send_personal_message(websocket, update_msg)
    
    else:
        # Unknown message type
        error_msg = create_ws_message(
            WSMessageType.ERROR,
            {"message": f"Unknown message type: {message_type}"}
        )
        await websocket_manager.send_personal_message(websocket, error_msg)

async def get_online_players_list():
    """Get list of currently online players"""
    try:
        # Get online players from WebSocket manager
        online_players = []
        
        # Get connected players from the websocket manager
        for player_id, websocket in websocket_manager.player_connections.items():
            # Get player metadata
            metadata = websocket_manager.connection_metadata.get(websocket, {})
            player_name = metadata.get("player_name", f"Player {player_id}")
            connected_at = metadata.get("connected_at")
            
            online_players.append({
                "player_id": player_id,
                "player_name": player_name,
                "connected_at": connected_at.isoformat() if connected_at else None,
                "connection_type": "player"
            })
        
        # Sort by connection time (most recent first)
        online_players.sort(key=lambda x: x["connected_at"] or "", reverse=True)
        
        return online_players
        
    except Exception as e:
        logger.error(f"Error getting online players list: {e}")
        return []

@router.get("/ws/online-players")
async def get_online_players_endpoint():
    """Get list of currently online players via HTTP"""
    online_players = await get_online_players_list()
    return {
        "online_players": online_players,
        "total_count": len(online_players),
        "timestamp": datetime.utcnow().isoformat()
    }

async def get_comprehensive_online_users():
    """Get comprehensive list of online users including authenticated users and WebSocket connections"""
    try:
        online_users = []
        
        # 1. Get WebSocket connected players
        for player_id, websocket in websocket_manager.player_connections.items():
            metadata = websocket_manager.connection_metadata.get(websocket, {})
            player_name = metadata.get("player_name", f"Player {player_id}")
            connected_at = metadata.get("connected_at")
            
            online_users.append({
                "user_id": player_id,
                "user_name": player_name,
                "email": "N/A",  # We'll try to get this from DB
                "connection_type": "websocket",
                "connected_at": connected_at.isoformat() if connected_at else None,
                "status": "websocket_connected"
            })
        
        # 2. Get authenticated users (you'll need to implement session tracking)
        # This is a placeholder - you'd need to implement proper session management
        
        # 3. Get recent database activity (users who logged in recently)
        try:
            from ..database import get_db
            db = next(get_db())
            
            # Get recent players from database (this is a basic example)
            recent_players = db.query(DBPlayer).filter(
                DBPlayer.last_played.isnot(None)
            ).order_by(DBPlayer.last_played.desc()).limit(10).all()
            
            for player in recent_players:
                # Check if already in WebSocket connections
                if not any(user["user_id"] == player.id for user in online_users):
                    online_users.append({
                        "user_id": player.id,
                        "user_name": player.name,
                        "email": "N/A",  # Add email field to DBPlayer if needed
                        "connection_type": "database",
                        "connected_at": player.last_played.isoformat() if player.last_played else None,
                        "status": "recently_active"
                    })
            
        except Exception as e:
            logger.error(f"Error getting database users: {e}")
        
        # Sort by connection time (most recent first)
        online_users.sort(key=lambda x: x["connected_at"] or "", reverse=True)
        
        return online_users
        
    except Exception as e:
        logger.error(f"Error getting comprehensive online users: {e}")
        return []

@router.get("/websocket/ws/comprehensive-online-users")
async def get_comprehensive_online_users_endpoint():
    """Get comprehensive list of online users including authenticated and WebSocket connected users"""
    online_users = await get_comprehensive_online_users()
    return {
        "online_users": online_users,
        "total_count": len(online_users),
        "websocket_connections": len(websocket_manager.player_connections),
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/websocket/ws/debug-connections")
async def debug_websocket_connections():
    """Debug endpoint to see all current WebSocket connections"""
    return {
        "player_connections": list(websocket_manager.player_connections.keys()),
        "game_connections": {game_id: len(connections) for game_id, connections in websocket_manager.game_connections.items()},
        "matchmaking_connections": len(websocket_manager.matchmaking_connections),
        "connection_metadata": {
            str(id(ws)): {
                "type": metadata.get("type"),
                "identifier": metadata.get("identifier"),
                "connected_at": metadata.get("connected_at").isoformat() if metadata.get("connected_at") else None
            }
            for ws, metadata in websocket_manager.connection_metadata.items()
        }
    }