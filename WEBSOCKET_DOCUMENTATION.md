# WebSocket Implementation for Jeu Fa API

This document describes the WebSocket implementation for real-time communication in the Jeu Fa strategic game API.

## Overview

The WebSocket implementation provides real-time communication for:
- **Player connections** - Individual player status and actions
- **Game sessions** - Real-time game state updates and turn management
- **Matchmaking** - Real-time opponent finding and queue management

## Architecture

### Components

1. **WebSocket Manager** (`app/websocket_manager.py`)
   - Manages all WebSocket connections
   - Handles connection types (player, game, matchmaking)
   - Provides message routing and broadcasting

2. **WebSocket Router** (`app/routers/websocket.py`)
   - Defines WebSocket endpoints
   - Handles connection validation and message processing
   - Integrates with existing game logic

3. **WebSocket Service** (`app/websocket_service.py`)
   - Provides high-level game event notifications
   - Integrates with existing game logic
   - Handles complex game state updates

## WebSocket Endpoints

### 1. Player WebSocket
**URL:** `ws://localhost:8000/websocket/ws/player/{player_id}`

**Purpose:** Individual player connections for status updates and actions

**Connection Flow:**
1. Client connects with player ID
2. Server validates player exists
3. Server sends welcome message
4. Client can send/receive player-specific messages

**Message Types:**
- `player_connect` - Welcome message
- `ping`/`pong` - Connection health check
- `player_action` - Player actions
- `error` - Error messages

### 2. Game WebSocket
**URL:** `ws://localhost:8000/websocket/ws/game/{game_id}?player_id={player_id}`

**Purpose:** Real-time game communication for active games

**Connection Flow:**
1. Client connects with game ID and player ID
2. Server validates game and player participation
3. Server sends current game state
4. Client can send/receive game-specific messages

**Message Types:**
- `game_state_update` - Game state changes
- `turn_start` - New turn begins
- `turn_action` - Player turn submissions
- `turn_result` - Turn results and calculations
- `game_end` - Game completion
- `player_action` - Player actions during game
- `ping`/`pong` - Connection health check

### 3. Matchmaking WebSocket
**URL:** `ws://localhost:8000/websocket/ws/matchmaking`

**Purpose:** Real-time matchmaking queue management

**Connection Flow:**
1. Client connects to matchmaking
2. Server sends welcome message
3. Client can join/leave queue
4. Server notifies when matches are found

**Message Types:**
- `matchmaking_status` - Queue status updates
- `match_found` - Opponent found notification
- `join_queue` - Join matchmaking queue
- `ping`/`pong` - Connection health check

## Message Format

All WebSocket messages follow this JSON format:

```json
{
  "type": "message_type",
  "data": {
    // Message-specific data
  },
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

### Message Types

#### Player Messages
- `player_connect` - Player successfully connected
- `player_disconnect` - Player disconnected
- `player_action` - Player performed an action

#### Game Messages
- `game_state_update` - Game state changed
- `turn_start` - New turn started
- `turn_action` - Player submitted turn action
- `turn_result` - Turn results calculated
- `game_end` - Game completed

#### Matchmaking Messages
- `matchmaking_join` - Joined matchmaking queue
- `matchmaking_leave` - Left matchmaking queue
- `match_found` - Opponent found
- `matchmaking_status` - Queue status update

#### System Messages
- `error` - Error occurred
- `ping` - Health check request
- `pong` - Health check response

## Integration with Existing Game Logic

### Matchmaking Integration

The WebSocket service integrates with the existing matchmaking system:

```python
# In matchmaking router
from app.websocket_service import websocket_game_service

# When match is found
await websocket_game_service.notify_match_found(
    player1_id, player2_id, game_id, db
)
```

### Game Logic Integration

WebSocket notifications are integrated with game logic:

```python
# When game starts
await websocket_game_service.notify_game_start(game_id, db)

# When turn starts
await websocket_game_service.notify_turn_start(game_id, turn_number, db)

# When turn completes
await websocket_game_service.notify_turn_result(game_id, turn_result)

# When game ends
await websocket_game_service.notify_game_end(game_id, winner_id, db)
```

## Client Implementation

### JavaScript Client Example

```javascript
class FaGameWebSocket {
    constructor(baseUrl = 'ws://localhost:8000') {
        this.baseUrl = baseUrl;
        this.websocket = null;
    }

