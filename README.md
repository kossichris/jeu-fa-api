# Jeu Fà API 🎮

A strategic game API built with FastAPI, featuring real-time gameplay via WebSocket connections, player management, and game logic for the Fà strategy game.

## 🚀 Features

- **Real-time Gameplay**: WebSocket support for live game interactions
- **Player Management**: Registration, authentication, and player profiles
- **Game Logic**: Complete Fà game implementation with strategic elements
- **Admin Panel**: Administrative controls for game management
- **Matchmaking**: Automated player matching system
- **Database Migrations**: Alembic integration for schema management
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation

## 📋 Requirements

- Python 3.8+
- PostgreSQL 12+
- pip (Python package manager)

## 🛠️ Installation & Setup

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd jeu-fa-api
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt

# Additionally, you might need to install python-multipart for form data processing
pip install python-multipart
```

### 4. Database Setup

#### Install PostgreSQL
Make sure PostgreSQL is installed and running on your system.

#### Create Database and User

```sql
-- Connect to PostgreSQL as superuser
sudo -u postgres psql

-- Create database and user
CREATE DATABASE fa_game_db;
CREATE USER fa_user WITH PASSWORD 'fagame2025';
GRANT ALL PRIVILEGES ON DATABASE fa_game_db TO fa_user;
\q
```

### 5. Environment Configuration

Create a `.env` file in the root directory:

**Option 1: Quick Setup (Recommended)**
```bash
# Navigate to project directory and activate virtual environment
cd jeu-fa-api
source venv/bin/activate

# Generate secure .env file automatically
cat > .env << 'EOF'
# Database Configuration
DATABASE_URL=postgresql://fa_user:fagame2025@localhost:5432/fa_game_db

# Application Configuration
ENVIRONMENT=development
DEBUG=true
API_TITLE=Jeu Fa API
API_DESCRIPTION=API pour le jeu stratégique Fà
API_VERSION=1.0.0
API_BASE_URL=http://localhost:8000

# Security Configuration (REQUIRED)
EOF

# Add generated secure keys
echo "SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" >> .env
echo "REFRESH_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" >> .env
echo "ADMIN_API_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(16))')" >> .env

# Add remaining configuration
cat >> .env << 'EOF'
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
RESET_TOKEN_EXPIRE_HOURS=24

# Game Configuration
MAX_GAME_TURNS=20
INITIAL_PFH=100
SACRIFICE_COST=14

# Database Pool
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10

# Server Configuration
SERVER_HOST=127.0.0.1
SERVER_PORT=8000

# CORS Origins (JSON format or comma-separated)
CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost", "http://127.0.0.1"]

# Logging
LOG_LEVEL=INFO
ENABLE_REQUEST_LOGGING=true
EOF
```

**Option 2: Manual Setup**
Create a `.env` file manually with the following content:

```bash
# Database Configuration
DATABASE_URL=postgresql://fa_user:fagame2025@localhost:5432/fa_game_db

# Application Configuration
ENVIRONMENT=development
DEBUG=true
API_TITLE=Jeu Fa API
API_DESCRIPTION=API pour le jeu stratégique Fà
API_VERSION=1.0.0
API_BASE_URL=http://localhost:8000

# Security Configuration (REQUIRED)
SECRET_KEY=your-secret-key-minimum-32-characters-long-for-jwt-tokens
REFRESH_SECRET_KEY=your-refresh-secret-key-minimum-32-characters-long-different-from-secret
ADMIN_API_KEY=your-admin-api-key-minimum-16-characters-long
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
RESET_TOKEN_EXPIRE_HOURS=24

# Game Configuration
MAX_GAME_TURNS=20
INITIAL_PFH=100
SACRIFICE_COST=14

# Database Pool
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10

# Server Configuration
SERVER_HOST=127.0.0.1
SERVER_PORT=8000

# CORS Origins (JSON format or comma-separated)
CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost", "http://127.0.0.1"]

# Logging
LOG_LEVEL=INFO
ENABLE_REQUEST_LOGGING=true
```

**⚠️ Important Security Notes:**
- Replace `SECRET_KEY` with a secure random string of at least 32 characters
- Replace `REFRESH_SECRET_KEY` with a different secure random string of at least 32 characters  
- Replace `ADMIN_API_KEY` with a secure string of at least 16 characters
- Never commit these keys to version control

**Generate secure keys manually:**
```bash
# Generate a secure SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate a secure REFRESH_SECRET_KEY  
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate a secure ADMIN_API_KEY
python -c "import secrets; print(secrets.token_urlsafe(16))"
```

### 6. Database Migration

Initialize and run database migrations:

```bash
# Initialize Alembic (if not already done)
alembic upgrade head
```

## 🚀 Running the Application

### Development Server

```bash
# Start the FastAPI development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc

