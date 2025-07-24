#!/usr/bin/env python3
"""
Test script to verify the queue user information endpoints work correctly.
"""
import asyncio
import aiohttp
import json
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8000/api/v1/websocket"

async def test_endpoint(session: aiohttp.ClientSession, endpoint: str, description: str) -> Dict[str, Any]:
    """Test a specific endpoint and return the response"""
    print(f"🧪 Testing {description}...")
    
    try:
        url = f"{BASE_URL}{endpoint}"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ {description} - Status: {response.status}")
                return {"success": True, "data": data, "status": response.status}
            else:
                text = await response.text()
                print(f"❌ {description} - Status: {response.status}")
                print(f"Response: {text}")
                return {"success": False, "status": response.status, "error": text}
    except Exception as e:
        print(f"❌ {description} - Error: {e}")
        return {"success": False, "error": str(e)}

async def display_queue_users(data: Dict[str, Any]):
    """Display queue users in a nice format"""
    if not data.get("success", False):
        print("❌ Failed to get queue users data")
        return
    
    queue_data = data.get("data", {})
    users = queue_data.get("users", [])
    
    if not users:
        print("📭 No users currently in the matchmaking queue")
        return
    
    print(f"\n👥 Joueurs connectés en file d'attente ({len(users)} joueur(s)):")
    print("=" * 70)
    
    for user in users:
        print(f"🎮 Position {user['position']}: {user['name']} (ID: {user['player_id']})")
        print(f"   ⏱️  En attente: {user['waiting_time_formatted']}")
        print(f"   📅 Rejoint: {user['joined_at']}")
        if user.get('email'):
            print(f"   📧 Email: {user['email']}")
        print(f"   ✅ Actif: {'Oui' if user.get('is_active', True) else 'Non'}")
        print("-" * 50)

async def display_connected_users(data: Dict[str, Any]):
    """Display all connected users in a nice format"""
    if not data.get("success", False):
        print("❌ Failed to get connected users data")
        return
    
    conn_data = data.get("data", {})
    summary = conn_data.get("summary", {})
    
    print(f"\n📊 Résumé des connexions:")
    print("=" * 40)
    print(f"👥 En file d'attente: {summary.get('total_in_queue', 0)}")
    print(f"🔗 Connectés (WebSocket): {summary.get('total_connected', 0)}")
    print(f"🎮 En jeu: {summary.get('total_in_games', 0)}")
    print(f"📡 Total connexions WS: {summary.get('total_websocket_connections', 0)}")
    
    # Show queue users
    queue_users = conn_data.get("queue_users", [])
    if queue_users:
        print(f"\n👥 File d'attente ({len(queue_users)} joueur(s)):")
        for user in queue_users:
            print(f"  • {user['name']} - Position {user['queue_position']} - {user['waiting_time_seconds']}s")
    
    # Show connected users
    connected_users = conn_data.get("connected_users", [])
    if connected_users:
        print(f"\n🔗 Utilisateurs connectés ({len(connected_users)} joueur(s)):")
        for user in connected_users:
            print(f"  • {user['name']} - {user['connection_count']} connexion(s)")

async def main():
    """Run all endpoint tests"""
    print("🚀 Testing Queue User Information Endpoints\n")
    
    async with aiohttp.ClientSession() as session:
        # Test the queue users endpoint
        queue_result = await test_endpoint(
            session, 
            "/ws/queue-users", 
            "Queue Users Endpoint"
        )
        
        if queue_result["success"]:
            await display_queue_users(queue_result)
        
        print("\n" + "="*70 + "\n")
        
        # Test the connected users endpoint
        connected_result = await test_endpoint(
            session,
            "/ws/connected-users",
            "Connected Users Endpoint"
        )
        
        if connected_result["success"]:
            await display_connected_users(connected_result)
        
        print("\n" + "="*70 + "\n")
        
        # Test the debug queue endpoint
        debug_result = await test_endpoint(
            session,
            "/websocket/ws/debug-queue",
            "Debug Queue Endpoint"
        )
        
        if debug_result["success"]:
            debug_data = debug_result["data"]
            print(f"🐛 Debug Info:")
            print(f"   Queue Size: {debug_data.get('queue_size', 0)}")
            print(f"   Players in Set: {debug_data.get('total_players_in_queue', 0)}")
            print(f"   Metadata Count: {debug_data.get('metadata_count', 0)}")
            
            if debug_data.get('queue_items'):
                print(f"   Detailed Queue Items:")
                for item in debug_data['queue_items']:
                    print(f"     • {item['player_name']} (ID: {item['player_id']}) - {item['waiting_time_formatted']}")
        
        # Summary
        print(f"\n📋 Test Summary:")
        print(f"✅ Queue Users Endpoint: {'PASS' if queue_result['success'] else 'FAIL'}")
        print(f"✅ Connected Users Endpoint: {'PASS' if connected_result['success'] else 'FAIL'}")
        print(f"✅ Debug Queue Endpoint: {'PASS' if debug_result['success'] else 'FAIL'}")
        
        all_passed = all([queue_result['success'], connected_result['success'], debug_result['success']])
        
        if all_passed:
            print("\n🎉 All endpoints are working correctly!")
            return 0
        else:
            print("\n❌ Some endpoints failed. Check your FastAPI server.")
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
