#!/usr/bin/env python3
"""
Simple test to verify the matchmaking WebSocket endpoint is working correctly.
"""
import asyncio
import websockets
import json
import sys

async def test_matchmaking_websocket():
    """Test the matchmaking WebSocket connection"""
    
    # Test URLs
    base_url = "ws://localhost:8000/api/v1/websocket/ws/matchmaking"
    
    print("🧪 Testing Matchmaking WebSocket Connection\n")
    
    # Test 1: Connection without player_id
    print("1️⃣ Testing connection without player_id...")
    try:
        async with websockets.connect(base_url) as websocket:
            print("✅ Connected successfully!")
            
            # Wait for welcome message
            message = await websocket.recv()
            data = json.loads(message)
            print(f"📨 Welcome message: {data}")
            
            print("✅ Test 1 passed: Connection without player_id works\n")
    except Exception as e:
        print(f"❌ Test 1 failed: {e}\n")
        return False
    
    # Test 2: Connection with valid player_id
    print("2️⃣ Testing connection with player_id=1...")
    try:
        url_with_player = f"{base_url}?player_id=1"
        async with websockets.connect(url_with_player) as websocket:
            print("✅ Connected successfully!")
            
            # Wait for welcome message
            message = await websocket.recv()
            data = json.loads(message)
            print(f"📨 Welcome message: {data}")
            
            # Test join queue
            join_message = {
                "type": "join_queue",
                "data": {
                    "player_id": 1
                }
            }
            await websocket.send(json.dumps(join_message))
            
            # Wait for response
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"📨 Join queue response: {response_data}")
            
            print("✅ Test 2 passed: Connection with player_id works\n")
    except Exception as e:
        print(f"❌ Test 2 failed: {e}\n")
        return False
    
    # Test 3: Connection with invalid player_id
    print("3️⃣ Testing connection with invalid player_id=99999...")
    try:
        url_with_invalid = f"{base_url}?player_id=99999"
        async with websockets.connect(url_with_invalid) as websocket:
            print("✅ Connected (connection accepted)!")
            
            # Wait for error message
            message = await websocket.recv()
            data = json.loads(message)
            print(f"📨 Error message: {data}")
            
            if data.get("type") == "error":
                print("✅ Test 3 passed: Invalid player_id properly handled\n")
            else:
                print("❌ Test 3 failed: Expected error message for invalid player_id\n")
                return False
    except Exception as e:
        print(f"❌ Test 3 failed: {e}\n")
        return False
    
    print("🎉 All tests passed! WebSocket matchmaking endpoint is working correctly!")
    return True

async def main():
    """Run the tests"""
    print("Starting WebSocket tests...\n")
    
    try:
        success = await test_matchmaking_websocket()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        print(f"❌ Failed to run tests: {e}")
        sys.exit(1)
