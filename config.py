import os
from dotenv import load_dotenv

class Config:
    """Base configuration class."""
    
    def __init__(self):
        # Load environment-specific .env file
        env = os.getenv('FLASK_ENV', 'development')
        env_file = f'.env.{env}'
        
        if os.path.exists(env_file):
            load_dotenv(env_file)
            print(f"Loaded configuration from {env_file}")
        else:
            # Fallback to default .env file
            load_dotenv('.env')
            print("Loaded configuration from .env")
    
    # Google OAuth Configuration
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI')
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-fallback-key')
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///calendar_harvest.db')
    
    # Optional Configuration
    TIMEZONE = os.getenv('TIMEZONE', 'UTC')
    PORT = int(os.getenv('PORT', 5001))
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Environment flags
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    # GCP Configuration
    GOOGLE_CLOUD_PROJECT = os.getenv('GOOGLE_CLOUD_PROJECT')

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    DATABASE_URL = 'sqlite:///test_calendar_harvest.db'

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on FLASK_ENV environment variable."""
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])
