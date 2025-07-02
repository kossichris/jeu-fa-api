#!/usr/bin/env python3
"""
Script to create a test player for WebSocket testing
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import sessionmaker
from app.database import engine
from app.models import DBPlayer, User
from app.config import Settings

def create_test_player():
    """Create a test player in the database"""
    settings = Settings()
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if test player already exists
        existing_player = db.query(DBPlayer).filter(DBPlayer.name == "TestPlayer").first()
        if existing_player:
            print(f"Test player already exists with ID: {existing_player.id}")
            print(f"Name: {existing_player.name}")
            print(f"PFH: {existing_player.pfh}")
            return existing_player.id
        
        # Create a test user first (if needed)
        test_user = db.query(User).filter(User.email == "test@example.com").first()
        if not test_user:
            test_user = User(
                email="test@example.com",
                username="testuser",
                hashed_password="dummy_hash",  # In real app, this would be properly hashed
                is_active=True
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
            print(f"Created test user with ID: {test_user.id}")
        
        # Create test player
        test_player = DBPlayer(
            name="TestPlayer",
            pfh=100,  # Initial PFH
            user_id=test_user.id,
            is_active=True
        )
        
        db.add(test_player)
        db.commit()
        db.refresh(test_player)
        
        print(f"✅ Test player created successfully!")
        print(f"Player ID: {test_player.id}")
        print(f"Player Name: {test_player.name}")
        print(f"Player PFH: {test_player.pfh}")
        print(f"User ID: {test_player.user_id}")
        print(f"Active: {test_player.is_active}")
        
        return test_player.id
        
    except Exception as e:
        print(f"❌ Error creating test player: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Creating test player for WebSocket testing...")
    player_id = create_test_player()
    print(f"\n🎮 You can now connect to WebSocket with player ID: {player_id}")
    print(f"WebSocket URL: ws://localhost:8000/api/v1/websocket/ws/player/{player_id}") 