import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration from environment variables"""

    # Flask configuration
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = FLASK_ENV == 'development'

    # Steam API configuration
    STEAM_API_KEY = os.getenv('STEAM_API_KEY')
    STEAM_OPENID_URL = 'https://steamcommunity.com/openid/login'

    # OpenRouter AI API configuration
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'
    OPENROUTER_MODEL = 'x-ai/grok-beta'  # Free tier model
    OPENROUTER_MAX_TOKENS = 2000
    OPENROUTER_TEMPERATURE = 0.7

    # Database configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///steamachieve.db')
    DATABASE_PATH = DATABASE_URL.replace('sqlite:///', '')

    # Cache configuration (in seconds)
    CACHE_GAME_LIBRARY = 3600  # 1 hour
    CACHE_ACHIEVEMENTS = 1800  # 30 minutes
    CACHE_GUIDE_SEARCH = 604800  # 7 days
    CACHE_AI_GUIDE = 2592000  # 30 days

    # Rate limiting
    DDGS_MAX_SEARCHES_PER_MINUTE = 5
    DDGS_MAX_RESULTS = 10
    AI_REQUESTS_PER_MINUTE = 10  # OpenRouter free tier limit
    AI_REQUESTS_PER_DAY = 200  # Conservative daily limit for free tier

    # Session configuration
    SESSION_COOKIE_SECURE = FLASK_ENV == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours

    @staticmethod
    def validate():
        """Validate required configuration"""
        if not Config.STEAM_API_KEY:
            raise ValueError("STEAM_API_KEY must be set in .env file")
        return True
