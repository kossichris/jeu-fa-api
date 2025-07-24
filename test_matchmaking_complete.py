#!/usr/bin/env python3
"""
Complete test script for the matchmaking system
Tests queue management, automatic matching, and proper cleanup
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MatchmakingTestClient:
    def __init__(self, player_id: int, name: str):
        self.player_id = player_id
        self.name = name
        self.websocket = None
        self.in_queue = False
        self.messages_received = []
        
    async def connect(self):
        """Connect to the matchmaking WebSocket"""
        try:
            # Note: You might need to add player_id as a query parameter
            # ws://localhost:8000/websocket/ws/matchmaking?player_id=1
            self.websocket = await websockets.connect(
                f"ws://localhost:8000/websocket/ws/matchmaking?player_id={self.player_id}"
            )
            logger.info(f"Player {self.player_id} ({self.name}) connected to matchmaking")
            return True
        except Exception as e:
            logger.error(f"Failed to connect player {self.player_id}: {e}")
            return False
    
    async def listen_for_messages(self):
        """Listen for messages from the server"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                self.messages_received.append({
                    "timestamp": datetime.now().isoformat(),
                    "data": data
                })
                
                logger.info(f"Player {self.player_id} received: {data}")
                
                # Handle specific message types
                if data.get("type") == "matchmaking_status":
                    msg_data = data.get("data", {})
                    if "in_queue" in msg_data:
                        self.in_queue = msg_data["in_queue"]
                        if msg_data.get("status") == "match_found":
                            logger.info(f"🎉 Player {self.player_id} found a match! Game ID: {msg_data.get('game_id')}")
                            # Could automatically connect to game WebSocket here
                            break
                        elif msg_data.get("status") == "joined":
                            logger.info(f"✅ Player {self.player_id} joined queue at position {msg_data.get('queue_position')}")
                        elif msg_data.get("status") == "left":
                            logger.info(f"👋 Player {self.player_id} left the queue")
                            
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Player {self.player_id} connection closed")
        except Exception as e:
            logger.error(f"Error listening for player {self.player_id}: {e}")
    
    async def join_queue(self):
        """Send join queue message"""
        if self.websocket:
            message = {
                "type": "join_queue",
                "data": {
                    "player_id": self.player_id
                }
            }
            await self.websocket.send(json.dumps(message))
            logger.info(f"Player {self.player_id} sent join_queue message")
    
    async def leave_queue(self):
        """Send leave queue message"""
        if self.websocket:
            message = {
                "type": "leave_queue",
                "data": {
                    "player_id": self.player_id
                }
            }
            await self.websocket.send(json.dumps(message))
            logger.info(f"Player {self.player_id} sent leave_queue message")
    
    async def ping(self):
        """Send ping message"""
        if self.websocket:
            message = {"type": "ping", "data": {}}
            await self.websocket.send(json.dumps(message))
    
    async def disconnect(self):
        """Close the WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            logger.info(f"Player {self.player_id} disconnected")

async def test_basic_matchmaking():
    """Test basic two-player matchmaking"""
    logger.info("🧪 Starting basic matchmaking test...")
    
    # Create two test clients
    player1 = MatchmakingTestClient(1, "Alice")
    player2 = MatchmakingTestClient(2, "Bob")
    
    # Connect both players
    if not await player1.connect():
        logger.error("Failed to connect player 1")
        return
    if not await player2.connect():
        logger.error("Failed to connect player 2")
        return
    
    # Start listening for messages
    listen_task1 = asyncio.create_task(player1.listen_for_messages())
    listen_task2 = asyncio.create_task(player2.listen_for_messages())
    
    # Wait a bit for initial connection messages
    await asyncio.sleep(1)
    
    # Player 1 joins queue
    await player1.join_queue()
    await asyncio.sleep(1)
    
    # Player 2 joins queue - this should trigger a match
    await player2.join_queue()
    
    # Wait for match to be made
    await asyncio.sleep(3)
    
    # Clean up
    listen_task1.cancel()
    listen_task2.cancel()
    await player1.disconnect()
    await player2.disconnect()
    
    logger.info("✅ Basic matchmaking test completed")

async def test_queue_leave():
    """Test leaving the queue"""
    logger.info("🧪 Starting queue leave test...")
    
    player1 = MatchmakingTestClient(3, "Charlie")
    
    if not await player1.connect():
        return
    
    listen_task = asyncio.create_task(player1.listen_for_messages())
    
    await asyncio.sleep(1)
    await player1.join_queue()
    await asyncio.sleep(1)
    await player1.leave_queue()
    await asyncio.sleep(1)
    
    listen_task.cancel()
    await player1.disconnect()
    
    logger.info("✅ Queue leave test completed")

async def test_multiple_players():
    """Test with multiple players joining"""
    logger.info("🧪 Starting multiple players test...")
    
    players = [
        MatchmakingTestClient(4, "David"),
        MatchmakingTestClient(5, "Eve"),
        MatchmakingTestClient(6, "Frank"),
        MatchmakingTestClient(7, "Grace")
    ]
    
    # Connect all players
    connected_players = []
    listen_tasks = []
    
    for player in players:
        if await player.connect():
            connected_players.append(player)
            listen_tasks.append(asyncio.create_task(player.listen_for_messages()))
    
    await asyncio.sleep(1)
    
    # Join queue with delays
    for i, player in enumerate(connected_players):
        await player.join_queue()
        await asyncio.sleep(0.5)  # Small delay between joins
    
    # Wait for matches to be made
    await asyncio.sleep(5)
    
    # Clean up
    for task in listen_tasks:
        task.cancel()
    for player in connected_players:
        await player.disconnect()
    
    logger.info("✅ Multiple players test completed")

async def main():
    """Run all tests"""
    logger.info("🚀 Starting matchmaking system tests...")
    
    try:
        await test_basic_matchmaking()
        await asyncio.sleep(2)
        
        await test_queue_leave()
        await asyncio.sleep(2)
        
        await test_multiple_players()
        
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
    except Exception as e:
        logger.error(f"Test error: {e}")
    
    logger.info("🏁 All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
