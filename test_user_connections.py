#!/usr/bin/env python3
"""
Test WebSocket connections for specific users
"""
import asyncio
import websockets
import json
from datetime import datetime

async def test_user_connection(player_id, user_name="Test User"):
    """Test connecting a specific user to the player WebSocket"""
    uri = f"ws://127.0.0.1:8000/api/v1/websocket/websocket/ws/player/{player_id}"
    
    try:
        print(f"[{datetime.now()}] Connecting {user_name} (ID: {player_id}) to {uri}")
        async with websockets.connect(uri) as websocket:
            print(f"[{datetime.now()}] {user_name} connected successfully!")
            
            # Listen for initial message
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                print(f"[{datetime.now()}] {user_name} received:")
                print(json.dumps(data, indent=2))
                
                # Keep connection alive
                print(f"[{datetime.now()}] {user_name} staying connected for 30 seconds...")
                await asyncio.sleep(30)
                
            except asyncio.TimeoutError:
                print(f"[{datetime.now()}] {user_name} - No response received within timeout")
            except Exception as e:
                print(f"[{datetime.now()}] {user_name} - Error: {e}")
                
    except Exception as e:
        print(f"[{datetime.now()}] {user_name} - Connection failed: {e}")

async def monitor_online_users():
    """Monitor online users while connections are active"""
    for i in range(35):  # Monitor for 35 seconds
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                # Check WebSocket connections
                async with session.get('http://127.0.0.1:8000/api/v1/websocket/websocket/ws/debug-connections') as response:
                    data = await response.json()
                    print(f"\n[{datetime.now()}] Connection Status:")
                    print(f"  Player connections: {data['player_connections']}")
                    print(f"  Matchmaking connections: {data['matchmaking_connections']}")
                
                # Check online players
                async with session.get('http://127.0.0.1:8000/api/v1/websocket/websocket/ws/online-players') as response:
                    data = await response.json()
                    print(f"  Online players: {data['total_count']}")
                    for player in data['online_players']:
                        print(f"    - {player['player_name']} (ID: {player['player_id']})")
                
        except Exception as e:
            print(f"[{datetime.now()}] Monitor error: {e}")
        
        await asyncio.sleep(5)  # Check every 5 seconds

async def test_multiple_users():
    """Test multiple user connections"""
    print("🚀 Testing multiple user connections...")
    
    # Start monitoring
    monitor_task = asyncio.create_task(monitor_online_users())
    
    # Start user connections with different IDs (simulating your logged-in users)
    user_tasks = [
        asyncio.create_task(test_user_connection(1, "koxkeny@gmail.com")),
        asyncio.create_task(test_user_connection(2, "chrishouns21@gmail.com")),
        asyncio.create_task(test_user_connection(3, "test_user@gmail.com"))
    ]
    
    # Wait for all tasks
    await asyncio.gather(monitor_task, *user_tasks, return_exceptions=True)
    
    print("🏁 Test completed!")

if __name__ == "__main__":
    asyncio.run(test_multiple_users())
