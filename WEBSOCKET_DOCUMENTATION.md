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

## WebSocket Endpoints (as of latest code)

### 1. **Player WebSocket**
- **URL:**  
  `ws://localhost:8000/api/v1/websocket/websocket/ws/player/{player_id}`
- **Purpose:** Real-time communication for a specific player.
- **Parameters:**  
  - `player_id` (path): The player's database ID (integer).
- **Flow:**  
  1. Accepts the connection.
  2. Validates the player exists in the database.
  3. Registers the connection with the WebSocket manager.
  4. Sends a welcome message.
  5. Handles incoming JSON messages via `handle_player_message`.
  6. On disconnect or error, unregisters the connection.

---

### 2. **Game WebSocket**
- **URL:**  
  `ws://localhost:8000/api/v1/websocket/websocket/ws/game/{game_id}?player_id={player_id}`
- **Purpose:** Real-time communication for a specific game session.
- **Parameters:**  
  - `game_id` (path): The game ID (integer).
  - `player_id` (query): The player's ID (integer).
- **Flow:**  
  1. Accepts the connection.
  2. Validates the game and player.
  3. Registers the connection with the WebSocket manager.
  4. Sends the current game state.
  5. Handles incoming JSON messages via `handle_game_message`.
  6. On disconnect or error, unregisters the connection.

---

### 3. **Matchmaking WebSocket**
- **URL:**  
  `ws://localhost:8000/api/v1/websocket/websocket/ws/matchmaking`
- **Purpose:** Real-time matchmaking queue management.
- **Flow:**  
  1. Accepts the connection.
  2. Registers the connection with the WebSocket manager.
  3. Sends a welcome message.
  4. Handles incoming JSON messages via `handle_matchmaking_message`.
  5. On disconnect or error, unregisters the connection.

---

### 4. **Test WebSocket (Echo)**
- **URL:**  
  `ws://localhost:8000/api/v1/websocket/websocket/ws/test`
- **Purpose:** Simple echo endpoint for connectivity testing.
- **Flow:**  
  1. Accepts the connection.
  2. Echoes back any received message as plain text.

---

## Message Handling Functions

- **`handle_player_message(websocket, player_id, message, db)`**  
  Handles messages for the player WebSocket.  
  Recognized message types:  
  - `ping`: Responds with a `pong` message.  
  - `player_action`: Handles player actions (e.g., strategy submission).  
  - Unknown types: Responds with an error message.

- **`handle_game_message(websocket, game_id, player_id, message, db)`**  
  Handles messages for the game WebSocket.  
  Recognized message types:  
  - `ping`: Responds with a `pong` message.  
  - `turn_action`: Handles turn action submissions.  
  - Unknown types: Responds with an error message.

- **`handle_matchmaking_message(websocket, message)`**  
  Handles messages for the matchmaking WebSocket.  
  Recognized message types:  
  - `ping`: Responds with a `pong` message.  
  - `join_queue`: Handles joining the matchmaking queue.  
  - Unknown types: Responds with an error message.

- **`process_player_action(player_id, game_id, action, db)`**  
  Processes a player action and notifies other players in the game.

- **`process_turn_action(game_id, player_id, strategy, sacrifice, db)`**  
  Processes a turn action submission and notifies other players in the game.

---

## Message Format

All WebSocket messages (except the test echo) are expected to be JSON objects with the following structure:
```json
{
  "type": "message_type",
  "data": { ... },
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

---

## Example URLs

- Player:      `ws://localhost:8000/api/v1/websocket/websocket/ws/player/1`
- Game:        `ws://localhost:8000/api/v1/websocket/websocket/ws/game/1?player_id=1`
- Matchmaking: `ws://localhost:8000/api/v1/websocket/websocket/ws/matchmaking`
- Test:        `ws://localhost:8000/api/v1/websocket/websocket/ws/test`

---

**Notes:**
- All endpoints require the correct path and parameters as described above.
- The test endpoint is for connectivity/debugging only and does not require JSON messages.
- Player and game endpoints require valid IDs that exist in the database.
- The backend uses a WebSocket manager to track and route messages for all connections.

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