"""
Bot Dashboard for Monitoring Automated Trading
Provides real-time monitoring and control interface
"""

import sys
import asyncio
import asyncpg
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import hashlib
import secrets
import re
from fastapi import FastAPI, HTTPException, Depends, Request, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
import jwt
# Simple status endpoint will be added directly to app

# Simple logging setup
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Trading Bot Dashboard", version="1.0.0")

# Router included in import section

# Session management with Redis
import redis
import json
import os

# Initialize Redis connection with proper pooling
redis_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
redis_client = None

def get_redis_client():
    """Get Redis client with singleton pattern to avoid connection leaks."""
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.Redis.from_url(
                redis_url, 
                decode_responses=True,
                max_connections=5,  # Smaller connection pool
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            redis_client.ping()
            logger.info("✅ Redis connection established with singleton pattern")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            redis_client = None
    return redis_client

security = HTTPBearer(auto_error=False)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (create directory if it doesn't exist)
import os
os.makedirs("dashboard/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")


# Simple database connection with proper cleanup
async def connect_db():
    """Connect to database with proper connection management."""
    return await asyncpg.connect(
        host='winu-bot-signal-postgres',
        port=5432,
        user='winu',
        password='winu250420',
        database='winudb',
        command_timeout=10  # Short timeout to prevent hanging connections
    )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash using passlib or SHA256 fallback."""
    import hashlib
    
    # Check if it's a SHA256 hash (64 hex characters)
    if len(hashed_password) == 64 and all(c in '0123456789abcdef' for c in hashed_password.lower()):
        logger.debug("Using SHA256 verification for legacy password")
        computed_hash = hashlib.sha256(plain_password.encode()).hexdigest()
        return computed_hash == hashed_password
    
    # Otherwise, try Argon2 (passlib) for newer passwords
    try:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False


# JWT Configuration
JWT_SECRET = os.getenv('JWT_SECRET', '302c4665d626ccf70553682a8038be89')
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 30

# Username validation pattern: alphanumeric, underscore, hyphen only
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{3,30}$')

def create_jwt_token(username: str) -> str:
    """Create a JWT token for API authentication."""
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    to_encode = {
        "sub": username,
        "exp": expire
    }
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


# Fallback in-memory sessions for when Redis is unavailable
fallback_sessions = {}

def create_session(user_id: int, username: str, is_admin: bool = False) -> str:
    """Create a new session in Redis with fallback to memory."""
    session_token = secrets.token_urlsafe(32)
    session_data = {
        "user_id": user_id,
        "username": username,
        "is_admin": is_admin,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
    }
    
    client = get_redis_client()
    if client:
        try:
            # Store session in Redis with 24-hour expiration
            client.setex(
                f"session:{session_token}",
                86400,  # 24 hours in seconds
                json.dumps(session_data)
            )
            logger.info(f"✅ Session stored in Redis: {username}")
        except Exception as e:
            logger.error(f"❌ Redis session storage failed: {e}, using fallback")
            fallback_sessions[session_token] = session_data
    else:
        # Fallback to in-memory storage
        fallback_sessions[session_token] = session_data
        logger.warning(f"⚠️ Using fallback session storage for: {username}")
    
    return session_token


def get_session(session_token: str) -> Optional[Dict]:
    """Get session data from Redis with fallback to memory."""
    client = get_redis_client()
    if client:
        try:
            session_data = client.get(f"session:{session_token}")
            if session_data:
                session = json.loads(session_data)
                
                # Check if session is expired
                expires_at = datetime.fromisoformat(session["expires_at"])
                if datetime.utcnow() > expires_at:
                    # Session expired, delete it from Redis
                    client.delete(f"session:{session_token}")
                    return None
                
                return session
        except Exception as e:
            logger.error(f"❌ Error getting session from Redis: {e}, trying fallback")
    
    # Fallback to in-memory sessions
    if session_token in fallback_sessions:
        session = fallback_sessions[session_token]
        
        # Check if session is expired
        expires_at = datetime.fromisoformat(session["expires_at"])
        if datetime.utcnow() > expires_at:
            # Session expired, delete it from fallback
            del fallback_sessions[session_token]
            return None
        
        return session
    
    return None


async def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """Authenticate user credentials."""
    conn = None
    try:
        conn = await connect_db()
        user = await conn.fetchrow(
            "SELECT id, username, email, hashed_password, is_active, is_admin FROM users WHERE username = $1",
            username
        )
        
        logger.info(f"User lookup result: {'Found' if user else 'Not found'}")
        
        if not user:
            logger.warning(f"User not found: {username}")
            return None
        
        if not user["is_active"]:
            logger.warning(f"User not active: {username}")
            return None
        
        logger.info(f"Verifying password for user: {username}")
        if not verify_password(password, user["hashed_password"]):
            logger.warning(f"Password verification failed for user: {username}")
            return None
        
        logger.info(f"Authentication successful for user: {username}")
        return {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "is_admin": user.get("is_admin", False)
        }
    except Exception as e:
        logger.error(f"Authentication error: {e}", exc_info=True)
        return None
    finally:
        if conn:
            await conn.close()


async def get_current_user(request: Request) -> Optional[Dict]:
    """Get current authenticated user."""
    session_token = request.cookies.get("session_token")
    if not session_token:
        return None
    
    return get_session(session_token)


def require_auth(current_user: Optional[Dict] = Depends(get_current_user)):
    """Require authentication for protected routes."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return current_user


def require_admin(current_user: Dict = Depends(require_auth)):
    """Require admin privileges."""
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user


@app.get("/test-login", response_class=HTMLResponse)
async def test_login_page():
    """Serve the test login page."""
    with open("static/test-login.html", "r") as f:
        return f.read()

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Serve the login page."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <!-- Google tag (gtag.js) -->
        <script async src="https://www.googletagmanager.com/gtag/js?id=G-R48BYVFMH2"></script>
        <script>
          window.dataLayer = window.dataLayer || [];
          function gtag(){dataLayer.push(arguments);}
          gtag('js', new Date());

          gtag('config', 'G-R48BYVFMH2');
        </script>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Winu Bot Dashboard - Login</title>
        <link href="/static/styles.css" rel="stylesheet">
        <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Inter', sans-serif; }
            .gradient-bg { background: linear-gradient(135deg, #1e40af 0%, #7c3aed 50%, #ec4899 100%); }
            .glass-effect { backdrop-filter: blur(10px); background: rgba(255, 255, 255, 0.1); }
            .winu-primary { background: linear-gradient(135deg, #1e40af 0%, #7c3aed 100%); }
            .winu-secondary { background: linear-gradient(135deg, #7c3aed 0%, #ec4899 100%); }
            .winu-accent { background: linear-gradient(135deg, #ec4899 0%, #f59e0b 100%); }
        </style>
    </head>
    <body class="gradient-bg min-h-screen flex items-center justify-center p-4">
        <div class="w-full max-w-md">
            <!-- Logo and Branding -->
            <div class="text-center mb-8">
                <div class="inline-flex items-center justify-center w-16 h-16 bg-white rounded-full shadow-lg mb-4">
                    <svg class="w-8 h-8 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                    </svg>
                </div>
                <h1 class="text-3xl font-bold text-white mb-2">Winu Bot</h1>
                <p class="text-white/80 text-sm">AI-Powered Trading Dashboard</p>
            </div>

            <!-- Login Card -->
            <div class="glass-effect rounded-2xl shadow-2xl p-8 border border-white/20">
                <div class="text-center mb-6">
                    <h2 class="text-2xl font-semibold text-white mb-2">Welcome Back</h2>
                    <p class="text-white/70 text-sm">Sign in to access your trading dashboard</p>
                </div>

                <form x-data="loginForm()" @submit.prevent="login" class="space-y-6">
                    <div class="space-y-4">
                        <div>
                            <label for="username" class="block text-sm font-medium text-white/90 mb-2">Username</label>
                            <input id="username" name="username" type="text" required 
                                   class="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/30 focus:border-transparent transition-all duration-200" 
                                   placeholder="Enter your username" x-model="username">
                        </div>
                        <div>
                            <label for="password" class="block text-sm font-medium text-white/90 mb-2">Password</label>
                            <input id="password" name="password" type="password" required 
                                   class="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/30 focus:border-transparent transition-all duration-200" 
                                   placeholder="Enter your password" x-model="password">
                        </div>
                    </div>

                    <button type="submit" 
                            class="w-full bg-white text-indigo-600 font-semibold py-3 px-4 rounded-lg hover:bg-white/90 focus:outline-none focus:ring-2 focus:ring-white/30 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                            :disabled="loading">
                        <span x-show="!loading" class="flex items-center justify-center">
                            <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"></path>
                            </svg>
                            Sign In
                        </span>
                        <span x-show="loading" class="flex items-center justify-center">
                            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-indigo-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Signing in...
                        </span>
                    </button>

                    <div x-show="error" class="bg-red-500/20 border border-red-500/30 rounded-lg p-3 text-red-200 text-sm text-center" x-text="error"></div>
                </form>
            </div>

            <!-- Footer -->
            <div class="text-center mt-8">
                <p class="text-white/60 text-sm">© 2024 Winu.app - Advanced Trading Solutions</p>
            </div>
        </div>

        <script>
            function loginForm() {
                return {
                    username: '',
                    password: '',
                    loading: false,
                    error: '',
                    
                    async login() {
                        this.loading = true;
                        this.error = '';
                        
                        // Get values from form inputs as fallback
                        const usernameInput = document.getElementById('username');
                        const passwordInput = document.getElementById('password');
                        
                        const username = this.username || usernameInput?.value || '';
                        const password = this.password || passwordInput?.value || '';
                        
                        console.log('Login attempt:', { username, password });
                        
                        if (!username || !password) {
                            this.error = 'Please enter both username and password';
                            this.loading = false;
                            return;
                        }
                        
                        try {
                            const requestData = { username, password };
                            console.log('Sending request data:', requestData);
                            
                            const response = await fetch('/api/auth/login', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                                body: JSON.stringify(requestData)
                            });
                            
                            console.log('Response status:', response.status);
                            
                            if (response.ok) {
                                const data = await response.json();
                                console.log('Login successful, setting cookie and redirecting...');
                                // Set the session cookie manually
                                document.cookie = `session_token=${data.session_token}; path=/; max-age=86400; secure; samesite=lax`;
                                window.location.href = '/';
                            } else {
                                try {
                                    const data = await response.json();
                                    this.error = data.detail || 'Login failed';
                                } catch (e) {
                                    this.error = 'Login failed. Please try again.';
                                }
                            }
                        } catch (error) {
                            console.error('Login error:', error);
                            this.error = 'Login failed. Please try again.';
                        } finally {
                            this.loading = false;
                        }
                    }
                }
            }
        </script>
    </body>
    </html>
    """


@app.post("/api/auth/test")
async def test_login(request: Request):
    """Test endpoint to debug login issues."""
    try:
        data = await request.json()
        logger.info(f"Test endpoint received: {data}")
        return {"message": "Test successful", "received_data": data}
    except Exception as e:
        logger.error(f"Test endpoint error: {e}")
        return {"error": str(e)}

@app.post("/api/auth/login")
async def login(request: Request):
    """Authenticate user and create session."""
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")
        
        logger.info(f"Login attempt - Username: {username}, Password length: {len(password) if password else 0}")
        
        if not username or not password:
            logger.error(f"Missing credentials - Username: {username}, Password present: {bool(password)}")
            raise HTTPException(status_code=400, detail="Username and password required")
        
        # Validate username format to prevent injection attacks
        if not USERNAME_PATTERN.match(username):
            logger.warning(f"Invalid username format in login attempt: {username}")
            raise HTTPException(status_code=400, detail="Invalid username format")
        
        user = await authenticate_user(username, password)
        if not user:
            logger.warning(f"Authentication failed for user: {username}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Check if user is admin
        if not user.get("is_admin", False):
            logger.warning(f"Non-admin user attempted to login: {username}")
            raise HTTPException(status_code=403, detail="Admin privileges required to access this dashboard")
        
        session_token = create_session(user["id"], user["username"], user.get("is_admin", False))
        logger.info(f"Login successful for admin user: {username}, session created")
        
        return {
            "message": "Login successful",
            "session_token": session_token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "is_admin": user.get("is_admin", False)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/logout")
async def logout(request: Request):
    """Logout user and clear session from Redis or fallback."""
    session_token = request.cookies.get("session_token")
    if session_token:
        # Delete session from Redis
        client = get_redis_client()
        if client:
            try:
                client.delete(f"session:{session_token}")
                logger.info("✅ Session deleted from Redis")
            except Exception as e:
                logger.error(f"❌ Error deleting session from Redis: {e}")
        
        # Also delete from fallback if it exists
        if session_token in fallback_sessions:
            del fallback_sessions[session_token]
            logger.info("✅ Session deleted from fallback storage")
    
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session_token")
    return response


@app.get("/api/current-user")
async def get_current_user_info(current_user: Dict = Depends(require_auth)):
    """Get current authenticated user information including admin status."""
    return {
        "user_id": current_user.get("user_id"),
        "username": current_user.get("username"),
        "is_admin": current_user.get("is_admin", False)
    }


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(current_user: Dict = Depends(require_admin)):
    """Serve the settings page for bot configuration and API key management."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Bot Settings - Winu Bot</title>
        <link href="/static/styles.css" rel="stylesheet">
        <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Inter', sans-serif; }
            .gradient-primary { background: linear-gradient(135deg, #1e40af 0%, #7c3aed 100%); }
            .gradient-accent { background: linear-gradient(135deg, #7c3aed 0%, #ec4899 100%); }
            .card-hover { transition: all 0.3s ease; }
            .card-hover:hover { transform: translateY(-2px); box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1); }
            .btn-gradient { background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%); }
            .btn-gradient:hover { background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%); }
        </style>
    </head>
    <body class="bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 min-h-screen">
        <div x-data="settingsApp()" class="min-h-screen">
            <!-- Header -->
            <header class="bg-white/90 backdrop-blur-lg shadow-xl border-b-2 border-indigo-100 sticky top-0 z-50">
                <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div class="flex justify-between items-center py-5">
                        <div class="flex items-center space-x-4">
                            <div class="w-12 h-12 gradient-primary rounded-2xl flex items-center justify-center shadow-2xl transform hover:scale-105 transition-all">
                                <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                                </svg>
                            </div>
                            <div>
                                <h1 class="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">Winu Bot</h1>
                                <p class="text-sm text-gray-500 font-medium">Configuration Center</p>
                            </div>
                        </div>
                        <div class="flex items-center space-x-3">
                            <a href="/" class="gradient-primary text-white px-6 py-3 rounded-xl hover:shadow-xl transition-all duration-300 flex items-center space-x-2 font-semibold transform hover:scale-105">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"></path>
                                </svg>
                                <span>Dashboard</span>
                            </a>
                        </div>
                    </div>
                </div>
            </header>

            <!-- Main Content -->
            <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <!-- Tabs -->
                <div class="bg-white/80 backdrop-blur-sm rounded-2xl shadow-2xl border border-white/20">
                    <div class="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-t-2xl border-b-2 border-indigo-100">
                        <nav class="flex space-x-1 px-6 py-2" aria-label="Tabs">
                            <button @click="activeTab = 'api-keys'" 
                                    :class="activeTab === 'api-keys' ? 'bg-white text-blue-600 shadow-lg' : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'"
                                    class="whitespace-nowrap py-3 px-6 rounded-xl font-semibold text-sm transition-all duration-200 flex items-center space-x-2">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"></path>
                                </svg>
                                <span>API Keys</span>
                            </button>
                            <button @click="activeTab = 'bot-config'" 
                                    :class="activeTab === 'bot-config' ? 'bg-white text-blue-600 shadow-lg' : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'"
                                    class="whitespace-nowrap py-3 px-6 rounded-xl font-semibold text-sm transition-all duration-200 flex items-center space-x-2">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                                </svg>
                                <span>Bot Configuration</span>
                            </button>
                            <button @click="activeTab = 'signals-history'; loadSignalsHistory()" 
                                    :class="activeTab === 'signals-history' ? 'bg-white text-blue-600 shadow-lg' : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'"
                                    class="whitespace-nowrap py-3 px-6 rounded-xl font-semibold text-sm transition-all duration-200 flex items-center space-x-2">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                                </svg>
                                <span>Signals History</span>
                            </button>
                        </nav>
                    </div>

                    <!-- API Keys Tab -->
                    <div x-show="activeTab === 'api-keys'" class="p-8">
                        <div class="flex justify-between items-center mb-8">
                            <div class="flex items-center space-x-4">
                                <div class="w-14 h-14 gradient-primary rounded-2xl flex items-center justify-center shadow-lg">
                                    <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                                        <path stroke-linecap="round" stroke-linejoin="round" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"></path>
                                    </svg>
                                </div>
                                <div>
                                    <h2 class="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">API Keys Manager</h2>
                                    <p class="text-gray-500 mt-1 font-medium">Connect your Binance trading accounts</p>
                                </div>
                            </div>
                            <button @click="showAddForm = !showAddForm" 
                                    class="btn-gradient text-white px-8 py-4 rounded-xl hover:shadow-2xl flex items-center space-x-3 font-bold transition-all duration-300 transform hover:scale-105">
                                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"></path>
                                </svg>
                                <span x-text="showAddForm ? 'Cancel' : 'Add API Key'"></span>
                            </button>
                        </div>

                        <!-- Add API Key Form -->
                        <div x-show="showAddForm" x-transition class="bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-2xl p-8 mb-8 shadow-xl">
                            <div class="flex items-center space-x-3 mb-6">
                                <div class="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center">
                                    <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"></path>
                                    </svg>
                                </div>
                                <h3 class="text-2xl font-bold text-gray-900">Add New Trading Account</h3>
                            </div>
                            <form @submit.prevent="addApiKey()" class="space-y-4">
                                <div class="grid grid-cols-2 gap-4">
                                    <div class="col-span-2">
                                        <label class="block text-sm font-medium text-gray-700">Account Name</label>
                                        <input x-model="newApiKey.api_name" type="text" required
                                               class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                               placeholder="e.g., Main Trading Account">
                                    </div>
                                    
                                    <div class="col-span-2">
                                        <label class="block text-sm font-medium text-gray-700">Binance API Key</label>
                                        <input x-model="newApiKey.api_key" type="text" required
                                               class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 font-mono">
                                    </div>
                                    
                                    <div class="col-span-2">
                                        <label class="block text-sm font-medium text-gray-700">Binance API Secret</label>
                                        <input x-model="newApiKey.api_secret" type="password" required
                                               class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 font-mono">
                                    </div>
                                    
                                    <div>
                                        <label class="block text-sm font-medium text-gray-700">Account Type</label>
                                        <select x-model="newApiKey.account_type"
                                                class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
                                            <option value="spot">Spot Trading</option>
                                            <option value="futures">Futures Trading</option>
                                            <option value="both">Both</option>
                                        </select>
                                    </div>
                                    
                                    <div>
                                        <label class="block text-sm font-medium text-gray-700">Environment</label>
                                        <select x-model="newApiKey.test_mode"
                                                class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
                                            <option :value="false">Live Trading</option>
                                            <option :value="true">Testnet</option>
                                        </select>
                                    </div>
                                    
                                    <div>
                                        <label class="block text-sm font-medium text-gray-700">Max Position Size (USD)</label>
                                        <input x-model.number="newApiKey.max_position_size_usd" type="number" step="10" min="10" required
                                               class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
                                    </div>
                                    
                                    <div>
                                        <label class="block text-sm font-medium text-gray-700">Leverage</label>
                                        <input x-model.number="newApiKey.leverage" type="number" step="1" min="1" max="125" required
                                               class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
                                    </div>
                                    
                                    <div class="col-span-2">
                                        <label class="flex items-center space-x-2">
                                            <input x-model="newApiKey.auto_trade_enabled" type="checkbox"
                                                   class="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-500 focus:ring-blue-500">
                                            <span class="text-sm font-medium text-gray-700">Enable Auto Trading</span>
                                        </label>
                                    </div>
                                </div>
                                
                                <div class="flex justify-end space-x-4 pt-6">
                                    <button type="button" @click="showAddForm = false" 
                                            class="px-8 py-3 border-2 border-gray-300 rounded-xl text-gray-700 hover:bg-gray-50 font-semibold transition-all hover:shadow-lg">
                                        Cancel
                                    </button>
                                    <button type="submit"
                                            class="btn-gradient text-white px-10 py-3 rounded-xl font-bold shadow-xl hover:shadow-2xl transition-all transform hover:scale-105">
                                        <span class="flex items-center space-x-2">
                                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                                                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"></path>
                                            </svg>
                                            <span>Add API Key</span>
                                        </span>
                                    </button>
                                </div>
                            </form>
                        </div>

                        <!-- API Keys List -->
                        <div class="space-y-4">
                            <template x-if="apiKeys.length === 0">
                                <div class="text-center py-12">
                                    <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"></path>
                                    </svg>
                                    <h3 class="mt-2 text-sm font-medium text-gray-900">No API keys</h3>
                                    <p class="mt-1 text-sm text-gray-500">Get started by adding your first Binance API key.</p>
                                </div>
                            </template>
                            
                            <template x-for="apiKey in apiKeys" :key="apiKey.id">
                                <div class="border-2 border-indigo-100 rounded-2xl p-6 hover:shadow-2xl transition-all duration-300 bg-white/50 backdrop-blur-sm card-hover">
                                    <div class="flex items-start justify-between">
                                        <div class="flex-1">
                                            <div class="flex items-center space-x-3 mb-4">
                                                <div class="w-10 h-10 gradient-primary rounded-xl flex items-center justify-center">
                                                    <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                                                        <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                                                    </svg>
                                                </div>
                                                <div class="flex-1">
                                                    <h3 class="text-xl font-bold text-gray-900" x-text="apiKey.api_name"></h3>
                                                    <div class="flex items-center space-x-2 mt-1">
                                                        <span class="px-3 py-1 rounded-full text-xs font-bold"
                                                              :class="apiKey.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'"
                                                              x-text="apiKey.is_active ? '✓ Active' : '○ Inactive'"></span>
                                                        <span class="px-3 py-1 rounded-full text-xs font-bold"
                                                              :class="apiKey.test_mode ? 'bg-yellow-100 text-yellow-700' : 'bg-blue-100 text-blue-700'"
                                                              x-text="apiKey.test_mode ? '⚠️ Testnet' : '🔴 Live'"></span>
                                                    </div>
                                                </div>
                                            </div>
                                            <div class="mt-4 grid grid-cols-2 gap-3 text-sm">
                                                <div class="bg-gradient-to-br from-blue-50 to-indigo-50 p-4 rounded-xl border-2 border-blue-200">
                                                    <div class="text-xs text-gray-500 font-semibold mb-1">TYPE</div>
                                                    <div class="text-lg font-bold text-blue-700" x-text="apiKey.account_type ? apiKey.account_type.toUpperCase() : 'N/A'"></div>
                                                </div>
                                                <div class="bg-gradient-to-br from-purple-50 to-pink-50 p-4 rounded-xl border-2 border-purple-200">
                                                    <div class="text-xs text-gray-500 font-semibold mb-1">LEVERAGE</div>
                                                    <div class="text-lg font-bold text-purple-700" x-text="apiKey.leverage ? apiKey.leverage + 'x' : 'N/A'"></div>
                                                </div>
                                                <div class="bg-gradient-to-br from-orange-50 to-amber-50 p-4 rounded-xl border-2 border-orange-200">
                                                    <div class="text-xs text-gray-500 font-semibold mb-1">MAX POSITION</div>
                                                    <div class="text-lg font-bold text-orange-700" x-text="apiKey.max_position_size_usd ? '$' + apiKey.max_position_size_usd : 'N/A'"></div>
                                                </div>
                                                <div class="bg-gradient-to-br from-green-50 to-emerald-50 p-4 rounded-xl border-2 border-green-200">
                                                    <div class="text-xs text-gray-500 font-semibold mb-1">BALANCE</div>
                                                    <div class="text-lg font-bold text-green-700" x-text="apiKey.current_balance ? '$' + apiKey.current_balance.toFixed(2) : 'Click Balance →'"></div>
                                                </div>
                                            </div>
                                        </div>
                                        <div class="flex flex-col space-y-3 ml-8">
                                            <button @click="verifyApiKey(apiKey.id)" 
                                                    style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); color: #ffffff;"
                                                    class="group px-6 py-3 rounded-xl font-bold shadow-lg hover:shadow-2xl transition-all duration-300 transform hover:scale-105 flex items-center justify-center space-x-2 min-w-[140px]">
                                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="3">
                                                    <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                                </svg>
                                                <span>Verify</span>
                                            </button>
                                            <button @click="getAccountBalance(apiKey.id)" 
                                                    style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #ffffff;"
                                                    class="group px-6 py-3 rounded-xl font-bold shadow-lg hover:shadow-2xl transition-all duration-300 transform hover:scale-105 flex items-center justify-center space-x-2 min-w-[140px]">
                                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="3">
                                                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                                </svg>
                                                <span>Balance</span>
                                            </button>
                                            <button @click="toggleAutoTrade(apiKey.id, !apiKey.auto_trade_enabled)" 
                                                    class="px-6 py-3 rounded-xl font-bold shadow-lg hover:shadow-2xl transition-all duration-300 transform hover:scale-105 flex items-center justify-center space-x-2 min-w-[140px]"
                                                    :style="apiKey.auto_trade_enabled ? 'background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: #ffffff;' : 'background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%); color: #ffffff;'">
                                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="3">
                                                    <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                                                </svg>
                                                <span x-text="apiKey.auto_trade_enabled ? 'Disable' : 'Enable'"></span>
                                            </button>
                                            <button @click="deleteApiKey(apiKey.id)" 
                                                    style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: #ffffff;"
                                                    class="group px-6 py-3 rounded-xl font-bold shadow-lg hover:shadow-2xl transition-all duration-300 transform hover:scale-105 flex items-center justify-center space-x-2 min-w-[140px]">
                                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="3">
                                                    <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                                </svg>
                                                <span>Delete</span>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </template>
                        </div>
                    </div>

                    <!-- Bot Configuration Tab -->
                    <div x-show="activeTab === 'bot-config'" class="p-8">
                        <div class="flex items-center space-x-4 mb-8">
                            <div class="w-14 h-14 gradient-accent rounded-2xl flex items-center justify-center shadow-lg">
                                <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                                </svg>
                            </div>
                            <div>
                                <h2 class="text-3xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">Bot Configuration</h2>
                                <p class="text-gray-500 mt-1 font-medium">Advanced trading bot settings and risk management</p>
                            </div>
                        </div>

                        <!-- Configuration Sections -->
                        <div class="space-y-6">
                            <!-- Trading Settings -->
                            <div class="bg-white/50 backdrop-blur-sm border-2 border-purple-100 rounded-2xl p-6 card-hover">
                                <div class="flex items-center space-x-3 mb-6">
                                    <div class="w-10 h-10 bg-purple-600 rounded-xl flex items-center justify-center">
                                        <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                                            <path stroke-linecap="round" stroke-linejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
                                        </svg>
                                    </div>
                                    <h3 class="text-xl font-bold text-gray-900">Trading Settings</h3>
                                </div>
                                <div class="grid grid-cols-2 gap-6">
                                    <div class="bg-white p-4 rounded-xl border border-gray-200">
                                        <label class="block text-sm font-semibold text-gray-700 mb-2">Default Max Position Size (USD)</label>
                                        <input type="number" value="1000" class="w-full px-4 py-2 rounded-lg border border-gray-300 focus:border-purple-500 focus:ring-2 focus:ring-purple-200">
                                        <p class="text-xs text-gray-500 mt-1">Maximum position size per trade</p>
                                    </div>
                                    <div class="bg-white p-4 rounded-xl border border-gray-200">
                                        <label class="block text-sm font-semibold text-gray-700 mb-2">Default Leverage</label>
                                        <input type="number" value="10" min="1" max="125" class="w-full px-4 py-2 rounded-lg border border-gray-300 focus:border-purple-500 focus:ring-2 focus:ring-purple-200">
                                        <p class="text-xs text-gray-500 mt-1">Trading leverage multiplier</p>
                                    </div>
                                    <div class="bg-white p-4 rounded-xl border border-gray-200">
                                        <label class="block text-sm font-semibold text-gray-700 mb-2">Min Signal Score</label>
                                        <input type="number" value="70" min="0" max="100" class="w-full px-4 py-2 rounded-lg border border-gray-300 focus:border-purple-500 focus:ring-2 focus:ring-purple-200">
                                        <p class="text-xs text-gray-500 mt-1">Minimum confidence score to execute</p>
                                    </div>
                                    <div class="bg-white p-4 rounded-xl border border-gray-200">
                                        <label class="block text-sm font-semibold text-gray-700 mb-2">Max Daily Trades</label>
                                        <input type="number" value="10" min="1" max="100" class="w-full px-4 py-2 rounded-lg border border-gray-300 focus:border-purple-500 focus:ring-2 focus:ring-purple-200">
                                        <p class="text-xs text-gray-500 mt-1">Maximum trades per day</p>
                                    </div>
                                </div>
                            </div>

                            <!-- Risk Management -->
                            <div class="bg-white/50 backdrop-blur-sm border-2 border-red-100 rounded-2xl p-6 card-hover">
                                <div class="flex items-center space-x-3 mb-6">
                                    <div class="w-10 h-10 bg-red-600 rounded-xl flex items-center justify-center">
                                        <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                                            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                                        </svg>
                                    </div>
                                    <h3 class="text-xl font-bold text-gray-900">Risk Management</h3>
                                </div>
                                <div class="grid grid-cols-2 gap-6">
                                    <div class="bg-white p-4 rounded-xl border border-gray-200">
                                        <label class="block text-sm font-semibold text-gray-700 mb-2">Max Risk Per Trade (%)</label>
                                        <input type="number" value="2" min="0.1" max="10" step="0.1" class="w-full px-4 py-2 rounded-lg border border-gray-300 focus:border-red-500 focus:ring-2 focus:ring-red-200">
                                        <p class="text-xs text-gray-500 mt-1">Maximum risk per single trade</p>
                                    </div>
                                    <div class="bg-white p-4 rounded-xl border border-gray-200">
                                        <label class="block text-sm font-semibold text-gray-700 mb-2">Max Daily Loss (%)</label>
                                        <input type="number" value="5" min="1" max="20" step="0.5" class="w-full px-4 py-2 rounded-lg border border-gray-300 focus:border-red-500 focus:ring-2 focus:ring-red-200">
                                        <p class="text-xs text-gray-500 mt-1">Stop trading if daily loss exceeds</p>
                                    </div>
                                    <div class="bg-white p-4 rounded-xl border border-gray-200 col-span-2">
                                        <label class="flex items-center space-x-3">
                                            <input type="checkbox" checked class="w-5 h-5 rounded border-gray-300 text-red-600 focus:ring-red-500">
                                            <div>
                                                <span class="text-sm font-semibold text-gray-700">Emergency Stop on Loss</span>
                                                <p class="text-xs text-gray-500">Automatically stop bot if daily loss limit is reached</p>
                                            </div>
                                        </label>
                                    </div>
                                </div>
                            </div>

                            <!-- Bot Status & Controls -->
                            <div class="bg-white/50 backdrop-blur-sm border-2 border-blue-100 rounded-2xl p-6 card-hover">
                                <div class="flex items-center space-x-3 mb-6">
                                    <div class="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center">
                                        <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                                            <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                                        </svg>
                                    </div>
                                    <h3 class="text-xl font-bold text-gray-900">Bot Status & Controls</h3>
                                </div>
                                <div class="grid grid-cols-3 gap-4">
                                    <div class="bg-gradient-to-br from-green-50 to-emerald-50 p-6 rounded-xl border-2 border-green-200 text-center">
                                        <div class="w-12 h-12 bg-green-600 rounded-full flex items-center justify-center mx-auto mb-3">
                                            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                                                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"></path>
                                            </svg>
                                        </div>
                                        <div class="text-2xl font-bold text-green-700 mb-1">ACTIVE</div>
                                        <p class="text-xs text-gray-600">Bot is running</p>
                                    </div>
                                    <div class="bg-white p-6 rounded-xl border-2 border-gray-200 text-center">
                                        <div class="text-3xl font-bold text-gray-900 mb-1">24h</div>
                                        <p class="text-sm text-gray-600 font-medium">Uptime</p>
                                    </div>
                                    <div class="bg-white p-6 rounded-xl border-2 border-gray-200 text-center">
                                        <div class="text-3xl font-bold text-blue-600 mb-1">15</div>
                                        <p class="text-sm text-gray-600 font-medium">Signals Today</p>
                                    </div>
                                </div>
                            </div>

                            <!-- Notification Settings -->
                            <div class="bg-white/50 backdrop-blur-sm border-2 border-yellow-100 rounded-2xl p-6 card-hover">
                                <div class="flex items-center space-x-3 mb-6">
                                    <div class="w-10 h-10 bg-yellow-600 rounded-xl flex items-center justify-center">
                                        <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                                            <path stroke-linecap="round" stroke-linejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"></path>
                                        </svg>
                                    </div>
                                    <h3 class="text-xl font-bold text-gray-900">Notifications</h3>
                                </div>
                                <div class="space-y-4">
                                    <label class="flex items-center justify-between p-4 bg-white rounded-xl border border-gray-200 cursor-pointer hover:bg-gray-50">
                                        <div class="flex items-center space-x-3">
                                            <div class="text-2xl">📧</div>
                                            <div>
                                                <div class="font-semibold text-gray-900">Email Notifications</div>
                                                <div class="text-xs text-gray-500">Get trade alerts via email</div>
                                            </div>
                                        </div>
                                        <input type="checkbox" checked class="w-5 h-5 rounded border-gray-300 text-yellow-600">
                                    </label>
                                    <label class="flex items-center justify-between p-4 bg-white rounded-xl border border-gray-200 cursor-pointer hover:bg-gray-50">
                                        <div class="flex items-center space-x-3">
                                            <div class="text-2xl">💬</div>
                                            <div>
                                                <div class="font-semibold text-gray-900">Discord Notifications</div>
                                                <div class="text-xs text-gray-500">Get trade alerts on Discord</div>
                                            </div>
                                        </div>
                                        <input type="checkbox" checked class="w-5 h-5 rounded border-gray-300 text-yellow-600">
                                    </label>
                                    <label class="flex items-center justify-between p-4 bg-white rounded-xl border border-gray-200 cursor-pointer hover:bg-gray-50">
                                        <div class="flex items-center space-x-3">
                                            <div class="text-2xl">📱</div>
                                            <div>
                                                <div class="font-semibold text-gray-900">Telegram Notifications</div>
                                                <div class="text-xs text-gray-500">Get trade alerts on Telegram</div>
                                            </div>
                                        </div>
                                        <input type="checkbox" class="w-5 h-5 rounded border-gray-300 text-yellow-600">
                                    </label>
                                </div>
                            </div>

                            <!-- Save Button -->
                            <div class="flex justify-end pt-4">
                                <button class="btn-gradient text-white px-12 py-4 rounded-xl font-bold shadow-2xl hover:shadow-3xl transition-all transform hover:scale-105 flex items-center space-x-3">
                                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                                        <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"></path>
                                    </svg>
                                    <span>Save Configuration</span>
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Signals History Tab -->
                    <div x-show="activeTab === 'signals-history'" class="p-8">
                        <div class="flex items-center space-x-4 mb-8">
                            <div class="w-14 h-14 gradient-accent rounded-2xl flex items-center justify-center shadow-lg">
                                <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                                </svg>
                            </div>
                            <div>
                                <h2 class="text-3xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">Signals History</h2>
                                <p class="text-gray-500 mt-1 font-medium">View and filter AI trading signals by confidence score</p>
                            </div>
                        </div>

                        <!-- Filters -->
                        <div class="bg-white/50 backdrop-blur-sm border-2 border-purple-100 rounded-2xl p-6 mb-6">
                            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                                <!-- Score Range Slider -->
                                <div class="md:col-span-2">
                                    <label class="block text-sm font-semibold text-gray-700 mb-2">
                                        AI Score Range: <span x-text="Math.round(signalFilters.min_score * 100)"></span>% - <span x-text="Math.round(signalFilters.max_score * 100)"></span>%
                                    </label>
                                    <div class="flex items-center space-x-4">
                                        <input type="range" x-model.number="signalFilters.min_score" min="0" max="1" step="0.05"
                                               class="flex-1" @change="loadSignalsHistory()">
                                        <input type="range" x-model.number="signalFilters.max_score" min="0" max="1" step="0.05"
                                               class="flex-1" @change="loadSignalsHistory()">
                                    </div>
                                </div>
                                
                                <!-- Symbol Filter -->
                                <div>
                                    <label class="block text-sm font-semibold text-gray-700 mb-2">Symbol</label>
                                    <input type="text" x-model="signalFilters.symbol" placeholder="e.g. BTC/USDT"
                                           @input="loadSignalsHistory()"
                                           class="w-full px-4 py-2 rounded-lg border border-gray-300 focus:border-purple-500 focus:ring-2 focus:ring-purple-200">
                                </div>
                                
                                <!-- Direction Filter -->
                                <div>
                                    <label class="block text-sm font-semibold text-gray-700 mb-2">Direction</label>
                                    <select x-model="signalFilters.direction" @change="loadSignalsHistory()"
                                            class="w-full px-4 py-2 rounded-lg border border-gray-300 focus:border-purple-500 focus:ring-2 focus:ring-purple-200">
                                        <option value="">All</option>
                                        <option value="LONG">LONG</option>
                                        <option value="SHORT">SHORT</option>
                                    </select>
                                </div>
                            </div>
                        </div>

                        <!-- Signals Table -->
                        <div class="bg-white/50 backdrop-blur-sm border-2 border-purple-100 rounded-2xl overflow-hidden">
                            <div class="overflow-x-auto">
                                <table class="min-w-full divide-y divide-gray-200">
                                    <thead class="bg-gradient-to-r from-purple-50 to-pink-50">
                                        <tr>
                                            <th class="px-6 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Symbol</th>
                                            <th class="px-6 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">AI Score</th>
                                            <th class="px-6 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Direction</th>
                                            <th class="px-6 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Entry Price</th>
                                            <th class="px-6 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Stop Loss</th>
                                            <th class="px-6 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Take Profit</th>
                                            <th class="px-6 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Status</th>
                                            <th class="px-6 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">PnL</th>
                                            <th class="px-6 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Date</th>
                                        </tr>
                                    </thead>
                                    <tbody class="bg-white divide-y divide-gray-200">
                                        <template x-if="signalsHistory.length === 0">
                                            <tr>
                                                <td colspan="9" class="px-6 py-8 text-center text-gray-500">
                                                    <svg class="mx-auto h-12 w-12 text-gray-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                                                    </svg>
                                                    <p class="font-semibold">No signals found</p>
                                                    <p class="text-sm">Try adjusting your filters</p>
                                                </td>
                                            </tr>
                                        </template>
                                        <template x-for="signal in signalsHistory" :key="signal.id">
                                            <tr class="hover:bg-purple-50 transition-colors">
                                                <td class="px-6 py-4 whitespace-nowrap">
                                                    <span class="font-semibold text-gray-900" x-text="signal.symbol"></span>
                                                </td>
                                                <td class="px-6 py-4 whitespace-nowrap">
                                                    <div class="flex items-center">
                                                        <div class="flex-shrink-0 h-10 w-10 rounded-full flex items-center justify-center text-xs font-bold"
                                                             :class="{
                                                                'bg-green-100 text-green-800': signal.score_percent >= 80,
                                                                'bg-yellow-100 text-yellow-800': signal.score_percent >= 60 && signal.score_percent < 80,
                                                                'bg-orange-100 text-orange-800': signal.score_percent < 60
                                                             }">
                                                            <span x-text="signal.score_percent + '%'"></span>
                                                        </div>
                                                    </div>
                                                </td>
                                                <td class="px-6 py-4 whitespace-nowrap">
                                                    <span class="px-3 py-1 rounded-full text-xs font-semibold"
                                                          :class="signal.direction === 'LONG' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'"
                                                          x-text="signal.direction"></span>
                                                </td>
                                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900" x-text="'$' + (signal.entry_price ? signal.entry_price.toFixed(4) : 'N/A')"></td>
                                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900" x-text="'$' + (signal.stop_loss ? signal.stop_loss.toFixed(4) : 'N/A')"></td>
                                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900" x-text="'$' + (signal.take_profit_1 ? signal.take_profit_1.toFixed(4) : 'N/A')"></td>
                                                <td class="px-6 py-4 whitespace-nowrap">
                                                    <span class="px-3 py-1 rounded-full text-xs font-semibold"
                                                          :class="{
                                                              'bg-blue-100 text-blue-800': signal.is_active,
                                                              'bg-green-100 text-green-800': signal.is_executed && !signal.is_active,
                                                              'bg-gray-100 text-gray-800': !signal.is_active && !signal.is_executed
                                                          }"
                                                          x-text="signal.is_executed ? 'Executed' : (signal.is_active ? 'Active' : 'Inactive')"></span>
                                                </td>
                                                <td class="px-6 py-4 whitespace-nowrap">
                                                    <span class="text-sm font-semibold"
                                                          :class="signal.realized_pnl > 0 ? 'text-green-600' : signal.realized_pnl < 0 ? 'text-red-600' : 'text-gray-500'"
                                                          x-text="signal.realized_pnl ? '$' + signal.realized_pnl.toFixed(2) : '-'"></span>
                                                </td>
                                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500" x-text="new Date(signal.created_at).toLocaleDateString()"></td>
                                            </tr>
                                        </template>
                                    </tbody>
                                </table>
                            </div>
                            
                            <!-- Pagination -->
                            <div class="bg-gray-50 px-6 py-3 flex items-center justify-between border-t border-gray-200">
                                <div class="text-sm text-gray-700">
                                    Showing <span class="font-semibold" x-text="signalsHistory.length"></span> of 
                                    <span class="font-semibold" x-text="signalsTotalCount"></span> signals
                                </div>
                                <div class="flex space-x-2">
                                    <button @click="signalFilters.offset = Math.max(0, signalFilters.offset - signalFilters.limit); loadSignalsHistory()"
                                            :disabled="signalFilters.offset === 0"
                                            class="px-4 py-2 border rounded-lg text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100">
                                        Previous
                                    </button>
                                    <button @click="signalFilters.offset += signalFilters.limit; loadSignalsHistory()"
                                            :disabled="signalFilters.offset + signalFilters.limit >= signalsTotalCount"
                                            class="px-4 py-2 border rounded-lg text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100">
                                        Next
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>

        <script>
            function settingsApp() {
                return {
                    activeTab: 'api-keys',
                    showAddForm: false,
                    apiKeys: [],
                    newApiKey: {
                        api_name: '',
                        api_key: '',
                        api_secret: '',
                        account_type: 'futures',
                        test_mode: false,
                        max_position_size_usd: 1000,
                        leverage: 10,
                        max_daily_trades: 5,
                        max_risk_per_trade: 2,
                        auto_trade_enabled: false
                    },
                    
                    // Signals History Data
                    signalsHistory: [],
                    signalsTotalCount: 0,
                    signalFilters: {
                        min_score: 0.0,
                        max_score: 1.0,
                        symbol: '',
                        direction: '',
                        days: 7,
                        limit: 50,
                        offset: 0
                    },
                    
                    async init() {
                        await this.loadApiKeys();
                    },
                    
                    async loadSignalsHistory() {
                        try {
                            const params = new URLSearchParams({
                                min_score: this.signalFilters.min_score,
                                max_score: this.signalFilters.max_score,
                                days: this.signalFilters.days,
                                limit: this.signalFilters.limit,
                                offset: this.signalFilters.offset
                            });
                            
                            if (this.signalFilters.symbol) {
                                params.append('symbol', this.signalFilters.symbol);
                            }
                            if (this.signalFilters.direction) {
                                params.append('direction', this.signalFilters.direction);
                            }
                            
                            const response = await fetch('/api/signals/history?' + params, {
                                credentials: 'include'
                            });
                            
                            if (response.ok) {
                                const data = await response.json();
                                this.signalsHistory = data.signals || [];
                                this.signalsTotalCount = data.total || 0;
                                console.log(`Loaded ${this.signalsHistory.length} signals (${this.signalsTotalCount} total)`);
                            } else {
                                console.error('Failed to load signals history:', response.status);
                                this.signalsHistory = [];
                                this.signalsTotalCount = 0;
                            }
                        } catch (error) {
                            console.error('Error loading signals history:', error);
                            this.signalsHistory = [];
                            this.signalsTotalCount = 0;
                        }
                    },
                    
                    async loadApiKeys() {
                        try {
                            const response = await fetch('/api/bot/multi-account/api-keys', { credentials: 'include' });
                            if (response.ok) {
                                const data = await response.json();
                                // Handle both array response and object with api_keys property
                                this.apiKeys = Array.isArray(data) ? data : (data.api_keys || []);
                                
                                // Ensure each API key has an 'id' field (some APIs might use 'api_key_id')
                                this.apiKeys = this.apiKeys.map(key => {
                                    if (!key.id && key.api_key_id) {
                                        key.id = key.api_key_id;
                                    }
                                    return key;
                                });
                                
                                console.log('Loaded API keys:', this.apiKeys.length);
                                console.log('API Keys structure:', this.apiKeys.length > 0 ? this.apiKeys[0] : 'No keys found');
                            }
                        } catch (error) {
                            console.error('Error loading API keys:', error);
                        }
                    },
                    
                    async addApiKey() {
                        try {
                            const response = await fetch('/api/bot/multi-account/api-keys', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                credentials: 'include',
                                body: JSON.stringify(this.newApiKey)
                            });
                            if (response.ok) {
                                await this.loadApiKeys();
                                this.showAddForm = false;
                                this.resetNewApiKeyForm();
                                alert('API Key added successfully!');
                            }
                        } catch (error) {
                            console.error('Error adding API key:', error);
                            alert('Error adding API key');
                        }
                    },
                    
                    async verifyApiKey(id) {
                        if (!id || id === undefined) {
                            console.error('API Key ID is undefined or missing');
                            alert('Error: API Key ID is missing. Please refresh the page and try again.');
                            return;
                        }
                        try {
                            console.log('Verifying API key with ID:', id);
                            const response = await fetch(`/api/bot/multi-account/api-keys/${id}/verify`, {
                                method: 'POST',
                                credentials: 'include'
                            });
                            const data = await response.json();
                            if (response.ok) {
                                alert('API Key verified successfully!');
                                await this.loadApiKeys();
                            } else {
                                alert('Verification failed: ' + data.detail);
                            }
                        } catch (error) {
                            console.error('Error verifying API key:', error);
                            alert('Error verifying API key: ' + error.message);
                        }
                    },
                    
                    async getAccountBalance(id) {
                        if (!id || id === undefined) {
                            console.error('API Key ID is undefined or missing');
                            alert('Error: API Key ID is missing. Please refresh the page and try again.');
                            return;
                        }
                        try {
                            console.log('Getting balance for API key with ID:', id);
                            const response = await fetch(`/api/bot/multi-account/accounts/${id}/balance`, {
                                credentials: 'include'
                            });
                            if (response.ok) {
                                const data = await response.json();
                                alert(`Balance: $${data.balance.total}`);
                                await this.loadApiKeys();
                            } else {
                                const data = await response.json();
                                alert('Error getting balance: ' + (data.detail || 'Unknown error'));
                            }
                        } catch (error) {
                            console.error('Error getting balance:', error);
                            alert('Error getting balance: ' + error.message);
                        }
                    },
                    
                    async toggleAutoTrade(id, enabled) {
                        if (!id || id === undefined) {
                            console.error('API Key ID is undefined or missing');
                            alert('Error: API Key ID is missing. Please refresh the page and try again.');
                            return;
                        }
                        try {
                            console.log('Toggling auto-trade for API key with ID:', id);
                            const response = await fetch(`/api/bot/multi-account/api-keys/${id}`, {
                                method: 'PATCH',
                                headers: { 'Content-Type': 'application/json' },
                                credentials: 'include',
                                body: JSON.stringify({ auto_trade_enabled: enabled })
                            });
                            if (response.ok) {
                                await this.loadApiKeys();
                            } else {
                                const data = await response.json();
                                alert('Error toggling auto-trade: ' + (data.detail || 'Unknown error'));
                            }
                        } catch (error) {
                            console.error('Error toggling auto-trade:', error);
                            alert('Error toggling auto-trade: ' + error.message);
                        }
                    },
                    
                    async deleteApiKey(id) {
                        if (!id || id === undefined) {
                            console.error('API Key ID is undefined or missing');
                            alert('Error: API Key ID is missing. Please refresh the page and try again.');
                            return;
                        }
                        if (!confirm('Are you sure you want to delete this API key?')) return;
                        try {
                            console.log('Deleting API key with ID:', id);
                            const response = await fetch(`/api/bot/multi-account/api-keys/${id}`, {
                                method: 'DELETE',
                                credentials: 'include'
                            });
                            if (response.ok) {
                                alert('API Key deleted successfully!');
                                await this.loadApiKeys();
                            } else {
                                const data = await response.json();
                                alert('Error deleting API key: ' + (data.detail || 'Unknown error'));
                            }
                        } catch (error) {
                            console.error('Error deleting API key:', error);
                            alert('Error deleting API key: ' + error.message);
                        }
                    },
                    
                    resetNewApiKeyForm() {
                        this.newApiKey = {
                            api_name: '',
                            api_key: '',
                            api_secret: '',
                            account_type: 'futures',
                            test_mode: false,
                            max_position_size_usd: 1000,
                            leverage: 10,
                            max_daily_trades: 5,
                            max_risk_per_trade: 2,
                            auto_trade_enabled: false
                        };
                    }
                }
            }
        </script>
    </body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the main dashboard."""
    # Check if user is authenticated
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <!-- Google tag (gtag.js) -->
        <script async src="https://www.googletagmanager.com/gtag/js?id=G-R48BYVFMH2"></script>
        <script>
          window.dataLayer = window.dataLayer || [];
          function gtag(){dataLayer.push(arguments);}
          gtag('js', new Date());

          gtag('config', 'G-R48BYVFMH2');
        </script>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Winu Bot Dashboard - AI Trading Control</title>
        <link href="/static/styles.css" rel="stylesheet">
        <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Inter', sans-serif; }
            .gradient-bg { background: linear-gradient(135deg, #1e40af 0%, #7c3aed 50%, #ec4899 100%); }
            .glass-effect { backdrop-filter: blur(10px); background: rgba(255, 255, 255, 0.1); }
            .winu-primary { background: linear-gradient(135deg, #1e40af 0%, #7c3aed 100%); }
            .winu-secondary { background: linear-gradient(135deg, #7c3aed 0%, #ec4899 100%); }
            .winu-accent { background: linear-gradient(135deg, #ec4899 0%, #f59e0b 100%); }
            .card-hover { transition: all 0.3s ease; }
            .card-hover:hover { transform: translateY(-2px); box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04); }
            .live-pulse { animation: livePulse 2s ease-in-out infinite; }
            [x-cloak] { display: none !important; }
            .modal-visible { display: block !important; }
            @keyframes livePulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            .live-indicator { 
                background: linear-gradient(90deg, #10b981, #059669, #10b981);
                background-size: 200% 100%;
                animation: liveFlow 3s linear infinite;
            }
            @keyframes liveFlow {
                0% { background-position: 200% 0; }
                100% { background-position: -200% 0; }
            }
        </style>
    </head>
    <body class="bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50">
        <div x-data="tradingBot()" class="min-h-screen">
            <!-- Header -->
            <header class="bg-white/80 backdrop-blur-md shadow-lg border-b border-white/20 sticky top-0 z-50">
                <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div class="flex justify-between items-center py-4">
                        <!-- Left side: Logo and Title -->
                        <div class="flex items-center space-x-4">
                            <div class="w-10 h-10 winu-primary rounded-xl flex items-center justify-center shadow-lg">
                                    <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                                    </svg>
                                </div>
                                <div>
                                    <h1 class="text-2xl font-bold text-gray-900">Winu Bot Dashboard</h1>
                                <div class="flex items-center space-x-3">
                                    <div class="flex items-center space-x-2">
                                        <div class="w-3 h-3 rounded-full live-indicator" 
                                             x-show="botStatus.is_running"></div>
                                        <div class="w-3 h-3 rounded-full bg-red-500" 
                                             x-show="!botStatus.is_running"></div>
                                        <span class="text-sm font-semibold" 
                                              :class="botStatus.is_running ? 'text-green-600' : 'text-red-600'"
                                              x-text="botStatus.is_running ? 'LIVE TRADING' : 'STOPPED'"></span>
                                    </div>
                                    <div class="text-xs text-gray-500" x-show="botStatus.is_running">
                                        <span x-text="'Last update: ' + new Date().toLocaleTimeString()"></span>
                                    </div>
                                </div>
                        </div>
                        </div>
                        
                        <!-- Right side: Action Buttons -->
                        <div class="flex items-center space-x-3">
                            <a href="/settings" x-show="isAdmin"
                               style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important; color: #ffffff !important;"
                               class="px-6 py-3 rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl flex items-center space-x-2 font-bold transform hover:scale-105">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                                </svg>
                                <span>Settings</span>
                            </a>
                            <div class="h-8 w-px bg-gray-300"></div>
                            <a href="/logout" 
                               class="bg-slate-700 text-white px-6 py-3 rounded-xl hover:bg-slate-800 transition-all duration-300 shadow-lg flex items-center space-x-2 font-semibold border-2 border-slate-600"
                               style="background-color: #374151 !important; color: white !important;">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path>
                                </svg>
                                <span style="color: white !important;">Logout</span>
                            </a>
                        </div>
                    </div>
                </div>
            </header>

            <!-- Main Content -->
            <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <!-- Stats Grid -->
                <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
                    <!-- Total PnL Card -->
                    <div class="bg-white/80 backdrop-blur-sm rounded-xl shadow-lg border border-white/20 p-4 card-hover">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center space-x-4">
                                <div class="p-2 winu-primary rounded-lg shadow-md">
                                    <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
                                    </svg>
                                </div>
                                <div>
                                    <p class="text-xs sm:text-sm font-medium text-gray-600">Total PnL</p>
                                    <p class="text-lg sm:text-2xl font-bold" 
                                       :class="stats.total_realized_pnl > 0 ? 'text-green-600' : 'text-red-600'"
                                       x-text="'$' + stats.total_realized_pnl.toFixed(2)"></p>
                                </div>
                            </div>
                            <div class="text-right">
                                <div class="w-3 h-3 rounded-full" 
                                     :class="stats.total_realized_pnl > 0 ? 'bg-green-500' : 'bg-red-500'"></div>
                            </div>
                        </div>
                    </div>

                    <!-- Win Rate Card -->
                    <div class="bg-white/80 backdrop-blur-sm rounded-xl shadow-lg border border-white/20 p-4 card-hover">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center space-x-4">
                                <div class="p-2 sm:p-3 bg-gradient-to-r from-green-500 to-green-600 rounded-xl shadow-lg">
                                    <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                    </svg>
                                </div>
                                <div>
                                    <p class="text-xs sm:text-sm font-medium text-gray-600">Win Rate</p>
                                    <p class="text-lg sm:text-2xl font-bold text-gray-900" x-text="stats.win_rate.toFixed(1) + '%'"></p>
                                </div>
                            </div>
                            <div class="text-right">
                                <div class="w-3 h-3 rounded-full bg-green-500"></div>
                            </div>
                        </div>
                    </div>

                    <!-- Total Trades Card -->
                    <div class="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border border-white/20 p-6 card-hover">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center space-x-4">
                                <div class="p-3 winu-primary rounded-xl shadow-lg">
                                    <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                                    </svg>
                                </div>
                                <div>
                                    <p class="text-xs font-medium text-gray-600">Total Trades</p>
                                    <p class="text-lg font-bold text-gray-900" x-text="stats.total_trades"></p>
                                </div>
                            </div>
                            <div class="text-right">
                                <div class="w-3 h-3 rounded-full bg-purple-500"></div>
                            </div>
                        </div>
                    </div>

                    <!-- Uptime Card -->
                    <div class="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border border-white/20 p-6 card-hover">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center space-x-4">
                                <div class="p-3 bg-gradient-to-r from-orange-500 to-orange-600 rounded-xl shadow-lg">
                                    <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                    </svg>
                                </div>
                                <div>
                                    <p class="text-xs font-medium text-gray-600">Uptime</p>
                                    <p class="text-lg font-bold text-gray-900" x-text="formatUptime(botStatus.uptime)"></p>
                                </div>
                            </div>
                            <div class="text-right">
                                <div class="w-3 h-3 rounded-full bg-orange-500 animate-pulse"></div>
                            </div>
                        </div>
                    </div>

                    <!-- Spot Balance Card -->
                    <div class="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border border-white/20 p-6 card-hover">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center space-x-4">
                                <div class="p-3 winu-secondary rounded-xl shadow-lg">
                                    <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 1.343-3 3s1.343 3 3 3 3-1.343 3-3-1.343-3-3-3z"></path>
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 1v6m0 6v6m11-7h-6m-6 0H1"></path>
                                    </svg>
                                </div>
                                <div>
                                    <p class="text-xs font-medium text-gray-600">Spot Balance</p>
                                    <p class="text-lg font-bold text-green-600" x-text="Number(balances.spot?.free_balance || 0).toFixed(2) + ' ' + (balances.spot?.currency || 'USDT')"></p>
                                    <p class="text-xs text-gray-500" x-text="'Total: $' + Number(balances.spot?.total_balance || 0).toFixed(2)"></p>
                                </div>
                            </div>
                            <div class="text-right">
                                <div class="w-3 h-3 rounded-full bg-green-500"></div>
                            </div>
                        </div>
                    </div>

                    <!-- Futures Balance Card -->
                    <div class="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border border-white/20 p-6 card-hover">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center space-x-4">
                                <div class="p-3 winu-primary rounded-xl shadow-lg">
                                    <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
                                    </svg>
                                </div>
                                <div>
                                    <p class="text-xs font-medium text-gray-600">Futures Balance</p>
                                    <p class="text-lg font-bold text-blue-600" x-text="Number(balances.futures?.free_balance || 0).toFixed(2) + ' ' + (balances.futures?.currency || 'USDT')"></p>
                                    <p class="text-xs text-gray-500" x-text="'Total: $' + Number(balances.futures?.total_balance || 0).toFixed(2)"></p>
                                </div>
                            </div>
                            <div class="text-right">
                                <div class="w-3 h-3 rounded-full bg-blue-500"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Real-time Activity Feed -->
                <div class="bg-white/80 backdrop-blur-sm rounded-xl shadow-lg border border-white/20 overflow-hidden mb-6">
                    <div class="px-4 py-3 winu-primary">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center space-x-3">
                                <div class="w-3 h-3 rounded-full live-indicator"></div>
                                <h3 class="text-base font-semibold text-white">Real-time Activity</h3>
                            </div>
                            <div class="text-xs text-white/80">
                                <span x-text="'Last signal: ' + ((recentActivity && recentActivity.length > 0) ? recentActivity[0].time : 'None')"></span>
                            </div>
                        </div>
                    </div>
                    <div class="px-4 py-3 max-h-32 overflow-y-auto">
                        <div class="space-y-2" x-show="recentActivity && recentActivity.length > 0">
                            <template x-for="activity in (recentActivity || []).slice(0, 5)" :key="activity.id">
                                <div class="flex items-center justify-between text-sm">
                                    <div class="flex items-center space-x-2">
                                        <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                                        <span class="text-gray-700" x-text="activity.message"></span>
                                    </div>
                                    <span class="text-xs text-gray-500" x-text="activity.time"></span>
                                </div>
                            </template>
                        </div>
                        <div class="text-sm text-gray-500 italic" x-show="!recentActivity || recentActivity.length === 0">
                            No recent activity...
                        </div>
                    </div>
                </div>

                <!-- Spot Positions Table -->
                <div class="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border border-white/20 overflow-hidden">
                    <div class="px-6 py-4 bg-gradient-to-r from-green-500 to-green-600">
                        <div class="flex items-center space-x-4">
                            <div class="p-2 bg-white/20 rounded-lg">
                                <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 1.343-3 3s1.343 3 3 3 3-1.343 3-3-1.343-3-3-3z"></path>
                                </svg>
                            </div>
                            <h3 class="text-base font-semibold text-white">Spot Trading Positions</h3>
                            <div class="ml-auto">
                                <span class="px-3 py-1 bg-white/20 rounded-full text-sm text-white font-medium" x-text="spotPositions.length + ' Active'"></span>
                            </div>
                        </div>
                    </div>
                    <div class="overflow-x-auto">
                        <table class="min-w-full">
                            <thead class="bg-gray-50/50">
                                <tr>
                                    <th class="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Symbol</th>
                                    <th class="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Side</th>
                                    <th class="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Entry Price</th>
                                    <th class="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Current Price</th>
                                    <th class="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Quantity</th>
                                    <th class="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">PnL</th>
                                    <th class="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Actions</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-gray-200/50">
                                <template x-for="position in spotPositions" :key="position.id">
                                    <tr class="hover:bg-gray-50/50 transition-colors duration-200">
                                        <td class="px-6 py-4 whitespace-nowrap">
                                            <div class="flex items-center space-x-3">
                                                <div class="w-8 h-8 bg-gradient-to-r from-green-500 to-green-600 rounded-lg flex items-center justify-center">
                                                    <span class="text-white font-bold text-sm" x-text="position.symbol.split('/')[0]"></span>
                                                </div>
                                                <div>
                                                <span class="text-sm font-semibold text-gray-900" x-text="position.symbol"></span>
                                                    <div class="text-xs text-gray-500">SPOT</div>
                                                </div>
                                            </div>
                                        </td>
                                        <td class="px-6 py-4 whitespace-nowrap">
                                            <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium"
                                                  :class="position.side === 'LONG' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'"
                                                  x-text="position.side"></span>
                                        </td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900" x-text="'$' + position.entry_price.toFixed(2)"></td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900" x-text="'$' + position.current_price.toFixed(2)"></td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900" x-text="position.quantity.toFixed(6)"></td>
                                        <td class="px-6 py-4 whitespace-nowrap">
                                            <div class="flex items-center space-x-2">
                                                <div class="w-2 h-2 rounded-full" 
                                                     :class="position.pnl || position.unrealized_pnl || 0 > 0 ? 'bg-green-500' : 'bg-red-500'"></div>
                                                <span class="text-sm font-semibold" 
                                                      :class="position.pnl || position.unrealized_pnl || 0 > 0 ? 'text-green-600' : 'text-red-600'"
                                                      x-text="'$' + (position.pnl || position.unrealized_pnl || 0).toFixed(2) + ' (' + (position.pnl_percentage || 0).toFixed(1) + '%)'"></span>
                                            </div>
                                        </td>
                                        <td class="px-6 py-4 whitespace-nowrap">
                                            <button @click="closePosition(position.id)" 
                                                    class="bg-gradient-to-r from-red-500 to-red-600 text-white px-4 py-2 rounded-lg hover:from-red-600 hover:to-red-700 transition-all duration-200 shadow-lg hover:shadow-xl flex items-center space-x-2">
                                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                                </svg>
                                                <span>Close</span>
                                            </button>
                                        </td>
                                    </tr>
                                </template>
                                <template x-if="spotPositions.length === 0">
                                    <tr>
                                        <td colspan="7" class="px-6 py-12 text-center">
                                            <div class="flex flex-col items-center space-y-4">
                                                <div class="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
                                                    <svg class="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 1.343-3 3s1.343 3 3 3 3-1.343 3-3-1.343-3-3-3z"></path>
                                                    </svg>
                                                </div>
                                                <div>
                                                    <h3 class="text-lg font-medium text-gray-900">No Active Spot Positions</h3>
                                                    <p class="text-gray-500">High confidence signals will be traded on spot</p>
                                                </div>
                                            </div>
                                        </td>
                                    </tr>
                                </template>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Futures Positions Table -->
                <div class="bg-white/80 backdrop-blur-sm rounded-xl shadow-lg border border-white/20 overflow-hidden mt-4">
                    <div class="px-4 py-3 winu-primary">
                        <div class="flex items-center space-x-4">
                            <div class="p-2 bg-white/20 rounded-lg">
                                <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
                                </svg>
                            </div>
                            <h3 class="text-base font-semibold text-white">Futures Trading Positions</h3>
                            <div class="ml-auto">
                                <span class="px-3 py-1 bg-white/20 rounded-full text-sm text-white font-medium" x-text="futuresPositions.length + ' Active'"></span>
                            </div>
                        </div>
                    </div>
                    <div class="overflow-x-auto">
                        <table class="min-w-full">
                            <thead class="bg-gray-50/50">
                                <tr>
                                    <th class="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Symbol</th>
                                    <th class="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Side</th>
                                    <th class="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Entry Price</th>
                                    <th class="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Current Price</th>
                                    <th class="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Quantity</th>
                                    <th class="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Leverage</th>
                                    <th class="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">PnL</th>
                                    <th class="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Actions</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-gray-200/50">
                                <template x-for="position in futuresPositions" :key="position.id">
                                    <tr class="hover:bg-gray-50/50 transition-colors duration-200">
                                        <td class="px-6 py-4 whitespace-nowrap">
                                            <div class="flex items-center space-x-3">
                                                <div class="w-8 h-8 winu-primary rounded-lg flex items-center justify-center">
                                                    <span class="text-white font-bold text-sm" x-text="position.symbol.split('/')[0]"></span>
                                                </div>
                                                <div>
                                                    <span class="text-sm font-semibold text-gray-900" x-text="position.symbol"></span>
                                                    <div class="text-xs text-gray-500">FUTURES</div>
                                                </div>
                                            </div>
                                        </td>
                                        <td class="px-6 py-4 whitespace-nowrap">
                                            <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium"
                                                  :class="position.side === 'LONG' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'"
                                                  x-text="position.side"></span>
                                        </td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900" x-text="'$' + position.entry_price.toFixed(2)"></td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900" x-text="'$' + position.current_price.toFixed(2)"></td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900" x-text="position.quantity.toFixed(6)"></td>
                                        <td class="px-6 py-4 whitespace-nowrap">
                                            <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                                                  x-text="(position.leverage || 1) + 'x'"></span>
                                        </td>
                                        <td class="px-6 py-4 whitespace-nowrap">
                                            <div class="flex items-center space-x-2">
                                                <div class="w-2 h-2 rounded-full" 
                                                     :class="position.pnl || position.unrealized_pnl || 0 > 0 ? 'bg-green-500' : 'bg-red-500'"></div>
                                                <span class="text-sm font-semibold" 
                                                      :class="position.pnl || position.unrealized_pnl || 0 > 0 ? 'text-green-600' : 'text-red-600'"
                                                      x-text="'$' + (position.pnl || position.unrealized_pnl || 0).toFixed(2) + ' (' + (position.pnl_percentage || 0).toFixed(1) + '%)'"></span>
                                            </div>
                                        </td>
                                        <td class="px-6 py-4 whitespace-nowrap">
                                            <button @click="closePosition(position.id)" 
                                                    class="bg-gradient-to-r from-red-500 to-red-600 text-white px-4 py-2 rounded-lg hover:from-red-600 hover:to-red-700 transition-all duration-200 shadow-lg hover:shadow-xl flex items-center space-x-2">
                                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                                </svg>
                                                <span>Close</span>
                                            </button>
                                        </td>
                                    </tr>
                                </template>
                                <template x-if="futuresPositions.length === 0">
                                    <tr>
                                        <td colspan="8" class="px-6 py-12 text-center">
                                            <div class="flex flex-col items-center space-y-4">
                                                <div class="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
                                                    <svg class="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
                                                    </svg>
                                                </div>
                                                <div>
                                                    <h3 class="text-lg font-medium text-gray-900">No Active Futures Positions</h3>
                                                    <p class="text-gray-500">Medium confidence signals will be traded on futures</p>
                                                </div>
                                            </div>
                                        </td>
                                    </tr>
                                </template>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Today's AI Signals Section -->
                <div class="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border border-white/20 overflow-hidden mt-6">
                    <div class="px-6 py-4 bg-gradient-to-r from-purple-500 to-pink-500">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center space-x-4">
                                <div class="p-2 bg-white/20 rounded-lg">
                                    <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                                    </svg>
                                </div>
                                <h3 class="text-lg font-bold text-white">🤖 Today's AI Signals</h3>
                            </div>
                            <div class="flex items-center space-x-4">
                                <!-- Score Filter Slider -->
                                <div class="flex items-center space-x-3 bg-white/20 rounded-lg px-4 py-2">
                                    <span class="text-white text-sm font-semibold">Min Score:</span>
                                    <input type="range" x-model.number="signalScoreFilter" min="0" max="100" step="5"
                                           @change="loadTodaySignals()"
                                           class="w-32">
                                    <span class="text-white text-sm font-bold min-w-[3rem]" x-text="signalScoreFilter + '%'"></span>
                                </div>
                                <span class="px-3 py-1 bg-white/20 rounded-full text-sm text-white font-medium" x-text="todaySignals.length + ' Signals'"></span>
                            </div>
                        </div>
                    </div>
                    <div class="overflow-x-auto">
                        <table class="min-w-full">
                            <thead class="bg-gradient-to-r from-purple-50 to-pink-50">
                                <tr>
                                    <th class="px-6 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Symbol</th>
                                    <th class="px-6 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">AI Score</th>
                                    <th class="px-6 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Direction</th>
                                    <th class="px-6 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Entry</th>
                                    <th class="px-6 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Stop Loss</th>
                                    <th class="px-6 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Take Profit</th>
                                    <th class="px-6 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">R:R Ratio</th>
                                    <th class="px-6 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Status</th>
                                    <th class="px-6 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Time</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-gray-200/50">
                                <template x-for="signal in todaySignals" :key="signal.id">
                                    <tr class="hover:bg-purple-50/30 transition-colors duration-200">
                                        <td class="px-6 py-4 whitespace-nowrap">
                                            <span class="text-sm font-bold text-gray-900" x-text="signal.symbol"></span>
                                        </td>
                                        <td class="px-6 py-4 whitespace-nowrap">
                                            <div class="flex items-center space-x-2">
                                                <div class="w-12 h-12 rounded-full flex items-center justify-center text-sm font-bold shadow-lg"
                                                     :class="{
                                                        'bg-gradient-to-r from-green-400 to-green-600 text-white': signal.score_percent >= 80,
                                                        'bg-gradient-to-r from-yellow-400 to-yellow-600 text-white': signal.score_percent >= 70 && signal.score_percent < 80,
                                                        'bg-gradient-to-r from-orange-400 to-orange-600 text-white': signal.score_percent >= 60 && signal.score_percent < 70,
                                                        'bg-gradient-to-r from-gray-400 to-gray-600 text-white': signal.score_percent < 60
                                                     }">
                                                    <span x-text="signal.score_percent + '%'"></span>
                                                </div>
                                            </div>
                                        </td>
                                        <td class="px-6 py-4 whitespace-nowrap">
                                            <span class="px-3 py-1 rounded-full text-xs font-bold shadow-sm"
                                                  :class="signal.direction === 'LONG' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'"
                                                  x-text="signal.direction"></span>
                                        </td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900" x-text="signal.entry_price ? '$' + signal.entry_price.toFixed(4) : '-'"></td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700" x-text="signal.stop_loss ? '$' + signal.stop_loss.toFixed(4) : '-'"></td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700" x-text="signal.take_profit_1 ? '$' + signal.take_profit_1.toFixed(4) : '-'"></td>
                                        <td class="px-6 py-4 whitespace-nowrap">
                                            <span class="text-sm font-semibold text-blue-600" x-text="signal.risk_reward_ratio ? signal.risk_reward_ratio.toFixed(2) : '-'"></span>
                                        </td>
                                        <td class="px-6 py-4 whitespace-nowrap">
                                            <span class="px-3 py-1 rounded-full text-xs font-bold"
                                                  :class="{
                                                      'bg-blue-100 text-blue-800': signal.is_active && !signal.is_executed,
                                                      'bg-green-100 text-green-800': signal.is_executed,
                                                      'bg-gray-100 text-gray-800': !signal.is_active && !signal.is_executed
                                                  }"
                                                  x-text="signal.is_executed ? '✅ Executed' : (signal.is_active ? '🔵 Active' : '⚪ Inactive')"></span>
                                        </td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500" x-text="new Date(signal.created_at).toLocaleTimeString()"></td>
                                    </tr>
                                </template>
                                <template x-if="todaySignals.length === 0">
                                    <tr>
                                        <td colspan="9" class="px-6 py-12 text-center">
                                            <div class="flex flex-col items-center space-y-4">
                                                <div class="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center">
                                                    <svg class="w-8 h-8 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                                                    </svg>
                                                </div>
                                                <div>
                                                    <h3 class="text-lg font-medium text-gray-900">No Signals Today</h3>
                                                    <p class="text-gray-500">AI is analyzing the markets... signals will appear here</p>
                                                    <p class="text-sm text-gray-400 mt-2">Current filter: Minimum <span x-text="signalScoreFilter"></span>% confidence</p>
                                                </div>
                                            </div>
                                        </td>
                                    </tr>
                                </template>
                            </tbody>
                        </table>
                    </div>
                </div>
            </main>
            
            <!-- Binance API Keys Management Modal -->
            <div id="accountsModal"
                 x-show="showAccountsModal"
                 class="fixed inset-0 z-50 overflow-y-auto bg-black bg-opacity-50">
                <div class="flex items-center justify-center min-h-screen px-4 py-8">
                    <!-- Backdrop -->
                    <div class="fixed inset-0 bg-black bg-opacity-75" @click="showAccountsModal = false" style="z-index: 99998 !important;"></div>
                    
                    <!-- Modal Content -->
                    <div class="relative bg-white rounded-2xl shadow-2xl max-w-4xl w-full mx-auto overflow-hidden" style="z-index: 1000000 !important; max-height: 85vh;">
                        <div class="overflow-y-auto" style="max-height: 85vh;">
                        <!-- Header -->
                        <div class="sticky top-0 bg-gradient-to-r from-teal-600 to-cyan-600 px-6 py-4 rounded-t-2xl" style="z-index: 100000;">
                            <div class="flex items-center justify-between">
                                <div class="flex items-center space-x-3">
                                    <div class="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center">
                                        <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
                                        </svg>
                                    </div>
                                    <h2 class="text-2xl font-bold text-white">⚙️ Trading Accounts Manager</h2>
                                </div>
                                <button @click="showAccountsModal = false" class="text-white hover:bg-white/20 rounded-lg p-2 transition-colors">
                                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                    </svg>
                                </button>
                            </div>
                        </div>
                        
                        <!-- Tabs -->
                        <div class="border-b border-gray-200">
                            <div class="flex space-x-8 px-6">
                                <button @click="accountsTab = 'list'" 
                                        :class="accountsTab === 'list' ? 'border-teal-600 text-teal-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
                                        class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors">
                                    📊 My Accounts
                                </button>
                                <button @click="accountsTab = 'add'" 
                                        :class="accountsTab === 'add' ? 'border-teal-600 text-teal-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
                                        class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors">
                                    ➕ Add New Account
                                </button>
                            </div>
                        </div>
                        
                        <!-- Content -->
                        <div class="p-6">
                            <!-- List Tab -->
                            <div x-show="accountsTab === 'list'" class="space-y-4">
                                <template x-if="apiKeys.length === 0">
                                    <div class="text-center py-12">
                                        <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"></path>
                                        </svg>
                                        <h3 class="mt-2 text-sm font-medium text-gray-900">No API keys</h3>
                                        <p class="mt-1 text-sm text-gray-500">Get started by adding your first Binance API key.</p>
                                        <div class="mt-6">
                                            <button @click="accountsTab = 'add'" class="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-teal-600 hover:bg-teal-700">
                                                ➕ Add Your First API Key
                                            </button>
                                        </div>
                                    </div>
                                </template>
                                
                                <template x-for="apiKey in apiKeys" :key="apiKey.id">
                                    <div class="border border-gray-200 rounded-xl p-4 hover:shadow-md transition-shadow">
                                        <div class="flex items-start justify-between">
                                            <div class="flex-1">
                                                <div class="flex items-center space-x-3">
                                                    <h3 class="text-lg font-semibold text-gray-900" x-text="apiKey.api_name"></h3>
                                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                                                          :class="apiKey.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'"
                                                          x-text="apiKey.is_active ? 'Active' : 'Inactive'"></span>
                                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                                                          :class="apiKey.test_mode ? 'bg-yellow-100 text-yellow-800' : 'bg-blue-100 text-blue-800'"
                                                          x-text="apiKey.test_mode ? 'Testnet' : 'Live'"></span>
                                                    <span x-show="apiKey.is_verified" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                                        ✓ Verified
                                                    </span>
                                                </div>
                                                <div class="mt-2 grid grid-cols-2 gap-4 text-sm">
                                                    <div>
                                                        <span class="text-gray-500">API Key:</span>
                                                        <span class="ml-2 font-mono text-gray-900" x-text="apiKey.api_key_masked"></span>
                                                    </div>
                                                    <div>
                                                        <span class="text-gray-500">Type:</span>
                                                        <span class="ml-2 text-gray-900 uppercase" x-text="apiKey.account_type"></span>
                                                    </div>
                                                    <div>
                                                        <span class="text-gray-500">Max Position:</span>
                                                        <span class="ml-2 text-gray-900" x-text="'$' + apiKey.max_position_size_usd"></span>
                                                    </div>
                                                    <div>
                                                        <span class="text-gray-500">Leverage:</span>
                                                        <span class="ml-2 text-gray-900" x-text="apiKey.leverage + 'x'"></span>
                                                    </div>
                                                    <div x-show="apiKey.current_balance">
                                                        <span class="text-gray-500">💰 Balance:</span>
                                                        <span class="ml-2 font-semibold text-green-600" x-text="'$' + (apiKey.current_balance || 0).toFixed(2)"></span>
                                                    </div>
                                                    <div x-show="apiKey.total_pnl !== undefined">
                                                        <span class="text-gray-500">📈 Total PnL:</span>
                                                        <span class="ml-2 font-semibold" 
                                                              :class="(apiKey.total_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'"
                                                              x-text="'$' + (apiKey.total_pnl || 0).toFixed(2)"></span>
                                                    </div>
                                                    <div x-show="apiKey.trade_count !== undefined">
                                                        <span class="text-gray-500">📊 Trades:</span>
                                                        <span class="ml-2 text-gray-900" x-text="apiKey.trade_count || 0"></span>
                                                    </div>
                                                    <div x-show="apiKey.win_rate !== undefined">
                                                        <span class="text-gray-500">🎯 Win Rate:</span>
                                                        <span class="ml-2 font-semibold"
                                                              :class="(apiKey.win_rate || 0) >= 50 ? 'text-green-600' : 'text-yellow-600'"
                                                              x-text="(apiKey.win_rate || 0).toFixed(1) + '%'"></span>
                                                    </div>
                                                </div>
                                            </div>
                                            <div class="flex flex-col space-y-2 ml-4">
                                                <button @click="verifyApiKey(apiKey.id)" 
                                                        class="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                                                    Verify
                                                </button>
                                                <button @click="getAccountBalance(apiKey.id)" 
                                                        class="px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors">
                                                    Refresh Balance
                                                </button>
                                                <button @click="toggleAutoTrade(apiKey.id, !apiKey.auto_trade_enabled)" 
                                                        class="px-3 py-1.5 text-sm rounded-lg transition-colors"
                                                        :class="apiKey.auto_trade_enabled ? 'bg-yellow-600 text-white hover:bg-yellow-700' : 'bg-gray-600 text-white hover:bg-gray-700'"
                                                        x-text="apiKey.auto_trade_enabled ? 'Disable Trading' : 'Enable Trading'">
                                                </button>
                                                <button @click="deleteApiKey(apiKey.id)" 
                                                        class="px-3 py-1.5 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors">
                                                    Delete
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </template>
                            </div>
                            
                            <!-- Add New Account Tab -->
                            <div x-show="accountsTab === 'add'" class="space-y-6">
                                <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                    <div class="flex">
                                        <div class="flex-shrink-0">
                                            <svg class="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                                                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path>
                                            </svg>
                                        </div>
                                        <div class="ml-3 flex-1">
                                            <h3 class="text-sm font-medium text-blue-800">API Key Security</h3>
                                            <div class="mt-2 text-sm text-blue-700">
                                                <ul class="list-disc pl-5 space-y-1">
                                                    <li>Your API keys are encrypted and stored securely</li>
                                                    <li>Enable IP whitelist on Binance for extra security</li>
                                                    <li>Never share your API secret with anyone</li>
                                                    <li>Testnet keys are recommended for testing</li>
                                                </ul>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <form @submit.prevent="addApiKey()" class="space-y-4">
                                    <div class="grid grid-cols-2 gap-4">
                                        <div class="col-span-2">
                                            <label class="block text-sm font-medium text-gray-700">Account Name</label>
                                            <input x-model="newApiKey.api_name" type="text" required
                                                   class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                                                   placeholder="e.g., Main Trading Account">
                                        </div>
                                        
                                        <div class="col-span-2">
                                            <label class="block text-sm font-medium text-gray-700">Binance API Key</label>
                                            <input x-model="newApiKey.api_key" type="text" required
                                                   class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 font-mono"
                                                   placeholder="Your Binance API Key">
                                        </div>
                                        
                                        <div class="col-span-2">
                                            <label class="block text-sm font-medium text-gray-700">Binance API Secret</label>
                                            <input x-model="newApiKey.api_secret" type="password" required
                                                   class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 font-mono"
                                                   placeholder="Your Binance API Secret">
                                        </div>
                                        
                                        <div>
                                            <label class="block text-sm font-medium text-gray-700">Account Type</label>
                                            <select x-model="newApiKey.account_type"
                                                    class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500">
                                                <option value="spot">Spot Trading</option>
                                                <option value="futures">Futures Trading</option>
                                                <option value="both">Both</option>
                                            </select>
                                        </div>
                                        
                                        <div>
                                            <label class="block text-sm font-medium text-gray-700">Environment</label>
                                            <select x-model="newApiKey.test_mode"
                                                    class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500">
                                                <option :value="false">Live Trading</option>
                                                <option :value="true">Testnet</option>
                                            </select>
                                        </div>
                                        
                                        <div>
                                            <label class="block text-sm font-medium text-gray-700">Max Position Size (USD)</label>
                                            <input x-model.number="newApiKey.max_position_size_usd" type="number" step="10" min="10" required
                                                   class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500">
                                        </div>
                                        
                                        <div>
                                            <label class="block text-sm font-medium text-gray-700">Leverage</label>
                                            <input x-model.number="newApiKey.leverage" type="number" step="1" min="1" max="125" required
                                                   class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500">
                                        </div>
                                        
                                        <div>
                                            <label class="block text-sm font-medium text-gray-700">Max Daily Trades</label>
                                            <input x-model.number="newApiKey.max_daily_trades" type="number" step="1" min="1" required
                                                   class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500">
                                        </div>
                                        
                                        <div>
                                            <label class="block text-sm font-medium text-gray-700">Max Risk Per Trade (%)</label>
                                            <input x-model.number="newApiKey.max_risk_per_trade" type="number" step="0.1" min="0.1" max="10" required
                                                   class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500">
                                        </div>
                                        
                                        <div class="col-span-2">
                                            <label class="flex items-center space-x-2">
                                                <input x-model="newApiKey.auto_trade_enabled" type="checkbox"
                                                       class="rounded border-gray-300 text-indigo-600 shadow-sm focus:border-indigo-500 focus:ring-indigo-500">
                                                <span class="text-sm font-medium text-gray-700">Enable Auto Trading</span>
                                            </label>
                                        </div>
                                    </div>
                                    
                                    <div class="flex justify-end space-x-3 pt-4">
                                        <button type="button" @click="resetNewApiKeyForm()" 
                                                class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors">
                                            🔄 Reset
                                        </button>
                                        <button type="submit"
                                                class="px-6 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors font-semibold shadow-lg">
                                            ✅ Add API Key
                                        </button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            function tradingBot() {
                return {
                    botStatus: {
                        is_running: false,
                        test_mode: true,
                        uptime: 0
                    },
                    stats: {
                        total_realized_pnl: 0,
                        win_rate: 0,
                        total_trades: 0
                    },
                    recentActivity: [],
                    lastUpdateTime: new Date(),
                    balances: {
                        spot: {
                        free_balance: 0,
                        total_balance: 0,
                        currency: 'USDT'
                        },
                        futures: {
                            free_balance: 0,
                            total_balance: 0,
                            currency: 'USDT'
                        }
                    },
                    positions: [],
                    spotPositions: [],
                    futuresPositions: [],
                    
                    // Today's Signals
                    todaySignals: [],
                    signalScoreFilter: 0,  // Default: show all signals
                    
                    // User & Admin
                    isAdmin: false,
                    
                    // API Keys Management
                    showAccountsModal: false,
                    accountsTab: 'list',
                    apiKeys: [],
                    newApiKey: {
                        api_name: '',
                        api_key: '',
                        api_secret: '',
                        account_type: 'futures',
                        test_mode: false,
                        max_position_size_usd: 1000,
                        leverage: 10,
                        max_daily_trades: 5,
                        max_risk_per_trade: 2,
                        max_daily_loss: 5,
                        stop_trading_on_loss: true,
                        position_sizing_mode: 'fixed',
                        position_size_value: 100,
                        auto_trade_enabled: false
                    },
                    
                    async init() {
                        console.log('🚀 Dashboard initializing...');
                        await this.loadData();
                        await this.loadApiKeys();
                        await this.loadTodaySignals();
                        console.log('✅ Dashboard initialized. showAccountsModal:', this.showAccountsModal);
                        
                        // Check if user is admin (from session)
                        try {
                            const response = await fetch('/api/current-user', { credentials: 'include' });
                            if (response.ok) {
                                const userData = await response.json();
                                this.isAdmin = userData.is_admin || false;
                                console.log('User is admin:', this.isAdmin);
                            }
                        } catch (error) {
                            console.error('Error checking admin status:', error);
                            this.isAdmin = false;
                        }
                        
                        // Use a more robust interval with error handling and cleanup
                        this.updateInterval = setInterval(() => {
                            // Only update if page is visible to save resources
                            if (!document.hidden) {
                                this.loadData().catch(error => {
                                    console.error('Error in loadData:', error);
                                    this.addActivity('Data loading error: ' + error.message);
                                });
                            }
                        }, 3000); // Reduced frequency to 3 seconds to prevent overload
                        
                        // Pause updates when tab is not visible to prevent resource waste
                        document.addEventListener('visibilitychange', () => {
                            if (document.hidden) {
                                console.log('Tab hidden, pausing updates');
                            } else {
                                console.log('Tab visible, resuming updates');
                                // Load fresh data when tab becomes visible again
                                this.loadData().catch(error => {
                                    console.error('Error in loadData after visibility change:', error);
                                });
                            }
                        });
                    },
                    
                    async loadData() {
                        try {
                            // Try authenticated endpoint first
                            let response = await fetch('/api/status', {
                                credentials: 'include'
                            });
                            
                            let data;
                            if (!response.ok) {
                                // Fallback to public endpoint
                                response = await fetch('/api/public-status');
                                if (!response.ok) {
                                    console.error('API error:', response.status, response.statusText);
                                    this.addActivity('Error loading data: API returned ' + response.status);
                                    return;
                                }
                            }
                            
                            data = await response.json();
                            
                            if (!data) {
                                console.error('Invalid response data:', data);
                                this.addActivity('Error loading data: Invalid response format');
                                return;
                            }
                            
                            // Handle both authenticated and public response formats
                            if (data.bot_status) {
                                // Authenticated response format
                                this.botStatus = data.bot_status;
                                this.stats = data.stats || {};
                                this.positions = data.positions || [];
                            } else if (data.open_positions !== undefined) {
                                // Public response format
                                this.botStatus = {
                                    is_running: data.bot_status === 'running',
                                    test_mode: false,
                                    uptime: 3600
                                };
                                this.stats = {
                                    total_realized_pnl: data.total_pnl || 0,
                                    win_rate: data.win_rate || 0,
                                    total_trades: data.total_trades || 0
                                };
                                this.positions = data.latest_position ? [data.latest_position] : [];
                            } else {
                                console.error('Unknown response format:', data);
                                this.addActivity('Error loading data: Unknown response format');
                                return;
                            }
                            
                            // Add activity log when bot status changes
                            if (this.botStatus.is_running) {
                                this.addActivity('Bot is running and monitoring markets');
                            }
                            
                            // Separate positions by market type
                            const oldSpotCount = this.spotPositions.length;
                            const oldFuturesCount = this.futuresPositions.length;
                            this.spotPositions = this.positions.filter(p => p.market_type === 'spot');
                            this.futuresPositions = this.positions.filter(p => p.market_type === 'futures');
                            
                            // Add activity log for position changes
                            if (this.spotPositions.length !== oldSpotCount) {
                                this.addActivity(`Spot positions updated: ${this.spotPositions.length} positions`);
                            }
                            if (this.futuresPositions.length !== oldFuturesCount) {
                                this.addActivity(`Futures positions updated: ${this.futuresPositions.length} positions`);
                            }
                            
                            // Load dual balances with better error handling
                            try {
                                let balanceResponse = await fetch('/api/public-balances', {
                                    credentials: 'include',
                                    timeout: 10000  // 10 second timeout
                                });
                                
                                if (!balanceResponse.ok) {
                                    // Fallback to public balance endpoint
                                    balanceResponse = await fetch('/api/public-balances', {
                                        timeout: 10000
                                    });
                                }
                                
                                if (balanceResponse.ok) {
                                    const balanceData = await balanceResponse.json();
                                    this.balances = balanceData.balances || balanceData;
                                    this.addActivity('Account balances updated');
                                } else {
                                    throw new Error(`Balance API failed with status ${balanceResponse.status}`);
                                }
                            } catch (balanceError) {
                                console.error('Error loading dual balances:', balanceError);
                                // Set default balances and don't spam activity log
                                if (!this.balances || this.balances.spot?.free_balance === 0) {
                                    this.balances = {
                                        spot: { free_balance: 0, total_balance: 0, currency: 'USDT' },
                                        futures: { free_balance: 0, total_balance: 0, currency: 'USDT' }
                                    };
                                    this.addActivity('Account balances unavailable - using defaults');
                                }
                            }
                            
                            this.lastUpdateTime = new Date();
                        } catch (error) {
                            console.error('Error loading data:', error);
                            this.addActivity('Error loading data: ' + error.message);
                            
                            // Ensure botStatus has default values if it's undefined
                            if (!this.botStatus) {
                                this.botStatus = {
                                    is_running: false,
                                    test_mode: true,
                                    uptime: 0
                                };
                            }
                        }
                    },
                    
                    async loadTodaySignals() {
                        try {
                            const minScore = this.signalScoreFilter / 100;  // Convert to 0-1 scale
                            // Add cache-busting parameter
                            const cacheBuster = Date.now();
                            const response = await fetch(`/api/signals/history?min_score=${minScore}&max_score=1.0&days=1&limit=100&_=${cacheBuster}`, {
                                credentials: 'include'
                            });
                            
                            if (response.ok) {
                                const data = await response.json();
                                this.todaySignals = data.signals || [];
                                console.log(`✅ Loaded ${this.todaySignals.length} signals for today (min score: ${this.signalScoreFilter}%)`);
                                
                                // Verify ordering (should be sorted by score DESC)
                                if (this.todaySignals.length > 0) {
                                    console.log(`📊 Top signal: ${this.todaySignals[0].symbol} - ${this.todaySignals[0].score_percent}%`);
                                    this.addActivity(`📊 ${this.todaySignals.length} AI signals loaded (top: ${this.todaySignals[0].score_percent}%)`);
                                }
                            } else {
                                console.error('Failed to load today signals:', response.status);
                                this.todaySignals = [];
                            }
                        } catch (error) {
                            console.error('Error loading today signals:', error);
                            this.todaySignals = [];
                        }
                    },
                    
                    addActivity(message) {
                        const now = new Date();
                        const activity = {
                            id: `activity_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                            message: message,
                            time: now.toLocaleTimeString()
                        };
                        
                        // Ensure recentActivity is initialized
                        if (!this.recentActivity) {
                            this.recentActivity = [];
                        }
                        
                        this.recentActivity.unshift(activity);
                        
                        // Keep only last 10 activities to prevent memory leaks
                        if (this.recentActivity.length > 10) {
                            this.recentActivity = this.recentActivity.slice(0, 10);
                        }
                    },
                    
                    // Add cleanup method for proper resource management
                    destroy() {
                        if (this.updateInterval) {
                            clearInterval(this.updateInterval);
                            this.updateInterval = null;
                        }
                    },
                    
                    async closePosition(positionId) {
                        try {
                            await fetch(`/api/positions/${positionId}/close`, { method: 'POST' });
                            await this.loadData();
                        } catch (error) {
                            console.error('Error closing position:', error);
                        }
                    },
                    
                    formatUptime(seconds) {
                        const hours = Math.floor(seconds / 3600);
                        const minutes = Math.floor((seconds % 3600) / 60);
                        return `${hours}h ${minutes}m`;
                    },
                    
                    // ===== API Keys Management Methods =====
                    
                    async loadApiKeys() {
                        try {
                            const response = await fetch('/api/bot/multi-account/api-keys', {
                                credentials: 'include'
                            });
                            
                            if (response.ok) {
                                const data = await response.json();
                                // Handle both array response and object with api_keys property
                                this.apiKeys = Array.isArray(data) ? data : (data.api_keys || []);
                                
                                // Ensure each API key has an 'id' field (some APIs might use 'api_key_id')
                                this.apiKeys = this.apiKeys.map(key => {
                                    if (!key.id && key.api_key_id) {
                                        key.id = key.api_key_id;
                                    }
                                    return key;
                                });
                                
                                console.log('Loaded API keys:', this.apiKeys.length);
                                console.log('API Keys structure (dashboard):', this.apiKeys.length > 0 ? this.apiKeys[0] : 'No keys found');
                            } else {
                                console.error('Failed to load API keys:', response.status);
                            }
                        } catch (error) {
                            console.error('Error loading API keys:', error);
                        }
                    },
                    
                    async addApiKey() {
                        try {
                            console.log('Adding API key...', this.newApiKey.api_name);
                            
                            const response = await fetch('/api/bot/multi-account/api-keys', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                credentials: 'include',
                                body: JSON.stringify(this.newApiKey)
                            });
                            
                            if (response.ok) {
                                const data = await response.json();
                                console.log('API key added successfully:', data);
                                this.addActivity(`✅ API key "${this.newApiKey.api_name}" added successfully`);
                                
                                // Reset form
                                this.resetNewApiKeyForm();
                                
                                // Reload API keys
                                await this.loadApiKeys();
                                
                                // Switch to list tab
                                this.accountsTab = 'list';
                            } else {
                                const error = await response.json();
                                console.error('Failed to add API key:', error);
                                alert('Failed to add API key: ' + (error.detail || 'Unknown error'));
                            }
                        } catch (error) {
                            console.error('Error adding API key:', error);
                            alert('Error adding API key: ' + error.message);
                        }
                    },
                    
                    async verifyApiKey(apiKeyId) {
                        if (!apiKeyId || apiKeyId === undefined) {
                            console.error('API Key ID is undefined or missing');
                            alert('Error: API Key ID is missing. Please refresh the page and try again.');
                            this.addActivity('❌ API key verification failed: ID missing');
                            return;
                        }
                        try {
                            console.log('Verifying API key:', apiKeyId);
                            this.addActivity('🔍 Verifying API key connection...');
                            
                            const response = await fetch(`/api/bot/multi-account/api-keys/${apiKeyId}/verify`, {
                                method: 'POST',
                                credentials: 'include'
                            });
                            
                            if (response.ok) {
                                const data = await response.json();
                                console.log('API key verified:', data);
                                this.addActivity(`✅ API key verified successfully. Balance: $${data.balance}`);
                                
                                // Reload API keys to show updated verification status
                                await this.loadApiKeys();
                            } else {
                                const error = await response.json();
                                console.error('Failed to verify API key:', error);
                                alert('Verification failed: ' + (error.detail || 'Unknown error'));
                                this.addActivity('❌ API key verification failed');
                            }
                        } catch (error) {
                            console.error('Error verifying API key:', error);
                            alert('Error verifying API key: ' + error.message);
                            this.addActivity('❌ API key verification error');
                        }
                    },
                    
                    async getAccountBalance(apiKeyId) {
                        if (!apiKeyId || apiKeyId === undefined) {
                            console.error('API Key ID is undefined or missing');
                            alert('Error: API Key ID is missing. Please refresh the page and try again.');
                            this.addActivity('❌ Balance refresh failed: ID missing');
                            return;
                        }
                        try {
                            console.log('Getting balance for API key:', apiKeyId);
                            this.addActivity('💰 Refreshing account balance...');
                            
                            const response = await fetch(`/api/bot/multi-account/accounts/${apiKeyId}/balance`, {
                                credentials: 'include'
                            });
                            
                            if (response.ok) {
                                const data = await response.json();
                                console.log('Balance retrieved:', data);
                                this.addActivity(`💰 Balance: $${data.balance.total.toFixed(2)}`);
                                
                                // Reload API keys to show updated balance
                                await this.loadApiKeys();
                            } else {
                                const error = await response.json();
                                console.error('Failed to get balance:', error);
                                alert('Failed to get balance: ' + (error.detail || 'Unknown error'));
                                this.addActivity('❌ Balance refresh failed');
                            }
                        } catch (error) {
                            console.error('Error getting balance:', error);
                            alert('Error getting balance: ' + error.message);
                            this.addActivity('❌ Balance refresh error');
                        }
                    },
                    
                    async toggleAutoTrade(apiKeyId, enabled) {
                        if (!apiKeyId || apiKeyId === undefined) {
                            console.error('API Key ID is undefined or missing');
                            alert('Error: API Key ID is missing. Please refresh the page and try again.');
                            return;
                        }
                        try {
                            console.log('Toggling auto-trade:', apiKeyId, enabled);
                            
                            const response = await fetch(`/api/bot/multi-account/api-keys/${apiKeyId}`, {
                                method: 'PATCH',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                credentials: 'include',
                                body: JSON.stringify({
                                    auto_trade_enabled: enabled
                                })
                            });
                            
                            if (response.ok) {
                                console.log('Auto-trade toggled successfully');
                                this.addActivity(`${enabled ? '✅ Enabled' : '⏸️ Disabled'} auto-trading`);
                                
                                // Reload API keys
                                await this.loadApiKeys();
                            } else {
                                const error = await response.json();
                                console.error('Failed to toggle auto-trade:', error);
                                alert('Failed to toggle auto-trade: ' + (error.detail || 'Unknown error'));
                            }
                        } catch (error) {
                            console.error('Error toggling auto-trade:', error);
                            alert('Error toggling auto-trade: ' + error.message);
                        }
                    },
                    
                    async deleteApiKey(apiKeyId) {
                        if (!apiKeyId || apiKeyId === undefined) {
                            console.error('API Key ID is undefined or missing');
                            alert('Error: API Key ID is missing. Please refresh the page and try again.');
                            return;
                        }
                        try {
                            if (!confirm('Are you sure you want to delete this API key? This action cannot be undone.')) {
                                return;
                            }
                            
                            console.log('Deleting API key:', apiKeyId);
                            
                            const response = await fetch(`/api/bot/multi-account/api-keys/${apiKeyId}`, {
                                method: 'DELETE',
                                credentials: 'include'
                            });
                            
                            if (response.ok) {
                                console.log('API key deleted successfully');
                                this.addActivity('🗑️ API key deleted successfully');
                                
                                // Reload API keys
                                await this.loadApiKeys();
                            } else {
                                const error = await response.json();
                                console.error('Failed to delete API key:', error);
                                alert('Failed to delete API key: ' + (error.detail || 'Unknown error'));
                            }
                        } catch (error) {
                            console.error('Error deleting API key:', error);
                            alert('Error deleting API key: ' + error.message);
                        }
                    },
                    
                    resetNewApiKeyForm() {
                        this.newApiKey = {
                            api_name: '',
                            api_key: '',
                            api_secret: '',
                            account_type: 'futures',
                            test_mode: false,
                            max_position_size_usd: 1000,
                            leverage: 10,
                            max_daily_trades: 5,
                            max_risk_per_trade: 2,
                            max_daily_loss: 5,
                            stop_trading_on_loss: true,
                            position_sizing_mode: 'fixed',
                            position_size_value: 100,
                            auto_trade_enabled: false
                        };
                    }
                }
            }
            
            // Trading History Enhancement
            class TradingHistoryEnhancement {
                constructor() {
                    this.apiBase = '/api/trading-history';
                    this.init();
                }
                
                async init() {
                    await this.loadHistoricalData();
                    this.addHistoricalContext();
                    this.addTradingHistorySection();
                }
                
                async loadHistoricalData() {
                    try {
                        const response = await fetch(`${this.apiBase}/summary`);
                        if (!response.ok) return;
                        
                        this.historicalData = await response.json();
                    } catch (error) {
                        console.error('Error loading historical data:', error);
                    }
                }
                
                addHistoricalContext() {
                    // Add historical context to existing PNL card
                    const pnlCard = document.querySelector('[x-text*="stats.total_realized_pnl"]')?.closest('.bg-white');
                    if (!pnlCard || !this.historicalData) return;
                    
                    // Get historical data
                    const summary = this.historicalData.summary;
                    const closedTrades = summary?.closed_trades_count || 0;
                    const closedPnl = summary?.total_closed_pnl || 0;
                    const totalTrades = summary?.total_trades || 0;
                    
                    // Find the main PNL display and modify it to show both current and realized
                    const pnlDisplay = pnlCard.querySelector('[x-text*="stats.total_realized_pnl"]');
                    if (pnlDisplay) {
                        // Create a new display showing both current and realized PNL
                        const currentPnl = window.stats?.total_realized_pnl || 0;
                        const realizedPnl = closedPnl;
                        
                        // Replace the single PNL display with a dual display
                        const dualPnlDisplay = document.createElement('div');
                        dualPnlDisplay.className = 'text-right';
                        dualPnlDisplay.innerHTML = `
                            <div class="space-y-2">
                                <div>
                                    <p class="text-sm text-gray-600">Current PNL</p>
                                    <p class="text-2xl font-bold ${currentPnl >= 0 ? 'text-green-600' : 'text-red-600'}">
                                        $${currentPnl.toFixed(2)}
                                    </p>
                                </div>
                                <div class="border-t pt-2">
                                    <p class="text-sm text-gray-600">Realized Profit</p>
                                    <p class="text-xl font-semibold ${realizedPnl >= 0 ? 'text-green-600' : 'text-red-600'}">
                                        $${realizedPnl.toFixed(2)}
                                    </p>
                                    <p class="text-xs text-gray-500">${closedTrades} closed trades</p>
                                </div>
                            </div>
                        `;
                        
                        // Replace the original display
                        const parentElement = pnlDisplay.parentElement;
                        if (parentElement) {
                            parentElement.replaceChild(dualPnlDisplay, pnlDisplay.parentElement);
                        }
                    }
                    
                    // Add comprehensive trading statistics below
                    const tradingStats = document.createElement('div');
                    tradingStats.className = 'mt-4 pt-4 border-t border-gray-200 text-xs text-gray-600';
                    tradingStats.innerHTML = `
                        <div class="grid grid-cols-2 gap-3">
                            <div class="text-center">
                                <span class="block font-medium text-gray-900">Total Trades</span>
                                <span class="text-lg font-semibold">${totalTrades}</span>
                            </div>
                            <div class="text-center">
                                <span class="block font-medium text-gray-900">Win Rate</span>
                                <span class="text-lg font-semibold">${(summary?.overall_win_rate || 0).toFixed(1)}%</span>
                            </div>
                        </div>
                    `;
                    
                    // Add to the card
                    pnlCard.appendChild(tradingStats);
                }
                
                addTradingHistorySection() {
                    // Add a new trading history section to the dashboard
                    const mainContent = document.querySelector('main');
                    if (!mainContent || !this.historicalData) return;
                    
                    const tradingHistorySection = document.createElement('div');
                    tradingHistorySection.className = 'mt-8';
                    tradingHistorySection.innerHTML = `
                        <div class="bg-white/80 backdrop-blur-sm rounded-xl shadow-lg border border-white/20 p-6">
                            <div class="flex items-center justify-between mb-6">
                                <h2 class="text-xl font-bold text-gray-900">Trading History</h2>
                                <button id="refresh-history-btn" class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors">
                                    Refresh Data
                                </button>
                            </div>
                            
                            <!-- Historical Stats Grid -->
                            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                                <div class="text-center p-4 bg-gray-50 rounded-lg">
                                    <div class="text-2xl font-bold text-gray-900">${this.historicalData.summary?.total_trades || 0}</div>
                                    <div class="text-sm text-gray-600">Total Trades</div>
                                </div>
                                <div class="text-center p-4 bg-green-50 rounded-lg">
                                    <div class="text-2xl font-bold text-green-600">${this.historicalData.summary?.closed_trades_count || 0}</div>
                                    <div class="text-sm text-gray-600">Closed Trades</div>
                                </div>
                                <div class="text-center p-4 bg-green-50 rounded-lg">
                                    <div class="text-2xl font-bold text-green-600">$${this.historicalData.summary?.total_closed_pnl?.toFixed(2) || '0.00'}</div>
                                    <div class="text-sm text-gray-600">Realized Profit</div>
                                </div>
                                <div class="text-center p-4 bg-gray-50 rounded-lg">
                                    <div class="text-2xl font-bold text-blue-600">${(this.historicalData.summary?.overall_win_rate || 0).toFixed(1)}%</div>
                                    <div class="text-sm text-gray-600">Win Rate</div>
                                </div>
                            </div>
                            
                            <!-- Recent Trades Table -->
                            <div class="overflow-x-auto">
                                <table class="min-w-full divide-y divide-gray-200">
                                    <thead class="bg-gray-50">
                                        <tr>
                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Side</th>
                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Symbol</th>
                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Amount</th>
                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Price</th>
                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">PNL</th>
                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
                                        </tr>
                                    </thead>
                                    <tbody class="bg-white divide-y divide-gray-200">
                                        ${this.renderRecentTrades()}
                                    </tbody>
                                </table>
                            </div>
                            
                            <!-- Top Profitable Trades -->
                            <div class="mt-6">
                                <h3 class="text-lg font-medium text-gray-900 mb-4">Top Profitable Trades</h3>
                                <div class="bg-green-50 rounded-lg p-4">
                                    ${this.renderTopProfitableTrades()}
                                </div>
                            </div>
                            
                            <!-- Daily PNL Chart -->
                            <div class="mt-6">
                                <h3 class="text-lg font-medium text-gray-900 mb-4">Daily PNL Trend</h3>
                                <div class="h-64 flex items-end justify-between px-4 py-4 bg-gray-50 rounded-lg">
                                    ${this.renderDailyPnlChart()}
                                </div>
                            </div>
                        </div>
                    `;
                    
                    mainContent.appendChild(tradingHistorySection);
                    
                    // Add event listener for refresh button
                    const refreshBtn = document.getElementById('refresh-history-btn');
                    if (refreshBtn) {
                        refreshBtn.addEventListener('click', () => this.refreshHistory());
                    }
                    
                    // Add refresh function to window for global access
                    window.refreshHistory = () => this.refreshHistory();
                }
                
                renderRecentTrades() {
                    if (!this.historicalData.recent_trades || this.historicalData.recent_trades.length === 0) {
                        return `
                            <tr>
                                <td colspan="6" class="px-6 py-4 text-center text-gray-500">
                                    No recent trades found
                                </td>
                            </tr>
                        `;
                    }
                    
                    return this.historicalData.recent_trades.slice(0, 10).map(trade => {
                        const pnlClass = trade.pnl && trade.pnl > 0 ? 'text-green-600' : 
                                       trade.pnl && trade.pnl < 0 ? 'text-red-600' : 'text-gray-600';
                        const sideClass = trade.side === 'buy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800';
                        const date = new Date(trade.timestamp).toLocaleString();
                        
                        return `
                            <tr class="hover:bg-gray-50">
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full ${sideClass}">
                                        ${trade.side.toUpperCase()}
                                    </span>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                    ${trade.symbol}
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                    ${parseFloat(trade.amount).toFixed(6)}
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                    $${parseFloat(trade.price).toFixed(2)}
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm ${pnlClass}">
                                    ${trade.pnl !== null && trade.pnl !== undefined ? `$${parseFloat(trade.pnl).toFixed(2)}` : '-'}
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                    ${date}
                                </td>
                            </tr>
                        `;
                    }).join('');
                }
                
                renderTopProfitableTrades() {
                    // Get all trades and filter for profitable ones
                    const allTrades = this.historicalData.recent_trades || [];
                    const profitableTrades = allTrades
                        .filter(trade => trade.pnl && trade.pnl > 0)
                        .sort((a, b) => b.pnl - a.pnl)
                        .slice(0, 5); // Top 5 most profitable
                    
                    if (profitableTrades.length === 0) {
                        return '<div class="text-center text-gray-500 py-4">No profitable trades found</div>';
                    }
                    
                    return profitableTrades.map(trade => {
                        const date = new Date(trade.timestamp).toLocaleDateString('en-US', { 
                            month: 'short', 
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                        });
                        
                        return `
                            <div class="flex items-center justify-between py-2 border-b border-green-200 last:border-b-0">
                                <div class="flex items-center space-x-4">
                                    <div class="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                                        <span class="text-green-600 text-sm font-bold">+</span>
                                    </div>
                                    <div>
                                        <div class="font-medium text-gray-900">${trade.symbol}</div>
                                        <div class="text-sm text-gray-500">${trade.side.toUpperCase()} • ${date}</div>
                                    </div>
                                </div>
                                <div class="text-right">
                                    <div class="text-lg font-bold text-green-600">+$${trade.pnl.toFixed(2)}</div>
                                    <div class="text-sm text-gray-500">${parseFloat(trade.amount).toFixed(2)} @ $${parseFloat(trade.price).toFixed(2)}</div>
                                </div>
                            </div>
                        `;
                    }).join('');
                }
                
                renderDailyPnlChart() {
                    if (!this.historicalData.daily_pnl || this.historicalData.daily_pnl.length === 0) {
                        return '<div class="text-center text-gray-500">No PNL data available</div>';
                    }
                    
                    const maxPnl = Math.max(...this.historicalData.daily_pnl.map(d => Math.abs(d.total_pnl)));
                    const chartHeight = 200;
                    
                    return this.historicalData.daily_pnl.slice(0, 7).map(day => {
                        const height = maxPnl > 0 ? (Math.abs(day.total_pnl) / maxPnl) * chartHeight : 0;
                        const color = day.total_pnl >= 0 ? 'bg-green-500' : 'bg-red-500';
                        const date = new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                        
                        return `
                            <div class="flex flex-col items-center">
                                <div class="relative">
                                    <div class="w-8 ${color} rounded-t" style="height: ${height}px"></div>
                                    <div class="absolute -bottom-6 text-xs text-gray-600 whitespace-nowrap">
                                        ${date}
                                    </div>
                                </div>
                                <div class="text-xs text-gray-500 mt-8">
                                    $${day.total_pnl.toFixed(2)}
                                </div>
                            </div>
                        `;
                    }).join('');
                }
                
                async refreshHistory() {
                    try {
                        // Show loading state
                        const refreshBtn = document.getElementById('refresh-history-btn');
                        if (refreshBtn) {
                            refreshBtn.textContent = 'Refreshing...';
                            refreshBtn.disabled = true;
                        }
                        
                        const response = await fetch(`${this.apiBase}/refresh`, { 
                            method: 'POST',
                            headers: {
                                'Authorization': 'Bearer test-token'
                            }
                        });
                        
                        if (response.ok) {
                            const result = await response.json();
                            console.log('Refresh result:', result);
                            
                            // Reload the page to show updated data
                            location.reload();
                        } else {
                            console.error('Failed to refresh history:', response.status);
                            alert('Failed to refresh trading history. Please try again.');
                        }
                    } catch (error) {
                        console.error('Error refreshing history:', error);
                        alert('Error refreshing trading history. Please try again.');
                    } finally {
                        // Reset button state
                        const refreshBtn = document.getElementById('refresh-history-btn');
                        if (refreshBtn) {
                            refreshBtn.textContent = 'Refresh Data';
                            refreshBtn.disabled = false;
                        }
                    }
                }
            }
            
            // Initialize trading history enhancement when dashboard loads
            document.addEventListener('DOMContentLoaded', () => {
                setTimeout(() => {
                    new TradingHistoryEnhancement();
                }, 1000); // Wait for main dashboard to load
            });
        </script>
    </body>
    </html>
    """


@app.get("/api/balance")
async def get_bot_balance(current_user: Dict = Depends(require_auth)):
    """Get current Binance account balance."""
    try:
        # Get balance from the trading bot API
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get("http://winu-bot-signal-trading-bot-api:8000/api/bot/balance") as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "message": "Balance retrieved successfully",
                        "balance": data.get("balance", {"free_balance": 0, "total_balance": 0, "currency": "USDT"}),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    raise Exception(f"Bot API returned status {response.status}")
        
    except Exception as e:
        logger.error(f"Error getting balance: {e}")
        return {
            "message": f"Error retrieving balance: {str(e)}",
            "balance": {"free_balance": 0, "total_balance": 0, "currency": "USDT"},
            "timestamp": datetime.utcnow().isoformat()
        }


@app.get("/api/dual-balances")
async def get_dual_balances(current_user: Dict = Depends(require_auth)):
    """Get current Binance account balances for both spot and futures."""
    try:
        # Get dual balances from the trading bot API
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get("http://winu-bot-signal-trading-bot-api:8000/api/bot/dual-balances") as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "message": "Dual balances retrieved successfully",
                        "balances": data.get("balances", {
                            "spot": {"free_balance": 0, "total_balance": 0, "currency": "USDT"},
                            "futures": {"free_balance": 0, "total_balance": 0, "currency": "USDT"}
                        }),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    # Fallback to single balance if dual endpoint not available
                    async with session.get("http://winu-bot-signal-trading-bot-api:8000/api/bot/balance") as fallback_response:
                        if fallback_response.status == 200:
                            fallback_data = await fallback_response.json()
                            balance = fallback_data.get("balance", {"free_balance": 0, "total_balance": 0, "currency": "USDT"})
                            return {
                                "message": "Single balance retrieved (dual not available)",
                                "balances": {
                                    "spot": balance,
                                    "futures": balance
                                },
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        else:
                            raise Exception(f"Both bot APIs returned status {response.status}")
        
    except Exception as e:
        logger.error(f"Error getting dual balances: {e}")
        return {
            "message": f"Error retrieving dual balances: {str(e)}",
            "balances": {
                "spot": {"free_balance": 0, "total_balance": 0, "currency": "USDT"},
                "futures": {"free_balance": 0, "total_balance": 0, "currency": "USDT"}
            },
            "timestamp": datetime.utcnow().isoformat()
        }


@app.get("/api/public-status")
async def get_public_status():
    """Get public bot status without authentication."""
    try:
        conn = await connect_db()
        
        try:
            # Get basic stats from REAL trading data
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_trades,
                    COALESCE(SUM(pnl), 0) as total_realized_pnl,
                    COUNT(CASE WHEN pnl > 0 THEN 1 END) as winning_trades,
                    COUNT(CASE WHEN pnl < 0 THEN 1 END) as losing_trades
                FROM trading_trades
                WHERE pnl IS NOT NULL
            """)
            
            # Get recent trades count (24h)
            trades_24h = await conn.fetchval("SELECT COUNT(*) FROM trading_trades WHERE created_at >= NOW() - INTERVAL '24 hours'")
            
            # Get latest REAL trade
            latest = await conn.fetchrow("""
                SELECT symbol, side, price, amount, pnl, trade_type
                FROM trading_trades 
                ORDER BY created_at DESC 
                LIMIT 1
            """)
            
            # Calculate win rate from closed trades only
            closed_trades = stats['winning_trades'] + stats['losing_trades']
            win_rate = (stats['winning_trades'] / closed_trades * 100) if closed_trades > 0 else 0
            
            result = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "recent_trades_24h": trades_24h,
                "total_trades": stats['total_trades'],
                "total_pnl": float(stats['total_realized_pnl']),
                "win_rate": round(win_rate, 2),
                "latest_trade": {
                    "symbol": latest['symbol'],
                    "side": latest['side'],
                    "price": float(latest['price']),
                    "amount": float(latest['amount']),
                    "pnl": float(latest['pnl']) if latest['pnl'] else 0,
                    "trade_type": latest['trade_type']
                } if latest else None,
                "bot_status": "running"
            }
            
            # Try to fetch real balances with better timeout handling
            try:
                import aiohttp
                timeout = aiohttp.ClientTimeout(total=30, connect=10)  # Longer timeouts
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get('http://winu-bot-signal-trading-bot-api:8000/api/bot/dual-balances') as response:
                        if response.status == 200:
                            balance_data = await response.json()
                            result["balances"] = balance_data.get('balances', {
                                "spot": {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"},
                                "futures": {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"}
                            })
                        else:
                            logger.warning(f"Balance API returned status {response.status}")
                            result["balances"] = {
                                "spot": {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"},
                                "futures": {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"}
                            }
            except asyncio.TimeoutError:
                logger.warning("Balance API request timed out")
                result["balances"] = {
                    "spot": {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"},
                    "futures": {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"}
                }
            except Exception as balance_error:
                logger.warning(f"Could not fetch balances: {balance_error}")
                result["balances"] = {
                    "spot": {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"},
                    "futures": {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"}
                }
            
            return result
            
        finally:
            await conn.close()
            
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "bot_status": "unknown"
        }

@app.get("/api/public-balances")
async def get_public_balances():
    """Get public balance information without authentication."""
    try:
        # Get balances from bot API with better timeout handling
        import aiohttp
        timeout = aiohttp.ClientTimeout(total=30, connect=10)  # Longer timeouts
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get('http://winu-bot-signal-trading-bot-api:8000/api/bot/dual-balances') as response:
                if response.status == 200:
                    balances = await response.json()
                    return {
                        "status": "success",
                        "timestamp": datetime.utcnow().isoformat(),
                        "balances": balances.get('balances', {
                            "spot": {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"},
                            "futures": {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"}
                        })
                    }
                else:
                    # Fallback to N/A balances
                    return {
                        "status": "success",
                        "timestamp": datetime.utcnow().isoformat(),
                        "balances": {
                            "spot": {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"},
                            "futures": {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"}
                        },
                        "note": "Balance API unavailable"
                    }
    except asyncio.TimeoutError:
        # Handle timeout specifically
        logger.warning("Balance API request timed out")
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "balances": {
                "spot": {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"},
                "futures": {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"}
            },
            "note": "Balance API timeout - check Binance directly"
        }
    except Exception as e:
        # Fallback to N/A balances when API fails
        logger.error(f"Balance API error: {e}")
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "balances": {
                "spot": {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"},
                "futures": {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"}
            },
            "note": "Balance data temporarily unavailable - check Binance directly"
        }

@app.get("/api/public-positions")
async def get_public_positions():
    """Get public position information without authentication."""
    try:
        conn = await connect_db()
        
        try:
            positions = await conn.fetch("""
                SELECT id, symbol, side, entry_price, quantity, current_price, unrealized_pnl, 
                       stop_loss, take_profit, market_type, created_at, updated_at
                FROM paper_positions 
                WHERE is_open = true
                ORDER BY created_at DESC
            """)
            
            position_list = []
            for pos in positions:
                position_list.append({
                    "id": pos['id'],
                    "symbol": pos['symbol'],
                    "side": pos['side'],
                    "entry_price": float(pos['entry_price']),
                    "current_price": float(pos['current_price']),
                    "quantity": float(pos['quantity']),
                    "unrealized_pnl": float(pos['unrealized_pnl']),
                    "market_type": pos['market_type'],
                    "stop_loss": float(pos['stop_loss']) if pos['stop_loss'] else None,
                    "take_profit": float(pos['take_profit']) if pos['take_profit'] else None,
                    "created_at": pos['created_at'].isoformat(),
                    "updated_at": pos['updated_at'].isoformat()
                })
            
            return {
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "positions": position_list,
                "total_positions": len(position_list)
            }
            
        finally:
            await conn.close()
            
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

# Removed bot control endpoints (start, stop, emergency-stop, sync-positions)
# These are no longer used from the frontend UI

@app.get("/api/sync-status")
async def get_sync_status(current_user: Dict = Depends(require_auth)):
    """Get position synchronization status."""
    try:
        # Import and use the position sync module
        import sys
        sys.path.append('/home/ubuntu/winubotsignal/bot/execution')
        from position_sync import PositionSync
        
        sync = PositionSync(test_mode=False)
        status = await sync.get_sync_status()
        
        return {
            "message": "Sync status retrieved",
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        return {
            "message": f"Error getting sync status: {str(e)}",
            "status": "error",
            "timestamp": datetime.utcnow().isoformat()
        }


@app.post("/api/reset-stats")
async def reset_bot_stats(current_user: Dict = Depends(require_auth)):
    """Reset bot statistics to start fresh."""
    try:
        conn = await connect_db()
        
        try:
            # Close all open positions
            await conn.execute("""
                UPDATE paper_positions 
                SET is_open = false, closed_at = NOW(), close_reason = 'stats_reset'
                WHERE is_open = true
            """)
            
            # Delete all positions to reset stats
            await conn.execute("DELETE FROM paper_positions")
            
            # Reset bot session
            await conn.execute("UPDATE bot_sessions SET is_active = false WHERE is_active = true")
            await conn.execute("""
                INSERT INTO bot_sessions (is_active, bot_status, test_mode, created_at) 
                VALUES (true, 'running', false, NOW())
            """)
            
            logger.info("✅ Bot stats reset successfully")
            
            return {
                "message": "Bot statistics reset successfully",
                "status": "success",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Error resetting bot stats: {e}")
        return {
            "message": f"Error resetting bot stats: {str(e)}",
            "status": "error",
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/api/test-positions")
async def test_positions(current_user: Dict = Depends(require_auth)):
    """Test endpoint to verify positions query works."""
    try:
        conn = await asyncpg.connect(
            host='winu-bot-signal-postgres',
            port=5432,
            user='winu',
            password='winu250420',
            database='winudb',
            command_timeout=10
        )
        
        positions_result = await conn.fetch("""
            SELECT id, symbol, side, entry_price, quantity, current_price, unrealized_pnl, 
                   stop_loss, take_profit, market_type, created_at, updated_at
            FROM paper_positions 
            WHERE is_open = true
            ORDER BY created_at DESC
        """)
        
        positions = []
        for pos in positions_result:
            positions.append({
                "id": pos['id'],
                "symbol": pos['symbol'],
                "side": pos['side'],
                "entry_price": float(pos['entry_price']),
                "current_price": float(pos['current_price']),
                "quantity": float(pos['quantity']),
                "unrealized_pnl": float(pos['unrealized_pnl']),
                "market_type": pos['market_type'],
                "stop_loss": float(pos['stop_loss']) if pos['stop_loss'] else None,
                "take_profit": float(pos['take_profit']) if pos['take_profit'] else None,
                "created_at": pos['created_at'].isoformat(),
                "updated_at": pos['updated_at'].isoformat()
            })
        
        await conn.close()
        
        return {
            "message": f"Found {len(positions)} positions",
            "positions": positions
        }
        
    except Exception as e:
        return {"error": str(e), "positions": []}

@app.get("/api/status")
async def get_bot_status(current_user: Dict = Depends(require_auth)):
    """Get current bot status and statistics - WORKING VERSION."""
    try:
        # Direct database connection - WORKING VERSION
        conn = await asyncpg.connect(
            host='winu-bot-signal-postgres',
            port=5432,
            user='winu',
            password='winu250420',
            database='winudb',
            command_timeout=10
        )
        
        try:
            # Get ALL positions with FULL DETAILS
            positions_result = await conn.fetch("""
                SELECT id, symbol, side, entry_price, quantity, current_price, unrealized_pnl, 
                       stop_loss, take_profit, market_type, created_at, updated_at
                FROM paper_positions 
                WHERE is_open = true
                ORDER BY created_at DESC
            """)
            
            positions = []
            for pos in positions_result:
                positions.append({
                    "id": pos['id'],
                    "symbol": pos['symbol'],
                    "side": pos['side'],
                    "entry_price": float(pos['entry_price']),
                    "current_price": float(pos['current_price']),
                    "quantity": float(pos['quantity']),
                    "unrealized_pnl": float(pos['unrealized_pnl']),
                    "market_type": pos['market_type'],
                    "stop_loss": float(pos['stop_loss']) if pos['stop_loss'] else None,
                    "take_profit": float(pos['take_profit']) if pos['take_profit'] else None,
                    "created_at": pos['created_at'].isoformat(),
                    "updated_at": pos['updated_at'].isoformat()
                })
            
            # Get bot status - check for recent activity (signals or positions)
            recent_activity = await conn.fetchval("""
                SELECT COUNT(*) FROM (
                    SELECT 1 FROM paper_positions WHERE created_at > NOW() - INTERVAL '2 hours'
                    UNION ALL
                    SELECT 1 FROM signals WHERE created_at > NOW() - INTERVAL '2 hours'
                ) as activity
            """)
            
            # Also check if bot container is running by checking recent signals
            recent_signals = await conn.fetchval("SELECT COUNT(*) FROM signals WHERE created_at > NOW() - INTERVAL '1 hour'")
            
            # Get stats from REAL trading data
            stats = await conn.fetchrow("""
                SELECT 
                    COALESCE(SUM(pnl), 0) as total_realized_pnl,
                    COUNT(*) as total_trades,
                    COUNT(CASE WHEN pnl > 0 THEN 1 END) as winning_trades,
                    COUNT(CASE WHEN pnl < 0 THEN 1 END) as losing_trades
                FROM trading_trades
                WHERE pnl IS NOT NULL
            """)
            
            closed_trades = stats['winning_trades'] + stats['losing_trades']
            win_rate = (stats['winning_trades'] / closed_trades * 100) if closed_trades > 0 else 0
            
            # Calculate real uptime from bot session
            bot_session = await conn.fetchrow("SELECT created_at FROM bot_sessions WHERE is_active = true ORDER BY created_at DESC LIMIT 1")
            uptime_seconds = 0
            if bot_session:
                from datetime import datetime
                start_time = bot_session['created_at']
                uptime_seconds = int((datetime.utcnow() - start_time).total_seconds())
            
            return {
                    "bot_status": {
                        "is_running": recent_activity > 0 or recent_signals > 0,
                        "test_mode": False,
                        "uptime": uptime_seconds
                    },
                "stats": {
                    "total_realized_pnl": float(stats['total_realized_pnl']),
                    "win_rate": win_rate,
                    "total_trades": stats['total_trades']
                },
                "positions": positions
            }
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Error getting bot status: {e}")
        return {
            "bot_status": {"is_running": False, "test_mode": True, "uptime": 0},
            "stats": {"total_realized_pnl": 0, "win_rate": 0, "total_trades": 0},
            "positions": [],
            "error": str(e)
        }


@app.post("/api/positions/{position_id}/close")
async def close_position(position_id: int, current_user: Dict = Depends(require_auth)):
    """Close a specific position."""
    conn = None
    try:
        conn = await connect_db()
        
        # First, get position details
        position = await conn.fetchrow("""
            SELECT * FROM paper_positions WHERE id = $1 AND is_open = true
        """, position_id)
        
        if not position:
            raise HTTPException(status_code=404, detail="Position not found or already closed")
        
        # Call bot API to properly close the position on Binance
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'http://winu-bot-signal-trading-bot-api:8000/api/bot/close-position/{position_id}',
                    timeout=30
                ) as response:
                    if response.status == 200:
                        close_result = await response.json()
                        logger.info(f"Position {position_id} closed successfully via bot API")
                        return {"message": f"Position {position_id} closed successfully", "result": close_result}
                    else:
                        error_text = await response.text()
                        logger.error(f"Bot API close failed: {response.status} - {error_text}")
                        # Fallback to database-only close
                        await conn.execute("""
                            UPDATE paper_positions 
                            SET is_open = false, closed_at = $1, updated_at = $2, close_reason = $3
                            WHERE id = $4
                        """, datetime.utcnow(), datetime.utcnow(), "manual_close_api_failed", position_id)
                        return {"message": f"Position {position_id} closed in database only (API failed)", "warning": "Orders may still be open on Binance"}
        except Exception as api_error:
            logger.error(f"Error calling bot API: {api_error}")
            # Fallback to database-only close
            await conn.execute("""
                UPDATE paper_positions 
                SET is_open = false, closed_at = $1, updated_at = $2, close_reason = $3
                WHERE id = $4
            """, datetime.utcnow(), datetime.utcnow(), "manual_close_api_error", position_id)
            return {"message": f"Position {position_id} closed in database only (API error)", "warning": "Orders may still be open on Binance"}
        
    except Exception as e:
        logger.error(f"Error closing position: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            await conn.close()


# Add trading history endpoints
@app.get("/api/trading-history/summary")
async def get_trading_history_summary(current_user: dict = Depends(get_current_user)):
    """Get trading history summary."""
    try:
        conn = await connect_db()
        
        # Get daily PNL summary (last 30 days)
        daily_pnl = await conn.fetch("""
            SELECT * FROM daily_pnl_summary 
            WHERE date >= CURRENT_DATE - INTERVAL '30 days'
            ORDER BY date DESC
        """)
        
        # Get recent trades (both spot and futures)
        recent_trades = await conn.fetch("""
            SELECT * FROM trading_trades 
            ORDER BY timestamp DESC 
            LIMIT 20
        """)
        
        # Get trades with PNL (closed positions)
        trades_with_pnl = await conn.fetch("""
            SELECT COUNT(*) as count, SUM(pnl) as total_pnl 
            FROM trading_trades 
            WHERE pnl IS NOT NULL AND pnl != 0
        """)
        
        # Get current balances
        current_balances = await conn.fetch("""
            SELECT * FROM account_balance_history 
            WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
            ORDER BY timestamp DESC
        """)
        
        # Calculate totals from daily PNL
        total_realized_pnl = sum(day['total_pnl'] for day in daily_pnl)
        total_winning = sum(day['winning_trades'] for day in daily_pnl)
        total_losing = sum(day['losing_trades'] for day in daily_pnl)
        # Total trades should be sum of all trades from daily PNL, not just recent 20
        total_trades_from_daily = sum(day['total_trades'] for day in daily_pnl)
        # Calculate win rate from actual closed trades with PNL
        closed_trades_total = total_winning + total_losing
        overall_win_rate = (total_winning / closed_trades_total * 100) if closed_trades_total > 0 else 0
        
        # Get trades with PNL statistics
        closed_trades_count = trades_with_pnl[0]['count'] if trades_with_pnl else 0
        total_closed_pnl = float(trades_with_pnl[0]['total_pnl']) if trades_with_pnl and trades_with_pnl[0]['total_pnl'] else 0.0
        
        await conn.close()
        
        return {
            "summary": {
                "total_realized_pnl": total_realized_pnl,
                "total_trades": total_trades_from_daily,
                "winning_trades": total_winning,
                "losing_trades": total_losing,
                "overall_win_rate": overall_win_rate,
                "days_analyzed": len(daily_pnl),
                "closed_trades_count": closed_trades_count,
                "total_closed_pnl": total_closed_pnl
            },
            "daily_pnl": [dict(day) for day in daily_pnl],
            "recent_trades": [dict(trade) for trade in recent_trades],
            "current_balances": [dict(balance) for balance in current_balances]
        }
        
    except Exception as e:
        logger.error(f"Error getting trading history summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trading-history/trades")
async def get_trading_trades(
    limit: int = 50,
    offset: int = 0,
    trade_type: Optional[str] = None,
    symbol: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get trading trades with pagination and filters."""
    try:
        conn = await connect_db()
        
        # Build query with filters
        where_conditions = []
        params = [limit, offset]
        param_count = 2
        
        if trade_type:
            param_count += 1
            where_conditions.append(f"trade_type = ${param_count}")
            params.append(trade_type)
        
        if symbol:
            param_count += 1
            where_conditions.append(f"symbol = ${param_count}")
            params.append(symbol)
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Get trades
        trades = await conn.fetch(f"""
            SELECT * FROM trading_trades 
            WHERE {where_clause}
            ORDER BY timestamp DESC 
            LIMIT $1 OFFSET $2
        """, *params)
        
        # Get total count
        count_result = await conn.fetchrow(f"""
            SELECT COUNT(*) as total FROM trading_trades 
            WHERE {where_clause}
        """, *params[2:])
        
        await conn.close()
        
        return {
            "trades": [dict(trade) for trade in trades],
            "total": count_result['total'],
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Error getting trading trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trading-history/daily-pnl")
async def get_daily_pnl(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """Get daily PNL data."""
    try:
        conn = await connect_db()
        
        daily_pnl = await conn.fetch("""
            SELECT * FROM daily_pnl_summary 
            WHERE date >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY date DESC
        """, days)
        
        await conn.close()
        
        return [dict(day) for day in daily_pnl]
        
    except Exception as e:
        logger.error(f"Error getting daily PNL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trading-history/balance-history")
async def get_balance_history(
    hours: int = 24,
    current_user: dict = Depends(get_current_user)
):
    """Get account balance history."""
    try:
        conn = await connect_db()
        
        balances = await conn.fetch("""
            SELECT * FROM account_balance_history 
            WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '%s hours'
            ORDER BY timestamp DESC
        """, hours)
        
        await conn.close()
        
        return [dict(balance) for balance in balances]
        
    except Exception as e:
        logger.error(f"Error getting balance history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Multi-Account API Proxy Endpoints =====

@app.get("/api/bot/multi-account/api-keys")
async def proxy_get_api_keys(current_user: Dict = Depends(require_auth)):
    """Proxy request to get API keys from main API."""
    try:
        # Create JWT token for the current user
        jwt_token = create_jwt_token(current_user.get('username'))
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            # Forward request to main API with JWT token
            async with session.get(
                "http://winu-bot-signal-api:8001/api/bot/multi-account/api-keys",
                headers={"Authorization": f"Bearer {jwt_token}"}
            ) as response:
                data = await response.json()
                logger.info(f"API Keys response from backend: {data}")
                logger.info(f"Response type: {type(data)}, Keys count: {len(data) if isinstance(data, list) else 'N/A'}")
                if isinstance(data, dict) and 'api_keys' in data:
                    logger.info(f"API keys count in dict: {len(data['api_keys'])}")
                return data
    except Exception as e:
        logger.error(f"Error proxying get API keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bot/multi-account/api-keys")
async def proxy_create_api_key(request: Request, current_user: Dict = Depends(require_auth)):
    """Proxy request to create API key."""
    try:
        # Create JWT token for the current user
        jwt_token = create_jwt_token(current_user.get('username'))
        
        data = await request.json()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://winu-bot-signal-api:8001/api/bot/multi-account/api-keys",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json=data
            ) as response:
                result = await response.json()
                return result
    except Exception as e:
        logger.error(f"Error proxying create API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/bot/multi-account/api-keys/{api_key_id}")
async def proxy_update_api_key(api_key_id: int, request: Request, current_user: Dict = Depends(require_auth)):
    """Proxy request to update API key."""
    try:
        # Create JWT token for the current user
        jwt_token = create_jwt_token(current_user.get('username'))
        
        data = await request.json()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f"http://winu-bot-signal-api:8001/api/bot/multi-account/api-keys/{api_key_id}",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json=data
            ) as response:
                result = await response.json()
                return result
    except Exception as e:
        logger.error(f"Error proxying update API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/bot/multi-account/api-keys/{api_key_id}")
async def proxy_delete_api_key(api_key_id: int, current_user: Dict = Depends(require_auth)):
    """Proxy request to delete API key."""
    try:
        # Create JWT token for the current user
        jwt_token = create_jwt_token(current_user.get('username'))
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"http://winu-bot-signal-api:8001/api/bot/multi-account/api-keys/{api_key_id}",
                headers={"Authorization": f"Bearer {jwt_token}"}
            ) as response:
                result = await response.json()
                return result
    except Exception as e:
        logger.error(f"Error proxying delete API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bot/multi-account/api-keys/{api_key_id}/verify")
async def proxy_verify_api_key(api_key_id: int, current_user: Dict = Depends(require_auth)):
    """Proxy request to verify API key."""
    try:
        # Create JWT token for the current user
        jwt_token = create_jwt_token(current_user.get('username'))
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"http://winu-bot-signal-api:8001/api/bot/multi-account/api-keys/{api_key_id}/verify",
                headers={"Authorization": f"Bearer {jwt_token}"}
            ) as response:
                result = await response.json()
                return result
    except Exception as e:
        logger.error(f"Error proxying verify API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/bot/multi-account/accounts/{api_key_id}/balance")
async def proxy_get_account_balance(api_key_id: int, current_user: Dict = Depends(require_auth)):
    """Proxy request to get account balance."""
    try:
        # Create JWT token for the current user
        jwt_token = create_jwt_token(current_user.get('username'))
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://winu-bot-signal-api:8001/api/bot/multi-account/accounts/{api_key_id}/balance",
                headers={"Authorization": f"Bearer {jwt_token}"}
            ) as response:
                result = await response.json()
                return result
    except Exception as e:
        logger.error(f"Error proxying get account balance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/trading-history/refresh")
async def refresh_trading_history(current_user: dict = Depends(get_current_user)):
    """Manually refresh trading history data."""
    try:
        # Import the trading history service
        sys.path.append('/packages')
        from services.trading_history_service import TradingHistoryService
        
        history_service = TradingHistoryService(test_mode=False)
        
        # Fetch and store data (extend to 90 days to catch more historical trades)
        futures_result = await history_service.fetch_and_store_futures_trades(days=90)
        spot_result = await history_service.fetch_and_store_spot_trades(days=90)
        balance_result = await history_service.store_account_balance()
        
        # Calculate spot PNL by matching buy/sell pairs
        spot_pnl_result = await history_service.calculate_spot_pnl()
        
        # Calculate recent PNL
        yesterday = datetime.now().date() - timedelta(days=1)
        today = datetime.now().date()
        
        yesterday_pnl = await history_service.calculate_daily_pnl(yesterday)
        today_pnl = await history_service.calculate_daily_pnl(today)
        
        return {
            "success": True,
            "futures_trades": futures_result,
            "spot_trades": spot_result,
            "balance_update": balance_result,
            "spot_pnl_calculation": spot_pnl_result,
            "yesterday_pnl": yesterday_pnl,
            "today_pnl": today_pnl
        }
        
    except Exception as e:
        logger.error(f"Error refreshing trading history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/signals/history")
async def get_signals_history(
    min_score: float = 0.0,
    max_score: float = 1.0,
    symbol: Optional[str] = None,
    direction: Optional[str] = None,
    days: int = 7,
    limit: int = 100,
    offset: int = 0,
    current_user: Dict = Depends(require_auth)
):
    """Get signals history with filtering by score, symbol, direction, etc."""
    try:
        conn = await connect_db()
        
        # Build WHERE conditions
        where_conditions = [
            "created_at >= NOW() - INTERVAL '%s days'" % days,
            "score >= $1",
            "score <= $2"
        ]
        params = [min_score, max_score, limit, offset]
        param_count = 2
        
        if symbol:
            param_count += 1
            where_conditions.append(f"symbol = ${param_count}")
            params.insert(param_count - 1, symbol)
        
        if direction:
            param_count += 1
            where_conditions.append(f"direction = ${param_count}")
            params.insert(param_count - 1, direction.upper())
        
        where_clause = " AND ".join(where_conditions)
        
        # Get signals with filtering
        query = f"""
            SELECT 
                id,
                symbol,
                timeframe,
                signal_type,
                direction,
                score,
                entry_price,
                stop_loss,
                take_profit_1,
                take_profit_2,
                take_profit_3,
                risk_reward_ratio,
                is_active,
                is_executed,
                filled_at,
                closed_at,
                realized_pnl,
                created_at,
                updated_at
            FROM signals
            WHERE {where_clause}
            ORDER BY score DESC, created_at DESC
            LIMIT ${param_count + 1} OFFSET ${param_count + 2}
        """
        
        # Adjust params order for LIMIT and OFFSET
        params_ordered = params[:param_count] + [limit, offset]
        
        signals = await conn.fetch(query, *params_ordered)
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM signals
            WHERE {where_clause}
        """
        count_result = await conn.fetchrow(count_query, *params[:param_count])
        
        # Format results
        signals_list = []
        for sig in signals:
            signals_list.append({
                "id": sig['id'],
                "symbol": sig['symbol'],
                "timeframe": sig['timeframe'],
                "signal_type": sig['signal_type'],
                "direction": sig['direction'],
                "score": round(float(sig['score']), 4),
                "score_percent": round(float(sig['score']) * 100, 2),
                "entry_price": float(sig['entry_price']) if sig['entry_price'] else None,
                "stop_loss": float(sig['stop_loss']) if sig['stop_loss'] else None,
                "take_profit_1": float(sig['take_profit_1']) if sig['take_profit_1'] else None,
                "take_profit_2": float(sig['take_profit_2']) if sig['take_profit_2'] else None,
                "take_profit_3": float(sig['take_profit_3']) if sig['take_profit_3'] else None,
                "risk_reward_ratio": float(sig['risk_reward_ratio']) if sig['risk_reward_ratio'] else None,
                "is_active": sig['is_active'],
                "is_executed": sig['is_executed'],
                "filled_at": sig['filled_at'].isoformat() if sig['filled_at'] else None,
                "closed_at": sig['closed_at'].isoformat() if sig['closed_at'] else None,
                "realized_pnl": float(sig['realized_pnl']) if sig['realized_pnl'] else None,
                "created_at": sig['created_at'].isoformat(),
                "updated_at": sig['updated_at'].isoformat()
            })
        
        await conn.close()
        
        return {
            "signals": signals_list,
            "total": count_result['total'],
            "limit": limit,
            "offset": offset,
            "filters": {
                "min_score": min_score,
                "max_score": max_score,
                "symbol": symbol,
                "direction": direction,
                "days": days
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting signals history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Security routes to prevent 404 errors
@app.get("/.env")
async def block_env():
    """Block access to .env file."""
    raise HTTPException(status_code=404, detail="Not Found")


@app.get("/.git/{path:path}")
async def block_git(path: str):
    """Block access to .git directory."""
    raise HTTPException(status_code=404, detail="Not Found")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
