#!/usr/bin/env python3
"""
Test script for matchmaking WebSocket with correct path
"""

import asyncio
import websockets
import json
import sys

async def test_matchmaking():
    """Test the matchmaking WebSocket endpoint"""
    
    # The correct WebSocket URL with API prefix
    ws_url = "ws://localhost:8000/api/v1/websocket/ws/matchmaking"
    
    try:
        print(f"Connecting to: {ws_url}")
        async with websockets.connect(ws_url) as websocket:
            print("✅ Connected to matchmaking WebSocket!")
            
            # Wait for welcome message
            welcome_msg = await websocket.recv()
            print(f"📥 Welcome message: {welcome_msg}")
            
            # Test joining queue
            join_message = {
                "type": "join_queue",
                "data": {
                    "player_id": 123
                }
            }
            
            print(f"📤 Sending join queue message: {json.dumps(join_message)}")
            await websocket.send(json.dumps(join_message))
            
            # Wait for response
            response = await websocket.recv()
            print(f"📥 Join queue response: {response}")
            
            # Test getting queue status
            status_message = {
                "type": "get_queue_status",
                "data": {
                    "player_id": 123
                }
            }
            
            print(f"📤 Sending status message: {json.dumps(status_message)}")
            await websocket.send(json.dumps(status_message))
            
            # Wait for response
            response = await websocket.recv()
            print(f"📥 Status response: {response}")
            
            # Test leaving queue
            leave_message = {
                "type": "leave_queue",
                "data": {
                    "player_id": 123
                }
            }
            
            print(f"📤 Sending leave queue message: {json.dumps(leave_message)}")
            await websocket.send(json.dumps(leave_message))
            
            # Wait for response
            response = await websocket.recv()
            print(f"📥 Leave queue response: {response}")
            
            print("✅ All matchmaking tests completed successfully!")
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Connection failed with status code: {e.status_code}")
        if e.status_code == 403:
            print("   This suggests the path might be wrong or there's an authentication issue")
        elif e.status_code == 404:
            print("   This suggests the endpoint doesn't exist at this path")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Testing Matchmaking WebSocket...")
    success = asyncio.run(test_matchmaking())
    sys.exit(0 if success else 1)
