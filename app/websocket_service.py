import logging
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from .websocket_manager import websocket_manager, WSMessageType, create_ws_message
from .models import DBGame, DBPlayer, Strategy
from .database import get_db

logger = logging.getLogger(__name__)

class WebSocketGameService:
    """Service to handle WebSocket game events and notifications"""
    
    @staticmethod
    async def notify_match_found(player1_id: int, player2_id: int, game_id: int, db: Session):
        """Notify players when a match is found"""
        try:
            # Get player names
            player1 = db.query(DBPlayer).filter(DBPlayer.id == player1_id).first()
            player2 = db.query(DBPlayer).filter(DBPlayer.id == player2_id).first()
            
            if not player1 or not player2:
                logger.error(f"Players not found for match notification: {player1_id}, {player2_id}")
                return
            
            # Create match found message
            match_msg = create_ws_message(
                WSMessageType.MATCH_FOUND,
                {
                    "game_id": game_id,
                    "opponent_name": player2.name,
                    "player_position": 1
                }
            )
            
            # Send to player 1
            await websocket_manager.send_to_player(player1_id, match_msg)
            
            # Send to player 2
            match_msg_player2 = create_ws_message(
                WSMessageType.MATCH_FOUND,
                {
                    "game_id": game_id,
                    "opponent_name": player1.name,
                    "player_position": 2
                }
            )
            await websocket_manager.send_to_player(player2_id, match_msg_player2)
            
            logger.info(f"Match found notification sent for game {game_id}")
            
        except Exception as e:
            logger.error(f"Error notifying match found: {e}")
    
    @staticmethod
    async def notify_game_start(game_id: int, db: Session):
        """Notify players when a game starts"""
        try:
            game = db.query(DBGame).filter(DBGame.id == game_id).first()
            if not game:
                logger.error(f"Game not found: {game_id}")
                return
            
            # Create game start message
            start_msg = create_ws_message(
                WSMessageType.GAME_STATE_UPDATE,
                {
                    "game_id": game_id,
                    "current_turn": game.current_turn,
                    "player1_pfh": game.player1_pfh,
                    "player2_pfh": game.player2_pfh,
                    "status": "started"
                }
            )
            
            # Send to all players in the game
            await websocket_manager.send_to_game(game_id, start_msg)
            
            logger.info(f"Game start notification sent for game {game_id}")
            
        except Exception as e:
            logger.error(f"Error notifying game start: {e}")
    
    @staticmethod
    async def notify_turn_start(game_id: int, turn_number: int, db: Session):
        """Notify players when a new turn starts"""
        try:
            game = db.query(DBGame).filter(DBGame.id == game_id).first()
            if not game:
                logger.error(f"Game not found: {game_id}")
                return
            
            # Create turn start message
            turn_msg = create_ws_message(
                WSMessageType.TURN_START,
                {
                    "game_id": game_id,
                    "turn_number": turn_number,
                    "player1_pfh": game.player1_pfh,
                    "player2_pfh": game.player2_pfh,
                    "time_limit": 30  # 30 seconds per turn
                }
            )
            
            # Send to all players in the game
            await websocket_manager.send_to_game(game_id, turn_msg)
            
            logger.info(f"Turn start notification sent for game {game_id}, turn {turn_number}")
            
        except Exception as e:
            logger.error(f"Error notifying turn start: {e}")
    
    @staticmethod
    async def notify_turn_result(game_id: int, turn_result: Dict[str, Any]):
        """Notify players of turn results"""
        try:
            # Create turn result message
            result_msg = create_ws_message(
                WSMessageType.TURN_RESULT,
                {
                    "game_id": game_id,
                    **turn_result
                }
            )
            
            # Send to all players in the game
            await websocket_manager.send_to_game(game_id, result_msg)
            
            logger.info(f"Turn result notification sent for game {game_id}")
            
        except Exception as e:
            logger.error(f"Error notifying turn result: {e}")
    
    @staticmethod
    async def notify_game_end(game_id: int, winner_id: Optional[int], db: Session):
        """Notify players when a game ends"""
        try:
            game = db.query(DBGame).filter(DBGame.id == game_id).first()
            if not game:
                logger.error(f"Game not found: {game_id}")
                return
            
            # Get winner name if there is one
            winner_name = None
            if winner_id:
                winner = db.query(DBPlayer).filter(DBPlayer.id == winner_id).first()
                winner_name = winner.name if winner else None
            
            # Create game end message
            end_msg = create_ws_message(
                WSMessageType.GAME_END,
                {
                    "game_id": game_id,
                    "winner_id": winner_id,
                    "winner_name": winner_name,
                    "final_player1_pfh": game.player1_pfh,
                    "final_player2_pfh": game.player2_pfh,
                    "total_turns": game.current_turn - 1
                }
            )
            
            # Send to all players in the game
            await websocket_manager.send_to_game(game_id, end_msg)
            
            logger.info(f"Game end notification sent for game {game_id}")
            
        except Exception as e:
            logger.error(f"Error notifying game end: {e}")
    
    @staticmethod
    async def notify_player_action(game_id: int, player_id: int, action: str, action_data: Dict[str, Any]):
        """Notify other players of a player's action"""
        try:
            # Create player action message
            action_msg = create_ws_message(
                WSMessageType.PLAYER_ACTION,
                {
                    "game_id": game_id,
                    "player_id": player_id,
                    "action": action,
                    **action_data
                }
            )
            
            # Send to all players in the game
            await websocket_manager.send_to_game(game_id, action_msg)
            
            logger.info(f"Player action notification sent for game {game_id}, player {player_id}")
            
        except Exception as e:
            logger.error(f"Error notifying player action: {e}")
    
    @staticmethod
    async def notify_fadu_draw(game_id: int, player_id: int, fadu_data: Dict[str, Any]):
        """Notify players of Fadu card draws"""
        try:
            # Create Fadu draw message
            fadu_msg = create_ws_message(
                WSMessageType.PLAYER_ACTION,
                {
                    "game_id": game_id,
                    "player_id": player_id,
                    "action": "fadu_draw",
                    "fadu_data": fadu_data
                }
            )
            
            # Send to all players in the game
            await websocket_manager.send_to_game(game_id, fadu_msg)
            
            logger.info(f"Fadu draw notification sent for game {game_id}, player {player_id}")
            
        except Exception as e:
            logger.error(f"Error notifying Fadu draw: {e}")
    
    @staticmethod
    async def notify_sacrifice_action(game_id: int, player_id: int, sacrifice_cost: int, fadu_data: Optional[Dict[str, Any]] = None):
        """Notify players of sacrifice actions"""
        try:
            # Create sacrifice message
            sacrifice_msg = create_ws_message(
                WSMessageType.PLAYER_ACTION,
                {
                    "game_id": game_id,
                    "player_id": player_id,
                    "action": "sacrifice",
                    "sacrifice_cost": sacrifice_cost,
                    "fadu_data": fadu_data
                }
            )
            
            # Send to all players in the game
            await websocket_manager.send_to_game(game_id, sacrifice_msg)
            
            logger.info(f"Sacrifice notification sent for game {game_id}, player {player_id}")
            
        except Exception as e:
            logger.error(f"Error notifying sacrifice action: {e}")
    
    @staticmethod
    async def notify_player_disconnect(game_id: int, player_id: int):
        """Notify other players when a player disconnects"""
        try:
            # Create disconnect message
            disconnect_msg = create_ws_message(
                WSMessageType.PLAYER_DISCONNECT,
                {
                    "game_id": game_id,
                    "player_id": player_id,
                    "message": "Player disconnected"
                }
            )
            
            # Send to all players in the game
            await websocket_manager.send_to_game(game_id, disconnect_msg)
            
            logger.info(f"Player disconnect notification sent for game {game_id}, player {player_id}")
            
        except Exception as e:
            logger.error(f"Error notifying player disconnect: {e}")
    
    @staticmethod
    async def notify_matchmaking_status(player_id: int, status: str, additional_data: Optional[Dict[str, Any]] = None):
        """Notify player of matchmaking status changes"""
        try:
            # Create matchmaking status message
            status_msg = create_ws_message(
                WSMessageType.MATCHMAKING_STATUS,
                {
                    "player_id": player_id,
                    "status": status,
                    **(additional_data or {})
                }
            )
            
            # Send to specific player
            await websocket_manager.send_to_player(player_id, status_msg)
            
            logger.info(f"Matchmaking status notification sent for player {player_id}: {status}")
            
        except Exception as e:
            logger.error(f"Error notifying matchmaking status: {e}")

# Global service instance
websocket_game_service = WebSocketGameService() 