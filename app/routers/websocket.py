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

@router.websocket("/ws/player/{player_id}")
async def player_websocket(
    websocket: WebSocket,
    player_id: int,
    token: Optional[str] = None
):
    """WebSocket endpoint for individual player connections"""
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

@router.websocket("/ws/game/{game_id}")
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

@router.websocket("/ws/matchmaking")
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
@router.get("/ws/connections")
async def get_connection_info():
    """Get information about current WebSocket connections"""
    return websocket_manager.get_connection_info() 