import json
import logging
from typing import Optional, Dict, Any, Tuple
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from collections import deque
import asyncio

from typing import Any, Dict, Optional, List, Tuple
from datetime import datetime, timezone
from fastapi import WebSocket

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
    print(f"Player {player_id} connected to matchmaking")
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
                break
            except json.JSONDecodeError:
                error_msg = create_ws_message(
                    WSMessageType.ERROR,
                    {"message": "Invalid JSON format"}
                )
                await websocket_manager.send_personal_message(websocket, error_msg)
            except Exception as e:
                print(f"Error handling matchmaking message: {e}")
                logger.error(f"Error handling matchmaking message: {e}", exc_info=True)
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

# ---------- helpers

async def _create_game_internal(player1_id: int, player2_id: int) -> int:
    """Internal function to create a new game between two players"""
    try:
        for db in _db_session():
            # Verify both players exist
            player1 = db.query(DBPlayer).filter(DBPlayer.id == player1_id).first()
            player2 = db.query(DBPlayer).filter(DBPlayer.id == player2_id).first()
            
            if not player1 or not player2:
                raise ValueError(f"One or both players not found: {player1_id}, {player2_id}")
            
            # Create new game
            new_game = DBGame(
                player1_id=player1_id,
                player2_id=player2_id,
                current_turn=player1_id,  # Player 1 starts
                player1_pfh=30,  # Initial PFH
                player2_pfh=30,  # Initial PFH
                is_completed=False
            )
            
            db.add(new_game)
            db.commit()
            db.refresh(new_game)
            
            logger.info(f"Created new game {new_game.id} between players {player1_id} and {player2_id}")
            return new_game.id
            
    except Exception as e:
        logger.error(f"Error creating internal game: {e}", exc_info=True)
        raise

async def _send_error(ws: WebSocket, message: str) -> None:
    await websocket_manager.send_personal_message(
        ws,
        create_ws_message(WSMessageType.ERROR, {"message": message})
    )

def _now_iso() -> str:
    return datetime.utcnow().isoformat()

def _get_opponent_ws(opponent_id) -> Optional[WebSocket]:
    """Get opponent WebSocket connection by ID (handles both int and str)"""
    # Convert to int if it's a string, or use as-is if it's already int
    try:
        opponent_id_int = int(opponent_id) if isinstance(opponent_id, str) else opponent_id
    except (ValueError, TypeError):
        return None
        
    # 1) try queue
    for pid, ws, _ in matchmaking_queue:
        if pid == opponent_id_int:
            return ws
    
    # 2) try active connections - the websocket manager might use int or str keys
    ws_list = websocket_manager.player_connections.get(opponent_id_int)
    if not ws_list:
        # Try with string key
        ws_list = websocket_manager.player_connections.get(str(opponent_id_int))
    
    print(f"Active WebSocket connections for {opponent_id_int}: {ws_list}")
    if ws_list and isinstance(ws_list, list) and len(ws_list) > 0:
        return ws_list[0]
    return None

def _db_session():
    # tiny helper so we always close
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

def _fetch_player(db, player_id: str) -> Optional[DBPlayer]:
    return db.query(DBPlayer).filter(DBPlayer.id == player_id).first()

def _format_waiting(joined_at: Optional[datetime]) -> Tuple[int, str]:
    if not joined_at:
        return 0, "0m 0s"
    waiting = int((datetime.now(timezone.utc) - joined_at).total_seconds())
    return waiting, f"{waiting // 60}m {waiting % 60}s"

def get_queue_position(player_id: int) -> int:
    """Get the position of a player in the matchmaking queue."""
    for index, (pid, _ws, _joined_at) in enumerate(matchmaking_queue):
        if pid == player_id:
            return index + 1  # Position is 1-based
    return -1  # Return -1 if the player is not in the queue

def _build_queue_users(db) -> List[Dict[str, Any]]:
    users = []
    for i, (pid, _ws, joined_at) in enumerate(matchmaking_queue):
        p = _fetch_player(db, pid)
        if p:
            secs, fmt = _format_waiting(joined_at)
            user_data = {
                "player_id": p.id,
                "name": p.name,
                "position": i + 1,
                "waiting_time_seconds": secs,
                "waiting_time_formatted": fmt,
                "status": "in_queue"
            }
            users.append(user_data)
            logger.info(f"Queue user data: {user_data}")
    logger.info(f"Total users in queue: {len(users)}")
    return users

