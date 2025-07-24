#!/usr/bin/env python3
"""
Test script to verify matchmaking WebSocket functionality
Tests the join_queue, leave_queue, and get_queue_status message types
"""

import asyncio
import websockets
import json
from datetime import datetime

async def test_matchmaking_websocket():
    """Test the matchmaking WebSocket endpoint"""
    uri = "ws://localhost:8000/api/v1/websocket/ws/matchmaking"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected to matchmaking WebSocket: {uri}")
            
            # Wait for welcome message
            welcome_msg = await websocket.recv()
            print(f"📨 Welcome message: {welcome_msg}")
            
            # Test 1: Join queue
            print("\n🔄 Testing join_queue...")
            join_message = {
                "type": "join_queue",
                "data": {
                    "player_id": 123
                }
            }
            await websocket.send(json.dumps(join_message))
            response = await websocket.recv()
            print(f"📨 Join queue response: {response}")
            
            # Parse response to check structure
            parsed_response = json.loads(response)
            if "data" in parsed_response and "in_queue" in parsed_response["data"]:
                in_queue = parsed_response["data"]["in_queue"]
                print(f"✅ in_queue field found: {in_queue}")
            else:
                print("❌ in_queue field missing in response")
            
            # Wait a moment
            await asyncio.sleep(1)
            
            # Test 2: Get queue status
            print("\n🔄 Testing get_queue_status...")
            status_message = {
                "type": "get_queue_status",
                "data": {
                    "player_id": 123
                }
            }
            await websocket.send(json.dumps(status_message))
            response = await websocket.recv()
            print(f"📨 Queue status response: {response}")
            
            # Wait a moment
            await asyncio.sleep(1)
            
            # Test 3: Leave queue
            print("\n🔄 Testing leave_queue...")
            leave_message = {
                "type": "leave_queue",
                "data": {
                    "player_id": 123
                }
            }
            await websocket.send(json.dumps(leave_message))
            response = await websocket.recv()
            print(f"📨 Leave queue response: {response}")
            
            # Parse response to check structure
            parsed_response = json.loads(response)
            if "data" in parsed_response and "in_queue" in parsed_response["data"]:
                in_queue = parsed_response["data"]["in_queue"]
                print(f"✅ in_queue field found: {in_queue}")
            else:
                print("❌ in_queue field missing in response")
            
            # Test 4: Ping
            print("\n🔄 Testing ping...")
            ping_message = {
                "type": "ping",
                "data": {}
            }
            await websocket.send(json.dumps(ping_message))
            response = await websocket.recv()
            print(f"📨 Ping response: {response}")
            
            print("\n✅ All matchmaking WebSocket tests completed!")
            
    except websockets.exceptions.ConnectionClosed:
        print("❌ WebSocket connection closed unexpectedly")
    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

async def simulate_frontend_matchmaking():
    """Simulate the frontend matchmaking flow"""
    uri = "ws://localhost:8000/api/v1/websocket/ws/matchmaking"
    
    print("🎮 Simulating frontend matchmaking flow...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected to matchmaking WebSocket")
            
            # Simulate frontend variables
            in_queue = False
            queue_start_time = None
            
            # Wait for welcome message
            welcome_msg = await websocket.recv()
            print(f"📨 Welcome: {json.loads(welcome_msg)}")
            
            # Simulate joining queue (like frontend would do)
            print("\n🎯 Joining matchmaking queue...")
            join_message = {
                "type": "join_queue",
                "data": {
                    "player_id": 456
                }
            }
            await websocket.send(json.dumps(join_message))
            response = await websocket.recv()
            msg = json.loads(response)
            
            print(f"📨 Server response: {msg}")
            
            # Simulate handleMatchmakingStatus function
            if msg.get("type") == "matchmaking_status":
                data = msg.get("data", {})
                if data.get("in_queue") == True:
                    in_queue = True
                    queue_start_time = datetime.now()
                    print(f"✅ Frontend state: in_queue={in_queue}, queue_start_time={queue_start_time}")
                elif data.get("in_queue") == False:
                    in_queue = False
                    queue_start_time = None
                    print(f"✅ Frontend state: in_queue={in_queue}, queue_start_time={queue_start_time}")
            
            # Wait and then leave queue
            await asyncio.sleep(2)
            
            print("\n🎯 Leaving matchmaking queue...")
            leave_message = {
                "type": "leave_queue",
                "data": {
                    "player_id": 456
                }
            }
            await websocket.send(json.dumps(leave_message))
            response = await websocket.recv()
            msg = json.loads(response)
            
            print(f"📨 Server response: {msg}")
            
            # Simulate handleMatchmakingStatus function
            if msg.get("type") == "matchmaking_status":
                data = msg.get("data", {})
                if data.get("in_queue") == True:
                    in_queue = True
                    queue_start_time = queue_start_time or datetime.now()
                    print(f"✅ Frontend state: in_queue={in_queue}, queue_start_time={queue_start_time}")
                elif data.get("in_queue") == False:
                    in_queue = False
                    queue_start_time = None
                    print(f"✅ Frontend state: in_queue={in_queue}, queue_start_time={queue_start_time}")
            
            print(f"\n🎮 Final frontend state: in_queue={in_queue}, queue_start_time={queue_start_time}")
            
    except Exception as e:
        print(f"❌ Error in frontend simulation: {e}")

if __name__ == "__main__":
    print("🚀 Starting matchmaking WebSocket tests...")
    print("Make sure the FastAPI server is running on localhost:8000")
    print()
    
    # Run tests
    asyncio.run(test_matchmaking_websocket())
    
    print("\n" + "="*50 + "\n")
    
    # Run frontend simulation
    asyncio.run(simulate_frontend_matchmaking())
