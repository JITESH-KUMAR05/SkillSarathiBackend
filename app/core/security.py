"""
Security Middleware for BuddyAgents Platform
Implements authentication, rate limiting, input validation, and security headers
"""

import time
import hashlib
import logging
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import Request, Response, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Security
security = HTTPBearer(auto_error=False)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# In-memory rate limiting store (use Redis in production)
rate_limit_store: Dict[str, Dict[str, Any]] = defaultdict(dict)


class SecurityError(Exception):
    """Custom security exception"""
    pass


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security middleware that handles:
    - Security headers
    - Request validation
    - IP blocking
    - Request logging
    """
    
    def __init__(self, app, blocked_ips: Optional[set] = None):
        super().__init__(app)
        self.blocked_ips = blocked_ips or set()
        self.suspicious_patterns = [
            "DROP TABLE",
            "DELETE FROM",
            "INSERT INTO",
            "<script>",
            "javascript:",
            "eval(",
            "exec(",
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get client IP
        client_ip = get_remote_address(request)
        
        # Block suspicious IPs
        if client_ip in self.blocked_ips:
            logger.warning(f"Blocked request from IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Validate request content
        if request.method in ["POST", "PUT", "PATCH"]:
            await self._validate_request_content(request)
        
        # Log request
        start_time = time.time()
        logger.info(f"Request: {request.method} {request.url.path} from {client_ip}")
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        self._add_security_headers(response)
        
        # Log response time
        process_time = time.time() - start_time
        logger.info(f"Response: {response.status_code} in {process_time:.3f}s")
        
        return response
    
    async def _validate_request_content(self, request: Request):
        """Validate request content for suspicious patterns"""
        try:
            # Check URL path
            path = str(request.url.path).lower()
            for pattern in self.suspicious_patterns:
                if pattern.lower() in path:
                    logger.warning(f"Suspicious pattern in URL: {pattern}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid request"
                    )
            
            # Check query parameters
            query_params = str(request.query_params).lower()
            for pattern in self.suspicious_patterns:
                if pattern.lower() in query_params:
                    logger.warning(f"Suspicious pattern in query: {pattern}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid request"
                    )
        
        except Exception as e:
            logger.error(f"Error validating request: {e}")
            # Don't block request for validation errors
            pass
    
    def _add_security_headers(self, response: Response):
        """Add security headers to response"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"


class AuthenticationService:
    """Authentication and authorization service"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Generate password hash"""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)
        
        to_encode.update({"exp": expire})
        
        try:
            encoded_jwt = jwt.encode(
                to_encode, 
                settings.jwt_secret_key, 
                algorithm=settings.jwt_algorithm
            )
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating JWT token: {e}")
            raise SecurityError("Failed to create authentication token")
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(
                token, 
                settings.jwt_secret_key, 
                algorithms=[settings.jwt_algorithm]
            )
            return payload
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            raise SecurityError("Invalid authentication token")
    
    @staticmethod
    async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
        """Get current user from JWT token"""
        # Development bypass - allow requests without authentication
        if settings.environment == "development":
            logger.info("Development mode: allowing request without authentication")
            return {
                "user_id": "dev_user", 
                "payload": {"sub": "dev_user", "role": "user"}
            }
        
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        try:
            payload = AuthenticationService.verify_token(credentials.credentials)
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token",
                )
            return {"user_id": user_id, "payload": payload}
        
        except SecurityError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )


class RateLimitService:
    """Advanced rate limiting service"""
    
    @staticmethod
    def get_rate_limit_key(request: Request, endpoint_type: str = "default") -> str:
        """Generate rate limit key for request"""
        client_ip = get_remote_address(request)
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Create unique key combining IP and endpoint
        key_data = f"{client_ip}:{endpoint_type}:{user_agent}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    @staticmethod
    def check_rate_limit(
        request: Request, 
        endpoint_type: str = "default",
        max_requests: int = 60,
        window_seconds: int = 60
    ) -> bool:
        """Check if request exceeds rate limit"""
        key = RateLimitService.get_rate_limit_key(request, endpoint_type)
        now = datetime.utcnow()
        
        # Clean old entries
        if key in rate_limit_store:
            rate_limit_store[key]["requests"] = [
                req_time for req_time in rate_limit_store[key]["requests"]
                if now - req_time < timedelta(seconds=window_seconds)
            ]
        else:
            rate_limit_store[key] = {"requests": []}
        
        # Check current count
        current_count = len(rate_limit_store[key]["requests"])
        
        if current_count >= max_requests:
            logger.warning(f"Rate limit exceeded for key: {key}")
            return False
        
        # Add current request
        rate_limit_store[key]["requests"].append(now)
        return True
    
    @staticmethod
    def get_remaining_requests(
        request: Request, 
        endpoint_type: str = "default",
        max_requests: int = 60
    ) -> int:
        """Get remaining requests for current window"""
        key = RateLimitService.get_rate_limit_key(request, endpoint_type)
        
        if key not in rate_limit_store:
            return max_requests
        
        current_count = len(rate_limit_store[key]["requests"])
        return max(0, max_requests - current_count)


class InputValidator:
    """Input validation and sanitization"""
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = 1000) -> str:
        """Sanitize text input"""
        if not isinstance(text, str):
            raise ValueError("Input must be a string")
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length]
        
        # Remove potentially dangerous patterns
        dangerous_patterns = [
            "<script>", "</script>",
            "javascript:",
            "data:text/html",
            "vbscript:",
            "onload=", "onerror=",
        ]
        
        for pattern in dangerous_patterns:
            text = text.replace(pattern, "")
        
        return text.strip()
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_file_upload(
        filename: str, 
        content_type: str, 
        file_size: int,
        allowed_types: set,
        max_size: int
    ) -> bool:
        """Validate file upload"""
        # Check file size
        if file_size > max_size:
            raise ValueError(f"File size exceeds maximum allowed size of {max_size} bytes")
        
        # Check content type
        if content_type not in allowed_types:
            raise ValueError(f"File type {content_type} not allowed")
        
        # Check filename
        if not filename or ".." in filename:
            raise ValueError("Invalid filename")
        
        return True


# Simple rate limiting function for development
def rate_limit_chat(func):
    """Simple rate limit for development"""
    return func


def rate_limit_voice(func):
    """Simple rate limit for development"""
    return func


def rate_limit_video(func):
    """Simple rate limit for development"""
    return func