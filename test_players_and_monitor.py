#!/usr/bin/env python3
"""
WebSocket client to test player connections and online players monitoring
"""
import asyncio
import websockets
import json
from datetime import datetime

async def simulate_player_connection(player_id: int):
    """Simulate a player connection"""
    uri = f"ws://127.0.0.1:8000/api/v1/websocket/websocket/ws/player/{player_id}"
    
    try:
        print(f"[{datetime.now()}] Player {player_id} connecting to {uri}")
        async with websockets.connect(uri) as websocket:
            print(f"[{datetime.now()}] Player {player_id} connected!")
            
            # Wait for welcome message
            response = await websocket.recv()
            data = json.loads(response)
            print(f"[{datetime.now()}] Player {player_id} received welcome:")
            print(json.dumps(data, indent=2))
            
            # Keep connection alive for a bit
            await asyncio.sleep(10)
            
    except Exception as e:
        print(f"[{datetime.now()}] Player {player_id} error: {e}")

async def monitor_online_players():
    """Monitor online players"""
    uri = "ws://127.0.0.1:8000/api/v1/websocket/websocket/ws/online-players"
    
    try:
        print(f"[{datetime.now()}] Monitor connecting to {uri}")
        async with websockets.connect(uri) as websocket:
            print(f"[{datetime.now()}] Monitor connected!")
            
            # Listen for messages for 15 seconds
            timeout = 15
            start_time = asyncio.get_event_loop().time()
            
            while asyncio.get_event_loop().time() - start_time < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(response)
                    print(f"[{datetime.now()}] Monitor received:")
                    print(json.dumps(data, indent=2))
                    print("-" * 50)
                    
                    # Request refresh every 5 seconds
                    if int(asyncio.get_event_loop().time() - start_time) % 5 == 0:
                        refresh_msg = {
                            "type": "refresh_online_players",
                            "data": {}
                        }
                        await websocket.send(json.dumps(refresh_msg))
                        
                except asyncio.TimeoutError:
                    # Request refresh every second if no messages
                    refresh_msg = {
                        "type": "refresh_online_players",
                        "data": {}
                    }
                    await websocket.send(json.dumps(refresh_msg))
                    
    except Exception as e:
        print(f"[{datetime.now()}] Monitor error: {e}")

async def test_with_simulated_players():
    """Test online players monitoring with simulated player connections"""
    print("Starting comprehensive test...")
    
    # Start the monitor
    monitor_task = asyncio.create_task(monitor_online_players())
    
    # Wait a bit, then start players
    await asyncio.sleep(2)
    
    # Start player connections with delays
    player_tasks = []
    for i in range(1, 4):  # Players 1, 2, 3
        await asyncio.sleep(2)  # Stagger connections
        task = asyncio.create_task(simulate_player_connection(i))
        player_tasks.append(task)
    
    # Wait for all tasks to complete
    await asyncio.gather(monitor_task, *player_tasks, return_exceptions=True)
    
    print("Test completed!")

if __name__ == "__main__":
    asyncio.run(test_with_simulated_players())
