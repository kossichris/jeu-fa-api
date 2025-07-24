import json
import logging
from typing import Optional, Dict, Any, Tuple
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from collections import deque
import asyncio

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

# Global matchmaking queue management
matchmaking_queue = deque()  # Queue of (player_id, websocket, timestamp) tuples
players_in_queue = set()  # Set of player_ids currently in queue
queue_metadata = {}  # player_id -> {websocket, joined_at, player_name}

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
async def matchmaking_websocket(websocket: WebSocket, player_id: int = None):
    """WebSocket endpoint for matchmaking"""
    try:
        await websocket.accept()
        
        # Connect to WebSocket manager
        await websocket_manager.connect(websocket, ConnectionType.MATCHMAKING)
        
        # Check if player is already in matchmaking queue from previous session
        is_already_in_queue = player_id and player_id in players_in_queue
        
        # Send welcome message
        welcome_msg = create_ws_message(
            WSMessageType.MATCHMAKING_STATUS,
            {
                "message": "Connected to matchmaking",
                "in_queue": is_already_in_queue,
                "player_id": player_id,
                "queue_size": len(matchmaking_queue)
            }
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
                # Clean up player from queue on disconnect
                await cleanup_player_from_queue(websocket, player_id)
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
        await cleanup_player_from_queue(websocket, player_id)

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
        player_id = data.get("player_id")
        if not player_id:
            error_msg = create_ws_message(
                WSMessageType.ERROR,
                {"message": "player_id is required to join queue"}
            )
            await websocket_manager.send_personal_message(websocket, error_msg)
            return
            
        # Check if already in queue
        if player_id in players_in_queue:
            ack_msg = create_ws_message(
                WSMessageType.MATCHMAKING_STATUS,
                {
                    "player_id": player_id,
                    "status": "already_in_queue",
                    "in_queue": True,
                    "queue_position": get_queue_position(player_id),
                    "message": "Already in matchmaking queue"
                }
            )
            await websocket_manager.send_personal_message(websocket, ack_msg)
            return
        
        # Get player info from database
        try:
            db = next(get_db())
            player = db.query(DBPlayer).filter(DBPlayer.id == player_id).first()
            if not player:
                error_msg = create_ws_message(
                    WSMessageType.ERROR,
                    {"message": "Player not found in database"}
                )
                await websocket_manager.send_personal_message(websocket, error_msg)
                return
        except Exception as e:
            logger.error(f"Database error when joining queue: {e}")
            error_msg = create_ws_message(
                WSMessageType.ERROR,
                {"message": "Database error"}
            )
            await websocket_manager.send_personal_message(websocket, error_msg)
            return
        
        # Add to queue
        joined_at = datetime.utcnow()
        players_in_queue.add(player_id)
        matchmaking_queue.append((player_id, websocket, joined_at))
        queue_metadata[player_id] = {
            "websocket": websocket,
            "joined_at": joined_at,
            "player_name": player.name
        }
        
        # Send confirmation
        ack_msg = create_ws_message(
            WSMessageType.MATCHMAKING_STATUS,
            {
                "player_id": player_id,
                "status": "joined",
                "in_queue": True,
                "queue_position": len(matchmaking_queue),
                "queue_size": len(matchmaking_queue),
                "message": f"Joined matchmaking queue as {player.name}"
            }
        )
        await websocket_manager.send_personal_message(websocket, ack_msg)
        
        logger.info(f"Player {player_id} ({player.name}) joined matchmaking queue")
        
        # Try to find a match
        await try_match_players()
    
    elif message_type == "leave_queue":
        player_id = data.get("player_id")
        if player_id and player_id in players_in_queue:
            await remove_player_from_queue(player_id)
            
            ack_msg = create_ws_message(
                WSMessageType.MATCHMAKING_STATUS,
                {
                    "player_id": player_id,
                    "status": "left",
                    "in_queue": False,
                    "message": "Left matchmaking queue"
                }
            )
            await websocket_manager.send_personal_message(websocket, ack_msg)
            logger.info(f"Player {player_id} left matchmaking queue")
    
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

async def try_match_players():
    """Try to match players in the queue - automatically called when players join"""
    if len(matchmaking_queue) >= 2:
        # Get two players from the queue
        player1_id, player1_ws, joined_at1 = matchmaking_queue.popleft()
        player2_id, player2_ws, joined_at2 = matchmaking_queue.popleft()
        
        # Remove from tracking structures
        players_in_queue.discard(player1_id)
        players_in_queue.discard(player2_id)
        queue_metadata.pop(player1_id, None)
        queue_metadata.pop(player2_id, None)
        
        try:
            # Create a new game
            game_id = await create_new_game(player1_id, player2_id)
            
            # Get player names
            player1_name = queue_metadata.get(player1_id, {}).get("player_name", f"Player {player1_id}")
            player2_name = queue_metadata.get(player2_id, {}).get("player_name", f"Player {player2_id}")
            
            # Notify both players
            match_msg_p1 = create_ws_message(
                WSMessageType.MATCHMAKING_STATUS,
                {
                    "player_id": player1_id,
                    "opponent_id": player2_id,
                    "opponent_name": player2_name,
                    "game_id": game_id,
                    "status": "match_found",
                    "in_queue": False,
                    "message": f"Match found! Playing against {player2_name}"
                }
            )
            
            match_msg_p2 = create_ws_message(
                WSMessageType.MATCHMAKING_STATUS,
                {
                    "player_id": player2_id,
                    "opponent_id": player1_id,
                    "opponent_name": player1_name,
                    "game_id": game_id,
                    "status": "match_found",
                    "in_queue": False,
                    "message": f"Match found! Playing against {player1_name}"
                }
            )
            
            await websocket_manager.send_personal_message(player1_ws, match_msg_p1)
            await websocket_manager.send_personal_message(player2_ws, match_msg_p2)
            
            logger.info(f"Matched players {player1_id} and {player2_id} in game {game_id}")
            
        except Exception as e:
            logger.error(f"Error creating match: {e}")
            # Put players back in queue on error
            matchmaking_queue.appendleft((player1_id, player1_ws, joined_at1))
            matchmaking_queue.appendleft((player2_id, player2_ws, joined_at2))
            players_in_queue.add(player1_id)
            players_in_queue.add(player2_id)
            
            # Restore metadata
            if player1_id not in queue_metadata:
                queue_metadata[player1_id] = {
                    "websocket": player1_ws,
                    "joined_at": joined_at1,
                    "player_name": player1_name
                }
            if player2_id not in queue_metadata:
                queue_metadata[player2_id] = {
                    "websocket": player2_ws,
                    "joined_at": joined_at2,
                    "player_name": player2_name
                }
            
            # Notify players of error
            error_msg = create_ws_message(
                WSMessageType.ERROR,
                {"message": "Failed to create match. You remain in queue."}
            )
            await websocket_manager.send_personal_message(player1_ws, error_msg)
            await websocket_manager.send_personal_message(player2_ws, error_msg)

async def create_new_game(player1_id: int, player2_id: int) -> int:
    """Create a new game between two players"""
    try:
        db = next(get_db())
        
        # Create new game record
        new_game = DBGame(
            player1_id=player1_id,
            player2_id=player2_id,
            current_turn=1,
            player1_pfh=100,  # Starting health
            player2_pfh=100,  # Starting health
            is_completed=False,
            created_at=datetime.utcnow()
        )
        
        db.add(new_game)
        db.commit()
        db.refresh(new_game)
        
        logger.info(f"Created new game {new_game.id} between players {player1_id} and {player2_id}")
        return new_game.id
        
    except Exception as e:
        logger.error(f"Error creating new game: {e}")
        raise

async def remove_player_from_queue(player_id: int):
    """Remove a player from the matchmaking queue"""
    if player_id in players_in_queue:
        players_in_queue.discard(player_id)
        queue_metadata.pop(player_id, None)
        
        # Remove from deque (this is inefficient for large queues but works for small ones)
        new_queue = deque()
        for pid, ws, joined_at in matchmaking_queue:
            if pid != player_id:
                new_queue.append((pid, ws, joined_at))
        matchmaking_queue.clear()
        matchmaking_queue.extend(new_queue)

async def cleanup_player_from_queue(websocket: WebSocket, player_id: Optional[int]):
    """Clean up player from queue when they disconnect"""
    if player_id and player_id in players_in_queue:
        await remove_player_from_queue(player_id)
        logger.info(f"Cleaned up player {player_id} from matchmaking queue on disconnect")

def get_queue_position(player_id: int) -> int:
    """Get the position of a player in the queue (1-indexed)"""
    for i, (pid, _, _) in enumerate(matchmaking_queue):
        if pid == player_id:
            return i + 1
    return -1

# Add endpoint to check queue status
@router.get("/websocket/ws/queue-status")
async def get_queue_status():
    """Get current matchmaking queue status"""
    queue_details = []
    for player_id, websocket, joined_at in matchmaking_queue:
        metadata = queue_metadata.get(player_id, {})
        queue_details.append({
            "player_id": player_id,
            "player_name": metadata.get("player_name", f"Player {player_id}"),
            "joined_at": joined_at.isoformat() if joined_at else None,
            "waiting_time_seconds": (datetime.utcnow() - joined_at).total_seconds() if joined_at else 0
        })
    
    return {
        "players_in_queue": len(players_in_queue),
        "queue_size": len(matchmaking_queue),
        "queue_details": queue_details,
        "timestamp": datetime.utcnow().isoformat()
    }

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

# Debug endpoints for matchmaking
@router.get("/websocket/ws/debug-queue")
async def debug_matchmaking_queue():
    """Debug endpoint to see detailed queue information"""
    queue_items = []
    for i, (player_id, websocket, joined_at) in enumerate(matchmaking_queue):
        metadata = queue_metadata.get(player_id, {})
        queue_items.append({
            "position": i + 1,
            "player_id": player_id,
            "player_name": metadata.get("player_name", f"Player {player_id}"),
            "joined_at": joined_at.isoformat() if joined_at else None,
            "waiting_time_seconds": (datetime.utcnow() - joined_at).total_seconds() if joined_at else 0,
            "websocket_id": str(id(websocket))
        })
    
    return {
        "total_players_in_queue": len(players_in_queue),
        "queue_size": len(matchmaking_queue),
        "players_set": list(players_in_queue),
        "queue_items": queue_items,
        "metadata_count": len(queue_metadata),
        "timestamp": datetime.utcnow().isoformat()
    }

@router.post("/websocket/ws/debug-force-match")
async def debug_force_match():
    """Debug endpoint to force a match between queued players"""
    if len(matchmaking_queue) >= 2:
        await try_match_players()
        return {"message": "Forced match attempt completed", "remaining_in_queue": len(matchmaking_queue)}
    else:
        return {"message": "Not enough players in queue", "players_in_queue": len(matchmaking_queue)}