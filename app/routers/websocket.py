import json
import logging
from typing import Optional, Dict, Any, Tuple
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone
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
        try:
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
        finally:
            db.close()
        
        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                # Ouvre une session DB pour chaque message
                with next(get_db()) as db_msg:
                    await handle_player_message(websocket, player_id, message, db_msg)

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
    # db.close() should not be here; already handled in the inner finally block
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
        try:
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
        finally:
            db.close()
        
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
    # db.close() should not be here; already handled in the inner finally block
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

@router.websocket("/ws/matchmaking")
async def matchmaking_websocket(websocket: WebSocket, player_id: Optional[int] = Query(None)):
    """WebSocket endpoint for matchmaking"""
    try:
        await websocket.accept()
        
        # Connect to WebSocket manager
        await websocket_manager.connect(websocket, ConnectionType.MATCHMAKING)
        
        # Validate player_id if provided
        if player_id is not None:
            try:
                # Check if player exists in database
                db = next(get_db())
                try:
                    player = db.query(DBPlayer).filter(DBPlayer.id == player_id).first()
                    if not player:
                        error_msg = create_ws_message(
                            WSMessageType.ERROR,
                            {"message": f"Player with ID {player_id} not found in database"}
                        )
                        await websocket_manager.send_personal_message(websocket, error_msg)
                        await websocket_manager.disconnect(websocket)
                        return
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Database error validating player {player_id}: {e}")
                error_msg = create_ws_message(
                    WSMessageType.ERROR,
                    {"message": "Database error while validating player"}
                )
                await websocket_manager.send_personal_message(websocket, error_msg)
                await websocket_manager.disconnect(websocket)
                return
        
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
    # db.close() should not be here; already handled in the inner finally block
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
    # Refactor to reduce complexity and remove redundant returns
    message_type = message.get("type")
    data = message.get("data", {})

    if message_type == "invite_player":
        opponent_id = data.get("opponent_id")
        player_id = data.get("player_id")
        if not opponent_id or not player_id:
            error_msg = create_ws_message(
                WSMessageType.ERROR,
                {"message": "Missing opponent_id or player_id for invitation"}
            )
            await websocket_manager.send_personal_message(websocket, error_msg)
            return

        opponent_ws = None
        for pid, ws, _ in matchmaking_queue:
            if pid == opponent_id:
                opponent_ws = ws
                break

        if not opponent_ws:
            ws_list = websocket_manager.player_connections.get(opponent_id)
            if ws_list:
                opponent_ws = ws_list[0]

        if opponent_ws:
            invite_msg = create_ws_message(
                WSMessageType.MATCHMAKING_STATUS,
                {
                    "type": "invitation_received",
                    "from_player_id": player_id,
                    "message": f"You have received a match invitation from player {player_id}"
                }
            )
            await websocket_manager.send_personal_message(opponent_ws, invite_msg)
        else:
            error_msg = create_ws_message(
                WSMessageType.ERROR,
                {"message": "Opponent not connected"}
            )
            await websocket_manager.send_personal_message(websocket, error_msg)

    elif message_type == "accept_invitation":
        opponent_id = data.get("opponent_id")
        player_id = data.get("player_id")
        if not opponent_id or not player_id:
            error_msg = create_ws_message(
                WSMessageType.ERROR,
                {"message": "Missing opponent_id or player_id for accept_invitation"}
            )
            await websocket_manager.send_personal_message(websocket, error_msg)
            return

        try:
            game_id = await create_new_game(player_id, opponent_id)
            accepted_msg = create_ws_message(
                WSMessageType.MATCHMAKING_STATUS,
                {
                    "type": "invitation_accepted",
                    "from_player_id": player_id,
                    "game_id": game_id,
                    "message": f"Player {player_id} accepted your invitation. Game {game_id} can start."
                }
            )
            opponent_ws = websocket_manager.player_connections.get(opponent_id, [None])[0]
            if opponent_ws:
                await websocket_manager.send_personal_message(opponent_ws, accepted_msg)
            await websocket_manager.send_personal_message(websocket, accepted_msg)

            await remove_player_from_queue(player_id)
            await remove_player_from_queue(opponent_id)

        except Exception as e:
            logger.error(f"Error creating game after invitation acceptance: {e}")
            error_msg = create_ws_message(
                WSMessageType.ERROR,
                {"message": "Failed to create game after invitation acceptance."}
            )
            await websocket_manager.send_personal_message(websocket, error_msg)

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
            db.close()
        except Exception as e:
            logger.error(f"Database error when joining queue: {e}")
            error_msg = create_ws_message(
                WSMessageType.ERROR,
                {"message": "Database error"}
            )
            await websocket_manager.send_personal_message(websocket, error_msg)
            return
        
        # Add to queue
        joined_at = datetime.now(timezone.utc)
        players_in_queue.add(player_id)
        matchmaking_queue.append((player_id, websocket, joined_at))
        queue_metadata[player_id] = {
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

    elif message_type == "get_opponent_players":
        # Handle request for opponent players (queue and connected users)
        try:
            db = next(get_db())
            # Get queue users with full info
            queue_users = []
            for i, (player_id, ws, joined_at) in enumerate(matchmaking_queue):
                player = db.query(DBPlayer).filter(DBPlayer.id == player_id).first()
                if player:
                    waiting_time = (datetime.now(timezone.utc) - joined_at).total_seconds() if joined_at else 0
                    queue_users.append({
                        "player_id": player.id,
                        "name": player.name,
                        "position": i + 1,
                        "waiting_time_seconds": int(waiting_time),
                        "waiting_time_formatted": f"{int(waiting_time // 60)}m {int(waiting_time % 60)}s",
                        "status": "in_queue"
                    })
            # Get connected users (excluding those in queue)
            connected_users = []
            for player_id, ws_list in websocket_manager.player_connections.items():
                if player_id not in players_in_queue:
                    player = db.query(DBPlayer).filter(DBPlayer.id == player_id).first()
                    if player:
                        connected_users.append({
                            "player_id": player.id,
                            "name": player.name,
                            "connection_count": len(ws_list),
                            "status": "connected"
                        })
            # Send response
            response_msg = create_ws_message(
                WSMessageType.MATCHMAKING_STATUS,
                {
                    "type": "opponent_players_response",
                    "data": {
                        "queue_users": queue_users,
                        "connected_users": connected_users,
                        "summary": {
                            "total_in_queue": len(queue_users),
                            "total_connected": len(connected_users),
                            "total_websocket_connections": len(websocket_manager.player_connections)
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
            await websocket_manager.send_personal_message(websocket, response_msg)
            db.close()
        except Exception as e:
            logger.error(f"Error getting opponent players: {e}")
            error_msg = create_ws_message(
                WSMessageType.ERROR,
                {"message": "Failed to retrieve opponent players"}
            )
            await websocket_manager.send_personal_message(websocket, error_msg)
    
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
    
    elif message_type == "get_online_players":
        # Handle request for online players information
        try:
            db = next(get_db())
            
            # Get queue users with full info
            queue_users = []
            for i, (player_id, ws, joined_at) in enumerate(matchmaking_queue):
                player = db.query(DBPlayer).filter(DBPlayer.id == player_id).first()
                if player:
                    waiting_time = (datetime.now(timezone.utc) - joined_at).total_seconds() if joined_at else 0
                    queue_users.append({
                        "player_id": player.id,
                        "name": player.name,
                        "position": i + 1,
                        "waiting_time_seconds": int(waiting_time),
                        "waiting_time_formatted": f"{int(waiting_time // 60)}m {int(waiting_time % 60)}s",
                        "status": "in_queue"
                    })
            
            # Get connected users (excluding those in queue)
            connected_users = []
            for player_id, ws_list in websocket_manager.player_connections.items():
                if player_id not in players_in_queue:
                    player = db.query(DBPlayer).filter(DBPlayer.id == player_id).first()
                    if player:
                        connected_users.append({
                            "player_id": player.id,
                            "name": player.name,
                            "connection_count": len(ws_list),
                            "status": "connected"
                        })
            
            # Send response
            response_msg = create_ws_message(
                WSMessageType.MATCHMAKING_STATUS,
                {
                    "type": "online_players_response",
                    "data": {
                        "queue_users": queue_users,
                        "connected_users": connected_users,
                        "summary": {
                            "total_in_queue": len(queue_users),
                            "total_connected": len(connected_users),
                            "total_websocket_connections": len(websocket_manager.player_connections)
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
            await websocket_manager.send_personal_message(websocket, response_msg)
            db.close()
        except Exception as e:
            logger.error(f"Error getting online players: {e}")
            error_msg = create_ws_message(
                WSMessageType.ERROR,
                {"message": "Failed to retrieve online players"}
            )
            await websocket_manager.send_personal_message(websocket, error_msg)
    
    elif message_type == "get_queue_status":
        # Handle request for current queue status
        queue_status_msg = create_ws_message(
            WSMessageType.MATCHMAKING_STATUS,
            {
                "type": "queue_status_response",
                "data": {
                    "queue_size": len(matchmaking_queue),
                    "players_in_queue": len(players_in_queue),
                    "queue_active": len(matchmaking_queue) > 0,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
        await websocket_manager.send_personal_message(websocket, queue_status_msg)
        
    elif message_type == "heartbeat":
        # Handle heartbeat/keepalive messages
        heartbeat_msg = create_ws_message(
            WSMessageType.PONG,
            {
                "type": "heartbeat_response",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        await websocket_manager.send_personal_message(websocket, heartbeat_msg)
    
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
    """Try to match players in the queue - notify players for invitation"""
    if len(matchmaking_queue) >= 2:
        # Get two players from the queue
        player1_id, player1_ws, joined_at1 = matchmaking_queue.popleft()
        player2_id, player2_ws, joined_at2 = matchmaking_queue.popleft()

        # Notify player1 to invite player2
        invite_msg_p1 = create_ws_message(
            WSMessageType.MATCHMAKING_STATUS,
            {
                "type": "match_possible",
                "player_id": player1_id,
                "opponent_id": player2_id,
                "message": f"You can invite Player {player2_id} to start a game."
            }
        )
        await websocket_manager.send_personal_message(player1_ws, invite_msg_p1)

        # Notify player2 that they are waiting for an invitation
        waiting_msg_p2 = create_ws_message(
            WSMessageType.MATCHMAKING_STATUS,
            {
                "type": "waiting_for_invitation",
                "player_id": player2_id,
                "opponent_id": player1_id,
                "message": f"Waiting for Player {player1_id} to invite you to a game."
            }
        )
        await websocket_manager.send_personal_message(player2_ws, waiting_msg_p2)

        # Keep players in queue until invitation is accepted
        matchmaking_queue.appendleft((player2_id, player2_ws, joined_at2))
        matchmaking_queue.appendleft((player1_id, player1_ws, joined_at1))