def _build_connected_users(db) -> List[Dict[str, Any]]:
    users = []
    for pid, ws_list in websocket_manager.player_connections.items():
        if pid in players_in_queue:
            continue
        p = _fetch_player(db, pid)
        if p:
            users.append({
                "player_id": p.id,
                "name": p.name,
                "connection_count": len(ws_list),
                "status": "connected"
            })
    return users

async def _send(ws: WebSocket, type_: WSMessageType, payload: Dict[str, Any]) -> None:
    await websocket_manager.send_personal_message(ws, create_ws_message(type_, payload))

# ---------- individual handlers

async def _handle_invite_player(ws: WebSocket, data: Dict[str, Any]) -> None:
    opponent_id = data.get("opponent_id")
    player_id = data.get("player_id")
    if not opponent_id or not player_id:
        return await _send_error(ws, "Missing opponent_id or player_id for invitation")

    opponent_ws = _get_opponent_ws(opponent_id)
    print(f"Opponent WebSocket: {opponent_ws}, {opponent_id}")

    if not opponent_ws:
        return await _send_error(ws, "Opponent not connected")

    invite_msg = {
        "type": "invitation_received",
        "from_player_id": player_id,
        "message": f"You have received a match invitation from player {player_id}"
    }
    await _send(opponent_ws, WSMessageType.MATCHMAKING_STATUS, invite_msg)

async def _handle_accept_invitation(ws: WebSocket, data: Dict[str, Any]) -> None:
    opponent_id = data.get("opponent_id")
    player_id = data.get("player_id")
    if not opponent_id or not player_id:
        return await _send_error(ws, "Missing opponent_id or player_id for accept_invitation")

    try:
        # Create a new game in the database
        game_id = await _create_game_internal(player_id, opponent_id)
        
        payload = {
            "type": "invitation_accepted",
            "from_player_id": player_id,
            "game_id": game_id,
            "message": f"Player {player_id} accepted your invitation. Game {game_id} can start."
        }

        # Get opponent's WebSocket connection safely
        opponent_ws = _get_opponent_ws(str(opponent_id))
        if opponent_ws:
            await _send(opponent_ws, WSMessageType.MATCHMAKING_STATUS, payload)

        await _send(ws, WSMessageType.MATCHMAKING_STATUS, payload)

        # Remove both players from queue (these are synchronous calls)
        remove_player_from_queue(player_id)
        remove_player_from_queue(opponent_id)

    except Exception as e:
        logger.error(f"Error creating game after invitation acceptance: {e}", exc_info=True)
        await _send_error(ws, "Failed to create game after invitation acceptance.")

async def _handle_join_queue(ws: WebSocket, data: Dict[str, Any]) -> None:
    player_id = data.get("player_id")
    if not player_id:
        return await _send_error(ws, "player_id is required to join queue")

    if player_id in players_in_queue:
        return await _send(
            ws,
            WSMessageType.MATCHMAKING_STATUS,
            {
                "player_id": player_id,
                "status": "already_in_queue",
                "in_queue": True,
                "queue_position": get_queue_position(player_id),
                "message": "Already in matchmaking queue"
            },
        )

    try:
        for db in _db_session():
            player = _fetch_player(db, player_id)
            if not player:
                return await _send_error(ws, "Player not found in database")
    except Exception as e:
        logger.error(f"Database error when joining queue: {e}")
        return await _send_error(ws, "Database error")

    joined_at = datetime.now(timezone.utc)
    players_in_queue.add(player_id)
    matchmaking_queue.append((player_id, ws, joined_at))
    queue_metadata[player_id] = {"joined_at": joined_at, "player_name": player.name}

    await _send(
        ws,
        WSMessageType.MATCHMAKING_STATUS,
        {
            "player_id": player_id,
            "status": "joined",
            "in_queue": True,
            "queue_position": len(matchmaking_queue),
            "queue_size": len(matchmaking_queue),
            "message": f"Joined matchmaking queue as {player.name}",
        },
    )
    logger.info(f"Player {player_id} ({player.name}) joined matchmaking queue")

    await try_match_players()

