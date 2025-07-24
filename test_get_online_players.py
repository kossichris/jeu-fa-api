#!/usr/bin/env python3
"""
Test script to verify that the "get_online_players" message type works correctly
in the matchmaking WebSocket endpoint.
"""
import asyncio
import websockets
import json
import sys

MATCHMAKING_WS_URL = "ws://localhost:8000/api/v1/websocket/ws/matchmaking"

async def test_get_online_players():
    """Test the get_online_players message type"""
    print("🧪 Testing 'get_online_players' message type\n")
    
    try:
        # Connect to matchmaking WebSocket
        async with websockets.connect(MATCHMAKING_WS_URL) as websocket:
            print("✅ Connected to matchmaking WebSocket")
            
            # Wait for welcome message
            welcome = await websocket.recv()
            welcome_data = json.loads(welcome)
            print(f"📨 Welcome message: {welcome_data.get('data', {}).get('message', 'Connected')}")
            
            # Send get_online_players request
            request_message = {
                "type": "get_online_players",
                "data": {}
            }
            
            print(f"📤 Sending message: {json.dumps(request_message, indent=2)}")
            await websocket.send(json.dumps(request_message))
            
            # Wait for response
            response = await websocket.recv()
            response_data = json.loads(response)
            
            print(f"📨 Response received:")
            print(json.dumps(response_data, indent=2))
            
            # Verify response structure
            if response_data.get("type") == "matchmaking_status":
                data = response_data.get("data", {})
                if data.get("type") == "online_players_response":
                    print("\n✅ Response structure is correct!")
                    
                    response_data_inner = data.get("data", {})
                    summary = response_data_inner.get("summary", {})
                    
                    print(f"📊 Summary:")
                    print(f"   - Players in queue: {summary.get('total_in_queue', 0)}")
                    print(f"   - Connected users: {summary.get('total_connected', 0)}")
                    print(f"   - Total WebSocket connections: {summary.get('total_websocket_connections', 0)}")
                    
                    queue_users = response_data_inner.get("queue_users", [])
                    connected_users = response_data_inner.get("connected_users", [])
                    
                    if queue_users:
                        print(f"\n👥 Queue users ({len(queue_users)}):")
                        for user in queue_users:
                            print(f"   - {user['name']} (ID: {user['player_id']}) - Position {user['position']}")
                    else:
                        print(f"\n👥 No users in queue")
                    
                    if connected_users:
                        print(f"\n🔗 Connected users ({len(connected_users)}):")
                        for user in connected_users:
                            print(f"   - {user['name']} (ID: {user['player_id']}) - {user['connection_count']} connection(s)")
                    else:
                        print(f"\n🔗 No other connected users")
                        
                    return True
                else:
                    print(f"❌ Unexpected response type: {data.get('type')}")
                    return False
            else:
                print(f"❌ Unexpected message type: {response_data.get('type')}")
                return False
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_other_message_types():
    """Test other supported message types"""
    print("\n" + "="*60)
    print("🧪 Testing other message types\n")
    
    try:
        async with websockets.connect(MATCHMAKING_WS_URL) as websocket:
            print("✅ Connected to test other message types")
            
            # Skip welcome message
            await websocket.recv()
            
            # Test get_queue_status
            print("📤 Testing 'get_queue_status'...")
            queue_status_msg = {
                "type": "get_queue_status",
                "data": {}
            }
            await websocket.send(json.dumps(queue_status_msg))
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"📨 Queue status response: {response_data}")
            
            # Test heartbeat
            print("\n📤 Testing 'heartbeat'...")
            heartbeat_msg = {
                "type": "heartbeat",
                "data": {}
            }
            await websocket.send(json.dumps(heartbeat_msg))
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"📨 Heartbeat response: {response_data}")
            
            # Test ping
            print("\n📤 Testing 'ping'...")
            ping_msg = {
                "type": "ping",
                "data": {}
            }
            await websocket.send(json.dumps(ping_msg))
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"📨 Ping response: {response_data}")
            
            print("\n✅ All message types tested successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Error testing message types: {e}")
        return False

async def test_unknown_message_type():
    """Test that unknown message types are handled properly"""
    print("\n" + "="*60)
    print("🧪 Testing unknown message type handling\n")
    
    try:
        async with websockets.connect(MATCHMAKING_WS_URL) as websocket:
            print("✅ Connected to test unknown message type")
            
            # Skip welcome message
            await websocket.recv()
            
            # Test unknown message type
            unknown_msg = {
                "type": "unknown_message_type",
                "data": {}
            }
            
            print(f"📤 Sending unknown message: {json.dumps(unknown_msg)}")
            await websocket.send(json.dumps(unknown_msg))
            
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"📨 Error response: {response_data}")
            
            if (response_data.get("type") == "error" and 
                "Unknown message type" in response_data.get("data", {}).get("message", "")):
                print("✅ Unknown message type properly handled with error response!")
                return True
            else:
                print("❌ Unexpected response to unknown message type")
                return False
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Testing Matchmaking WebSocket Message Types\n")
    
    results = []
    
    # Test get_online_players
    results.append(await test_get_online_players())
    
    # Test other message types
    results.append(await test_other_message_types())
    
    # Test unknown message type handling
    results.append(await test_unknown_message_type())
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📋 Test Results Summary:")
    print(f"✅ get_online_players: {'PASS' if results[0] else 'FAIL'}")
    print(f"✅ Other message types: {'PASS' if results[1] else 'FAIL'}")
    print(f"✅ Unknown message handling: {'PASS' if results[2] else 'FAIL'}")
    print(f"📊 Overall: {sum(results)}/{len(results)} tests passed")
    
    if all(results):
        print("\n🎉 All tests passed! The 'get_online_players' message type is working correctly!")
        return 0
    else:
        print("\n❌ Some tests failed. Check the WebSocket message handling.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