    connectPlayer(playerId) {
        const url = `${this.baseUrl}/websocket/ws/player/${playerId}`;
        this.websocket = new WebSocket(url);
        
        this.websocket.onopen = () => {
            console.log('Connected to player WebSocket');
        };
        
        this.websocket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
        };
        
        this.websocket.onclose = () => {
            console.log('WebSocket connection closed');
        };
    }

    connectGame(gameId, playerId) {
        const url = `${this.baseUrl}/websocket/ws/game/${gameId}?player_id=${playerId}`;
        this.websocket = new WebSocket(url);
        
        this.websocket.onopen = () => {
            console.log('Connected to game WebSocket');
        };
        
        this.websocket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
        };
    }

    handleMessage(message) {
        switch (message.type) {
            case 'game_state_update':
                this.updateGameState(message.data);
                break;
            case 'turn_start':
                this.startTurn(message.data);
                break;
            case 'turn_result':
                this.showTurnResult(message.data);
                break;
            case 'game_end':
                this.endGame(message.data);
                break;
            case 'match_found':
                this.handleMatchFound(message.data);
                break;
        }
    }

    sendTurnAction(strategy, sacrifice = false) {
        this.sendMessage('turn_action', {
            strategy: strategy,
            sacrifice: sacrifice
        });
    }

    sendMessage(type, data) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                type: type,
                data: data
            }));
        }
    }
}
```

### Python Client Example

See `websocket_client_example.py` for a complete Python client implementation.

## Testing

### Manual Testing

1. **Start the server:**
   ```bash
   uvicorn app.main:app --reload
   ```

2. **Test WebSocket connections:**
   ```bash
   python websocket_client_example.py
   ```

3. **Monitor connections:**
   ```bash
   curl http://localhost:8000/websocket/ws/connections
   ```

### Automated Testing

Create tests for WebSocket functionality:

```python
import pytest
import asyncio
import websockets
import json

@pytest.mark.asyncio
async def test_player_websocket():
    async with websockets.connect('ws://localhost:8000/websocket/ws/player/1') as websocket:
        # Test connection
        message = await websocket.recv()
        data = json.loads(message)
        assert data['type'] == 'player_connect'
        
        # Test ping/pong
        await websocket.send(json.dumps({'type': 'ping', 'data': {}}))
        response = await websocket.recv()
        data = json.loads(response)
        assert data['type'] == 'pong'
```

## Security Considerations

1. **Authentication:** WebSocket connections should be authenticated
2. **Authorization:** Players can only access their own games
3. **Rate Limiting:** Implement rate limiting for WebSocket messages
4. **Input Validation:** Validate all incoming WebSocket messages

## Performance Considerations

1. **Connection Pooling:** WebSocket manager handles multiple connections
2. **Message Broadcasting:** Efficient broadcasting to game participants
3. **Memory Management:** Automatic cleanup of disconnected connections
4. **Scalability:** Consider Redis for WebSocket state in production

## Production Deployment

### Environment Variables

Add WebSocket-specific configuration:

```env
# WebSocket Configuration
WEBSOCKET_ENABLED=true
WEBSOCKET_MAX_CONNECTIONS=1000
WEBSOCKET_HEARTBEAT_INTERVAL=30
```

### Load Balancing

For production, consider:
- WebSocket-aware load balancers (HAProxy, Nginx)
- Sticky sessions for WebSocket connections
- Redis for WebSocket state across multiple servers

### Monitoring

Monitor WebSocket connections:
- Connection count
- Message throughput
- Error rates
- Connection duration

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check if server is running
   - Verify WebSocket endpoint URL
   - Check firewall settings

2. **Authentication Errors**
   - Verify player/game IDs exist
   - Check authorization logic

3. **Message Not Received**
   - Verify message format
   - Check WebSocket connection status
   - Monitor server logs

### Debug Tools

1. **Connection Info Endpoint:**
   ```bash
   curl http://localhost:8000/websocket/ws/connections
   ```

2. **Server Logs:**
   ```bash
   tail -f app.log
   ```

3. **WebSocket Client:**
   Use the provided `websocket_client_example.py` for testing.

## Future Enhancements

1. **Real-time Chat:** Add in-game chat functionality
2. **Spectator Mode:** Allow spectators to watch games
3. **Tournament Support:** Real-time tournament updates
4. **Mobile Support:** Optimize for mobile WebSocket clients
5. **Analytics:** Track WebSocket usage and performance 