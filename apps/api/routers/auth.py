"""Authentication router for Million Trader API."""

from datetime import datetime, timedelta
from typing import Optional
import re

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, field_validator, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import sys
sys.path.append('/packages')

from common.config import get_settings
from common.database import User
from common.logging import get_logger
from dependencies import get_db

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()

# Password hashing - use argon2 instead of bcrypt to avoid the 72-byte limit
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# JWT token scheme
security = HTTPBearer()

# Username validation pattern: alphanumeric, underscore, hyphen only
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')


class UserCreate(BaseModel):
    """User creation schema."""
    username: str = Field(..., min_length=3, max_length=30)
    email: EmailStr
    password: str = Field(..., min_length=8)
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not USERNAME_PATTERN.match(v):
            raise ValueError(
                'Username must contain only alphanumeric characters, underscores, and hyphens'
            )
        
        # Prevent usernames that might cause confusion
        if v.lower() in ['admin', 'root', 'system', 'api', 'support', 'help', 'null', 'undefined']:
            raise ValueError('This username is reserved')
        
        return v


class UserLogin(BaseModel):
    """User login schema."""
    username: str = Field(..., min_length=3, max_length=30)
    password: str
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not USERNAME_PATTERN.match(v):
            raise ValueError(
                'Username must contain only alphanumeric characters, underscores, and hyphens'
            )
        return v


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str
    expires_in: int


class UserResponse(BaseModel):
    """User response schema."""
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    risk_percent: float
    max_positions: int
    telegram_enabled: bool
    discord_enabled: bool
    email_enabled: bool
    min_signal_score: float
    created_at: datetime
    # Subscription fields
    subscription_status: str
    current_period_end: Optional[datetime]
    plan_id: Optional[str]
    stripe_customer_id: Optional[str]
    telegram_user_id: Optional[str]
    
    class Config:
        from_attributes = True


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.api.jwt_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.api.jwt_secret, 
        algorithm=settings.api.jwt_algorithm
    )
    
    return encoded_jwt


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Get user by username."""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """Authenticate user credentials."""
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.api.jwt_secret,
            algorithms=[settings.api.jwt_algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_username(db, username)
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@router.post("/register", response_model=UserResponse)
async def register_user(
    user: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user."""
    # Check if user already exists
    existing_user = await get_user_by_username(db, user.username)
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )
    
    existing_email = await get_user_by_email(db, user.email)
    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    logger.info(f"New user registered: {user.username}")
    return db_user


@router.post("/login", response_model=Token)
async def login_user(
    user: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Login user and return JWT token."""
    authenticated_user = await authenticate_user(db, user.username, user.password)
    if not authenticated_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not authenticated_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )
    
    access_token_expires = timedelta(minutes=settings.api.jwt_expire_minutes)
    access_token = create_access_token(
        data={"sub": authenticated_user.username},
        expires_delta=access_token_expires
    )
    
    logger.info(f"User logged in: {user.username}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.api.jwt_expire_minutes * 60
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information."""
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: User = Depends(get_current_active_user)
):
    """Refresh JWT token."""
    access_token_expires = timedelta(minutes=settings.api.jwt_expire_minutes)
    access_token = create_access_token(
        data={"sub": current_user.username},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.api.jwt_expire_minutes * 60
    }


@router.get("/subscription-info")
async def get_subscription_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user's subscription information."""
    from middleware.subscription import get_user_subscription_info
    
    try:
        subscription_info = await get_user_subscription_info(current_user)
        return subscription_info
    except Exception as e:
        # Return default subscription info for users without subscriptions
        return {
            "status": "inactive",
            "is_active": False,
            "current_period_end": None,
            "plan_id": None,
            "has_stripe_customer": False,
            "telegram_linked": False,
            "subscription_created_at": None,
            "subscription_updated_at": None
        }



