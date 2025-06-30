import json
import logging
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import asyncio
from enum import Enum

logger = logging.getLogger(__name__)

class ConnectionType(str, Enum):
    PLAYER = "player"
    GAME = "game"
    MATCHMAKING = "matchmaking"

class WebSocketManager:
    def __init__(self):
        # Store active connections by type and ID
        self.player_connections: Dict[int, WebSocket] = {}
        self.game_connections: Dict[int, Set[WebSocket]] = {}
        self.matchmaking_connections: Set[WebSocket] = set()
        
        # Store connection metadata
        self.connection_metadata: Dict[WebSocket, Dict] = {}
        
        # Lock for thread safety
        self.lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, connection_type: ConnectionType, 
                     identifier: Optional[int] = None, metadata: Optional[Dict] = None):
        """Connect a WebSocket with specified type and identifier"""
        await websocket.accept()
        
        async with self.lock:
            if connection_type == ConnectionType.PLAYER and identifier:
                self.player_connections[identifier] = websocket
            elif connection_type == ConnectionType.GAME and identifier:
                if identifier not in self.game_connections:
                    self.game_connections[identifier] = set()
                self.game_connections[identifier].add(websocket)
            elif connection_type == ConnectionType.MATCHMAKING:
                self.matchmaking_connections.add(websocket)
            
            # Store metadata
            self.connection_metadata[websocket] = {
                "type": connection_type,
                "identifier": identifier,
                "connected_at": datetime.utcnow(),
                **(metadata or {})
            }
        
        logger.info(f"WebSocket connected: {connection_type} - {identifier}")
    
    async def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket and clean up"""
        async with self.lock:
            metadata = self.connection_metadata.get(websocket, {})
            connection_type = metadata.get("type")
            identifier = metadata.get("identifier")
            
            if connection_type == ConnectionType.PLAYER and identifier:
                self.player_connections.pop(identifier, None)
            elif connection_type == ConnectionType.GAME and identifier:
                if identifier in self.game_connections:
                    self.game_connections[identifier].discard(websocket)
                    if not self.game_connections[identifier]:
                        del self.game_connections[identifier]
            elif connection_type == ConnectionType.MATCHMAKING:
                self.matchmaking_connections.discard(websocket)
            
            self.connection_metadata.pop(websocket, None)
        
        logger.info(f"WebSocket disconnected: {connection_type} - {identifier}")
    
    async def send_to_player(self, player_id: int, message: Dict[str, Any]):
        """Send message to a specific player"""
        websocket = self.player_connections.get(player_id)
        if websocket:
            try:
                await websocket.send_text(json.dumps(message))
                return True
            except Exception as e:
                logger.error(f"Error sending to player {player_id}: {e}")
                await self.disconnect(websocket)
        return False
    
    async def send_to_game(self, game_id: int, message: Dict[str, Any]):
        """Send message to all players in a game"""
        websockets = self.game_connections.get(game_id, set()).copy()
        disconnected = set()
        
        for websocket in websockets:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending to game {game_id}: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            await self.disconnect(websocket)
        
        return len(websockets) - len(disconnected)
    
    async def broadcast_matchmaking(self, message: Dict[str, Any]):
        """Broadcast message to all matchmaking connections"""
        disconnected = set()
        
        for websocket in self.matchmaking_connections.copy():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting matchmaking: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            await self.disconnect(websocket)
    
    async def send_personal_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to a specific WebSocket connection"""
        try:
            await websocket.send_text(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            await self.disconnect(websocket)
            return False
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get information about current connections (for debugging)"""
        return {
            "player_connections": len(self.player_connections),
            "game_connections": {game_id: len(connections) for game_id, connections in self.game_connections.items()},
            "matchmaking_connections": len(self.matchmaking_connections),
            "total_connections": len(self.connection_metadata)
        }

# Global WebSocket manager instance
websocket_manager = WebSocketManager()

# Message types for WebSocket communication
class WSMessageType(str, Enum):
    # Matchmaking messages
    MATCHMAKING_JOIN = "matchmaking_join"
    MATCHMAKING_LEAVE = "matchmaking_leave"
    MATCH_FOUND = "match_found"
    MATCHMAKING_STATUS = "matchmaking_status"
    
    # Game messages
    GAME_JOIN = "game_join"
    GAME_LEAVE = "game_leave"
    GAME_STATE_UPDATE = "game_state_update"
    TURN_START = "turn_start"
    TURN_ACTION = "turn_action"
    TURN_RESULT = "turn_result"
    GAME_END = "game_end"
    
    # Player messages
    PLAYER_CONNECT = "player_connect"
    PLAYER_DISCONNECT = "player_disconnect"
    PLAYER_ACTION = "player_action"
    
    # System messages
    ERROR = "error"
    PING = "ping"
    PONG = "pong"

def create_ws_message(message_type: WSMessageType, data: Dict[str, Any], 
                     timestamp: Optional[datetime] = None) -> Dict[str, Any]:
    """Create a standardized WebSocket message"""
    return {
        "type": message_type,
        "data": data,
        "timestamp": (timestamp or datetime.utcnow()).isoformat()
    } 