#!/usr/bin/env python3
"""
WebSocket client to test the online players endpoint
"""
import asyncio
import websockets
import json
from datetime import datetime

async def test_online_players_websocket():
    uri = "ws://127.0.0.1:8000/api/v1/websocket/websocket/ws/online-players"
    
    try:
        print(f"[{datetime.now()}] Connecting to {uri}")
        async with websockets.connect(uri) as websocket:
            print(f"[{datetime.now()}] Connected!")
            
            # Listen for initial message
            print(f"[{datetime.now()}] Waiting for initial message...")
            response = await websocket.recv()
            data = json.loads(response)
            
            print(f"[{datetime.now()}] Received initial message:")
            print(json.dumps(data, indent=2))
            
            # Send a ping message
            print(f"\n[{datetime.now()}] Sending ping message...")
            ping_msg = {
                "type": "ping",
                "data": {}
            }
            await websocket.send(json.dumps(ping_msg))
            
            # Wait for pong response
            response = await websocket.recv()
            data = json.loads(response)
            print(f"[{datetime.now()}] Received pong response:")
            print(json.dumps(data, indent=2))
            
            # Request refresh of online players
            print(f"\n[{datetime.now()}] Requesting online players refresh...")
            refresh_msg = {
                "type": "refresh_online_players",
                "data": {}
            }
            await websocket.send(json.dumps(refresh_msg))
            
            # Wait for refresh response
            response = await websocket.recv()
            data = json.loads(response)
            print(f"[{datetime.now()}] Received refresh response:")
            print(json.dumps(data, indent=2))
            
            print(f"\n[{datetime.now()}] Test completed successfully!")
            
    except Exception as e:
        print(f"[{datetime.now()}] Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_online_players_websocket())