async def _handle_get_opponent_players(ws: WebSocket, _data: Dict[str, Any]) -> None:
    try:
        for db in _db_session():
            queue_users = _build_queue_users(db)
            connected_users = _build_connected_users(db)

        await _send(
            ws,
            WSMessageType.MATCHMAKING_STATUS,
            {
                "type": "opponent_players_response",
                "data": {
                    "queue_users": queue_users,
                    "connected_users": connected_users,
                    "summary": {
                        "total_in_queue": len(queue_users),
                        "total_connected": len(connected_users),
                        "total_websocket_connections": len(websocket_manager.player_connections),
                    },
                    "timestamp": _now_iso(),
                },
            },
        )
    except Exception as e:
        logger.error(f"Error getting opponent players: {e}")
        await _send_error(ws, "Failed to retrieve opponent players")

async def _handle_leave_queue(ws: WebSocket, data: Dict[str, Any]) -> None:
    player_id = data.get("player_id")
    if player_id and player_id in players_in_queue:
        remove_player_from_queue(player_id)  # Removed `await` since the function is synchronous
        await _send(
            ws,
            WSMessageType.MATCHMAKING_STATUS,
            {
                "player_id": player_id,
                "status": "left",
                "in_queue": False,
                "message": "Left matchmaking queue",
            },
        )
        logger.info(f"Player {player_id} left matchmaking queue")

async def _handle_get_online_players(ws: WebSocket, _data: Dict[str, Any]) -> None:
    try:
        for db in _db_session():
            queue_users = _build_queue_users(db)
            connected_users = _build_connected_users(db)

        await _send(
            ws,
            WSMessageType.MATCHMAKING_STATUS,
            {
                "type": "online_players_response",
                "data": {
                    "queue_users": queue_users,
                    "connected_users": connected_users,
                    "summary": {
                        "total_in_queue": len(queue_users),
                        "total_connected": len(connected_users),
                        "total_websocket_connections": len(websocket_manager.player_connections),
                    },
                    "timestamp": _now_iso(),
                },
            },
        )
    except Exception as e:
        logger.error(f"Error getting online players: {e}")
        await _send_error(ws, "Failed to retrieve online players")

async def _handle_get_queue_status(ws: WebSocket, _data: Dict[str, Any]) -> None:
    await _send(
        ws,
        WSMessageType.MATCHMAKING_STATUS,
        {
            "type": "queue_status_response",
            "data": {
                "queue_size": len(matchmaking_queue),
                "players_in_queue": len(players_in_queue),
                "queue_active": len(matchmaking_queue) > 0,
                "timestamp": _now_iso(),
            },
        },
    )

async def _handle_heartbeat(ws: WebSocket, _data: Dict[str, Any]) -> None:
    await _send(
        ws,
        WSMessageType.PONG,
        {"type": "heartbeat_response", "timestamp": _now_iso()},
    )

async def _handle_unknown(ws: WebSocket, message_type: Any) -> None:
    await _send_error(ws, f"Unknown message type: {message_type}")

# ---------- dispatcher

HANDLERS = {
    "invite_player": _handle_invite_player,
    "accept_invitation": _handle_accept_invitation,
    "join_queue": _handle_join_queue,
    "get_opponent_players": _handle_get_opponent_players,
    "leave_queue": _handle_leave_queue,
    "get_online_players": _handle_get_online_players,
    "get_queue_status": _handle_get_queue_status,
    "heartbeat": _handle_heartbeat,
}

async def handle_matchmaking_message(websocket: WebSocket, message: Dict[str, Any]):
    message_type = message.get("type")
    data = message.get("data", {}) or {}
    print(f"Handling matchmaking message: {message_type}, {data}")

    handler = HANDLERS.get(message_type)
    if handler:
        await handler(websocket, data)
    else:
        await _handle_unknown(websocket, message_type)

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

def remove_player_from_queue(player_id: int) -> None:
    """Remove a player from the matchmaking queue and update related data structures."""
    global matchmaking_queue, players_in_queue, queue_metadata

    # Remove player from the queue
    matchmaking_queue = deque(
        (pid, ws, joined_at) for pid, ws, joined_at in matchmaking_queue if pid != player_id
    )

    # Remove player from the set of players in queue
    players_in_queue.discard(player_id)

    # Remove player metadata
    queue_metadata.pop(player_id, None)

    logger.info(f"Player {player_id} removed from matchmaking queue.")