### Production Server

```bash
# For production, use gunicorn with uvicorn workers
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 📚 API Documentation

### Main Endpoints

- **Players**: `/players` - Player management and registration
- **Authentication**: `/auth` - User authentication and tokens
- **Game Actions**: `/game-actions` - Game moves and actions
- **FADU**: `/fadu` - FADU-specific game logic
- **Matchmaking**: `/matchmaking` - Player matching system
- **Admin**: `/admin` - Administrative functions
- **WebSocket**: `/ws` - Real-time game connections

### Authentication

The API uses JWT token-based authentication. To access protected endpoints:

1. Register/login via `/auth` endpoints
2. Include the JWT token in the Authorization header: `Bearer <token>`

### WebSocket Connection

Connect to the WebSocket endpoint for real-time game updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/{player_id}');
```

See `websocket_client_example.py` and `WEBSOCKET_DOCUMENTATION.md` for detailed WebSocket usage.

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_game_logic.py
```

### WebSocket Testing

Use the provided WebSocket client example:

```bash
python websocket_client_example.py
```

## 🗃️ Database Management

### Create New Migration

```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply Migrations

```bash
alembic upgrade head
```

### Rollback Migration

```bash
alembic downgrade -1
```

## 🏗️ Project Structure

```
jeu-fa-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database connection and session
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── auth.py              # Authentication logic
│   ├── dependencies.py      # Dependency injection
│   ├── utils.py             # Utility functions
│   ├── game_logic.py        # Core game logic
│   ├── websocket_manager.py # WebSocket connection management
│   ├── websocket_service.py # WebSocket business logic
│   ├── token_utils.py       # JWT token utilities
│   ├── game_logic/          # Game-specific logic modules
│   │   ├── fadu_data.py
│   │   ├── fadu_logic.py
│   │   └── strategy_logic.py
│   └── routers/             # API route handlers
│       ├── admin.py
│       ├── auth.py
│       ├── fadu_router.py
│       ├── game_actions.py
│       ├── matchmaking.py
│       ├── players.py
│       └── websocket.py
├── alembic/                 # Database migrations
├── requirements.txt         # Python dependencies
├── alembic.ini             # Alembic configuration
├── API_DOCUMENTATION.md    # Detailed API documentation
├── WEBSOCKET_DOCUMENTATION.md # WebSocket documentation
└── websocket_client_example.py # WebSocket client example
```

## 🔧 Configuration

The application uses Pydantic Settings for configuration management. All settings can be configured via environment variables or the `.env` file.

Key configuration sections:
- **Database**: Connection settings and pool configuration
- **Game Logic**: Game rules and parameters
- **API**: Server settings and CORS configuration
- **Security**: Authentication and token settings

## 📖 Documentation Files

- `API_DOCUMENTATION.md` - Comprehensive API endpoint documentation
- `WEBSOCKET_DOCUMENTATION.md` - WebSocket protocol and usage guide
- `websocket_client_example.py` - Example WebSocket client implementation

## 🐛 Troubleshooting

### Common Issues

1. **"Form data requires python-multipart to be installed" Error**
   - This occurs when your FastAPI application uses form data but python-multipart is not installed
   - Fix with: `pip install python-multipart`
   - This package is required for handling form data in FastAPI

2. **ValidationError: String should have at least X characters**
   - This occurs when security keys don't meet minimum length requirements
   - `SECRET_KEY` and `REFRESH_SECRET_KEY` must be at least 32 characters
   - `ADMIN_API_KEY` must be at least 16 characters
   - Use the key generation commands provided in the Environment Configuration section

2. **Database Connection Error**
   - Verify PostgreSQL is running
   - Check database credentials in `.env`
   - Ensure database and user exist

3. **Import Errors**
   - Activate virtual environment
   - Install all requirements: `pip install -r requirements.txt`

4. **Migration Issues**
   - Check database connection
   - Verify Alembic configuration in `alembic.ini`

5. **WebSocket Connection Issues**
   - Ensure the server is running
   - Check firewall settings
   - Verify WebSocket endpoint URL
   - If you see "Expected ASGI message 'websocket.send' or 'websocket.close', but got 'websocket.accept'" error, it indicates a double WebSocket acceptance issue

### Logs

Application logs are written to:
- Console output (for development)
- `app.log` file (for persistent logging)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Commit your changes: `git commit -am 'Add new feature'`
5. Push to the branch: `git push origin feature-name`
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Happy Gaming! 🎮**