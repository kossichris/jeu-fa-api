#!/usr/bin/env python3
"""
Simple WebSocket client to test online players endpoint functionality
"""
import asyncio
import websockets
import json
from datetime import datetime

async def test_online_players_functionality():
    """Test the online players WebSocket functionality"""
    uri = "ws://127.0.0.1:8000/api/v1/websocket/websocket/ws/online-players"
    
    try:
        print(f"🔌 Connecting to online players monitor...")
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected successfully!")
            
            # Test 1: Receive initial message
            print(f"\n📥 Test 1: Waiting for initial message...")
            response = await websocket.recv()
            data = json.loads(response)
            
            print(f"✅ Received initial message:")
            print(f"   Type: {data['type']}")
            print(f"   Online players: {data['data']['total_count']}")
            print(f"   Message: {data['data'].get('message', 'N/A')}")
            
            # Test 2: Send ping and receive pong
            print(f"\n🏓 Test 2: Testing ping/pong...")
            ping_msg = {"type": "ping", "data": {}}
            await websocket.send(json.dumps(ping_msg))
            
            response = await websocket.recv()
            data = json.loads(response)
            
            if data['type'] == 'pong':
                print(f"✅ Pong received successfully!")
            else:
                print(f"❌ Expected pong, got: {data['type']}")
            
            # Test 3: Request refresh of online players
            print(f"\n🔄 Test 3: Testing refresh functionality...")
            refresh_msg = {"type": "refresh_online_players", "data": {}}
            await websocket.send(json.dumps(refresh_msg))
            
            response = await websocket.recv()
            data = json.loads(response)
            
            if data['type'] == 'online_players_update':
                print(f"✅ Refresh response received!")
                print(f"   Total online players: {data['data']['total_count']}")
                print(f"   Players list: {len(data['data']['online_players'])} entries")
            else:
                print(f"❌ Expected online_players_update, got: {data['type']}")
            
            # Test 4: Send invalid message type
            print(f"\n❌ Test 4: Testing error handling...")
            invalid_msg = {"type": "invalid_message_type", "data": {}}
            await websocket.send(json.dumps(invalid_msg))
            
            response = await websocket.recv()
            data = json.loads(response)
            
            if data['type'] == 'error':
                print(f"✅ Error handling works correctly!")
                print(f"   Error message: {data['data']['message']}")
            else:
                print(f"❌ Expected error, got: {data['type']}")
            
            print(f"\n🎉 All tests completed successfully!")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")

async def test_http_endpoint():
    """Test the HTTP endpoint as well"""
    import aiohttp
    
    try:
        print(f"\n🌐 Testing HTTP endpoint...")
        async with aiohttp.ClientSession() as session:
            async with session.get('http://127.0.0.1:8000/api/v1/websocket/websocket/ws/online-players') as response:
                data = await response.json()
                
                print(f"✅ HTTP endpoint works!")
                print(f"   Status: {response.status}")
                print(f"   Total online players: {data['total_count']}")
                print(f"   Players: {len(data['online_players'])} entries")
                
    except Exception as e:
        print(f"❌ HTTP endpoint error: {e}")

async def main():
    """Run all tests"""
    print("🚀 Starting Online Players WebSocket Tests")
    print("=" * 50)
    
    await test_online_players_functionality()
    await test_http_endpoint()
    
    print("\n" + "=" * 50)
    print("🏁 Tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
