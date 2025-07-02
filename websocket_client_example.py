#!/usr/bin/env python3
"""
WebSocket Client Example for Jeu Fa API

This script demonstrates how to connect to the WebSocket endpoints
and handle real-time game events.
"""

import asyncio
import json
import websockets
from typing import Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FaGameWebSocketClient:
    def __init__(self, base_url: str = "ws://localhost:8000/api/v1"):
        self.base_url = base_url
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.player_id: Optional[int] = None
        self.game_id: Optional[int] = None
        
    async def connect_player(self, player_id: int):
        """Connect to player WebSocket endpoint"""
        try:
            url = f"{self.base_url}/websocket/ws/player/{player_id}"
            self.websocket = await websockets.connect(url)
            self.player_id = player_id
            
            logger.info(f"Connected to player WebSocket for player {player_id}")
            
            # Start listening for messages
            await self.listen_for_messages()
            
        except Exception as e:
            logger.error(f"Error connecting to player WebSocket: {e}")
    
    async def connect_game(self, game_id: int, player_id: int):
        """Connect to game WebSocket endpoint"""
        try:
            url = f"{self.base_url}/websocket/ws/game/{game_id}?player_id={player_id}"
            self.websocket = await websockets.connect(url)
            self.game_id = game_id
            self.player_id = player_id
            
            logger.info(f"Connected to game WebSocket for game {game_id}, player {player_id}")
            
            # Start listening for messages
            await self.listen_for_messages()
            
        except Exception as e:
            logger.error(f"Error connecting to game WebSocket: {e}")
    
    async def connect_matchmaking(self):
        """Connect to matchmaking WebSocket endpoint"""
        try:
            url = f"{self.base_url}/websocket/ws/matchmaking"
            self.websocket = await websockets.connect(url)
            
            logger.info("Connected to matchmaking WebSocket")
            
            # Start listening for messages
            await self.listen_for_messages()
            
        except Exception as e:
            logger.error(f"Error connecting to matchmaking WebSocket: {e}")
    
    async def listen_for_messages(self):
        """Listen for incoming WebSocket messages"""
        try:
            async for message in self.websocket:
                await self.handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error listening for messages: {e}")
    
    async def handle_message(self, message: str):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            message_data = data.get("data", {})
            timestamp = data.get("timestamp")
            
            logger.info(f"Received message: {message_type} at {timestamp}")
            
            # Handle different message types
            if message_type == "player_connect":
                logger.info(f"Player connected: {message_data}")
                
            elif message_type == "match_found":
                logger.info(f"Match found! Game ID: {message_data.get('game_id')}, Opponent: {message_data.get('opponent_name')}")
                
            elif message_type == "game_state_update":
                logger.info(f"Game state updated: {message_data}")
                
            elif message_type == "turn_start":
                logger.info(f"Turn {message_data.get('turn_number')} started!")
                
            elif message_type == "turn_result":
                logger.info(f"Turn result: {message_data}")
                
            elif message_type == "game_end":
                winner = message_data.get('winner_name', 'No winner')
                logger.info(f"Game ended! Winner: {winner}")
                
            elif message_type == "player_action":
                logger.info(f"Player action: {message_data}")
                
            elif message_type == "error":
                logger.error(f"Error message: {message_data}")
                
            elif message_type == "pong":
                logger.debug("Received pong")
                
            else:
                logger.info(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON message received")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def send_message(self, message_type: str, data: dict):
        """Send a message through the WebSocket"""
        if not self.websocket:
            logger.error("No WebSocket connection")
            return
        
        try:
            message = {
                "type": message_type,
                "data": data,
                "timestamp": None  # Server will add timestamp
            }
            
            await self.websocket.send(json.dumps(message))
            logger.info(f"Sent message: {message_type}")
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    async def send_ping(self):
        """Send a ping message"""
        await self.send_message("ping", {})
    
    async def send_turn_action(self, strategy: str, sacrifice: bool = False):
        """Send a turn action"""
        await self.send_message("turn_action", {
            "strategy": strategy,
            "sacrifice": sacrifice
        })
    
    async def send_player_action(self, action: str, game_id: Optional[int] = None):
        """Send a player action"""
        data = {"action": action}
        if game_id:
            data["game_id"] = game_id
        await self.send_message("player_action", data)
    
    async def join_matchmaking_queue(self, player_id: int):
        """Join the matchmaking queue"""
        await self.send_message("join_queue", {"player_id": player_id})
    
    async def close(self):
        """Close the WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            logger.info("WebSocket connection closed")

async def demo_player_connection():
    """Demonstrate player WebSocket connection"""
    client = FaGameWebSocketClient()
    
    try:
        # Connect to player WebSocket
        await client.connect_player(player_id=1)
        
        # Send a ping
        await client.send_ping()
        
        # Keep connection alive for a while
        await asyncio.sleep(10)
        
    finally:
        await client.close()

async def demo_game_connection():
    """Demonstrate game WebSocket connection"""
    client = FaGameWebSocketClient()
    
    try:
        # Connect to game WebSocket
        await client.connect_game(game_id=1, player_id=1)
        
        # Send a turn action
        await asyncio.sleep(2)
        await client.send_turn_action(strategy="C", sacrifice=False)
        
        # Keep connection alive for a while
        await asyncio.sleep(10)
        
    finally:
        await client.close()

async def demo_matchmaking():
    """Demonstrate matchmaking WebSocket connection"""
    client = FaGameWebSocketClient()
    
    try:
        # Connect to matchmaking WebSocket
        await client.connect_matchmaking()
        
        # Join the queue
        await asyncio.sleep(1)
        await client.join_matchmaking_queue(player_id=1)
        
        # Keep connection alive for a while
        await asyncio.sleep(10)
        
    finally:
        await client.close()

async def main():
    """Main demo function"""
    print("Jeu Fa WebSocket Client Demo")
    print("=" * 40)
    
    # Choose which demo to run
    print("1. Player connection demo")
    print("2. Game connection demo")
    print("3. Matchmaking demo")
    
    choice = input("Enter your choice (1-3): ").strip()
    
    if choice == "1":
        await demo_player_connection()
    elif choice == "2":
        await demo_game_connection()
    elif choice == "3":
        await demo_matchmaking()
    else:
        print("Invalid choice")

if __name__ == "__main__":
    # Install websockets if not available
    try:
        import websockets
    except ImportError:
        print("websockets package not found. Install it with: pip install websockets")
        exit(1)
    
    asyncio.run(main()) 