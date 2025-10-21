"""
Secure secrets management using Google Cloud Secret Manager
Provides fallback to environment variables for development
"""

import os
import secrets
import string
from typing import Optional, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecretsManager:
    """Manages application secrets with Google Cloud Secret Manager integration"""
    
    def __init__(self):
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        self.use_secret_manager = (
            os.getenv('FLASK_ENV') == 'production' and 
            self.project_id is not None
        )
        self._client = None
        self._cache = {}
        
        if self.use_secret_manager:
            try:
                from google.cloud import secretmanager
                self._client = secretmanager.SecretManagerServiceClient()
                logger.info("Google Cloud Secret Manager initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Secret Manager: {e}")
                self.use_secret_manager = False
    
    def get_secret(self, secret_name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a secret value from Secret Manager or environment variables
        
        Args:
            secret_name: Name of the secret
            default: Default value if secret not found
            
        Returns:
            Secret value or default
        """
        # Check cache first
        if secret_name in self._cache:
            return self._cache[secret_name]
        
        secret_value = None
        
        if self.use_secret_manager:
            try:
                secret_value = self._get_from_secret_manager(secret_name)
            except Exception as e:
                logger.warning(f"Failed to get secret {secret_name} from Secret Manager: {e}")
        
        # Fallback to environment variable
        if secret_value is None:
            secret_value = os.getenv(secret_name, default)
        
        # Cache the value (but not None values)
        if secret_value is not None:
            self._cache[secret_name] = secret_value
        
        return secret_value
    
    def _get_from_secret_manager(self, secret_name: str) -> Optional[str]:
        """Get secret from Google Cloud Secret Manager"""
        if not self._client or not self.project_id:
            return None
        
        try:
            name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
            response = self._client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.error(f"Error accessing secret {secret_name}: {e}")
            return None
    
    def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """
        Set a secret value in Secret Manager (production only)
        
        Args:
            secret_name: Name of the secret
            secret_value: Value to store
            
        Returns:
            True if successful, False otherwise
        """
        if not self.use_secret_manager:
            logger.warning("Secret Manager not available, cannot set secret")
            return False
        
        try:
            # Create secret if it doesn't exist
            parent = f"projects/{self.project_id}"
            try:
                self._client.create_secret(
                    request={
                        "parent": parent,
                        "secret_id": secret_name,
                        "secret": {"replication": {"automatic": {}}},
                    }
                )
                logger.info(f"Created new secret: {secret_name}")
            except Exception:
                # Secret might already exist
                pass
            
            # Add secret version
            parent = f"projects/{self.project_id}/secrets/{secret_name}"
            response = self._client.add_secret_version(
                request={
                    "parent": parent,
                    "payload": {"data": secret_value.encode("UTF-8")},
                }
            )
            
            # Update cache
            self._cache[secret_name] = secret_value
            
            logger.info(f"Successfully set secret: {secret_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set secret {secret_name}: {e}")
            return False
    
    def generate_secure_key(self, length: int = 32) -> str:
        """Generate a cryptographically secure random key"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def get_database_url(self) -> str:
        """Get database URL with proper fallbacks"""
        if self.use_secret_manager:
            db_url = self.get_secret('DATABASE_URL')
            if db_url:
                return db_url

        # Development fallback - use absolute path for SQLite
        db_url = os.getenv('DATABASE_URL')
        if db_url:
            return db_url

        # Default to absolute path for SQLite
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'calendar_harvest_dev.db')
        return f'sqlite:///{db_path}'
    
    def get_oauth_credentials(self) -> Dict[str, Optional[str]]:
        """Get OAuth credentials for Google and Harvest"""
        return {
            'google_client_id': self.get_secret('GOOGLE_CLIENT_ID'),
            'google_client_secret': self.get_secret('GOOGLE_CLIENT_SECRET'),
            'google_redirect_uri': self.get_secret('GOOGLE_REDIRECT_URI'),
            'harvest_client_id': self.get_secret('HARVEST_CLIENT_ID'),
            'harvest_client_secret': self.get_secret('HARVEST_CLIENT_SECRET'),
            'harvest_redirect_uri': self.get_secret('HARVEST_REDIRECT_URI'),
        }
    
    def get_flask_secret_key(self) -> str:
        """Get Flask secret key, generating one if needed"""
        secret_key = self.get_secret('SECRET_KEY')
        
        if not secret_key or secret_key in ['dev-secret-key-change-in-production', 'dev-fallback-key']:
            # Generate a new secure key
            new_key = self.generate_secure_key(64)
            
            if self.use_secret_manager:
                # Store in Secret Manager
                if self.set_secret('SECRET_KEY', new_key):
                    logger.info("Generated and stored new Flask secret key")
                    return new_key
            
            # For development, use the generated key but warn
            logger.warning("Using generated secret key - not persisted in development")
            return new_key
        
        return secret_key
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate that all required secrets are available"""
        required_secrets = [
            'GOOGLE_CLIENT_ID',
            'GOOGLE_CLIENT_SECRET', 
            'GOOGLE_REDIRECT_URI',
            'HARVEST_CLIENT_ID',
            'HARVEST_CLIENT_SECRET',
            'HARVEST_REDIRECT_URI',
            'SECRET_KEY'
        ]
        
        results = {
            'valid': True,
            'missing_secrets': [],
            'weak_secrets': [],
            'using_secret_manager': self.use_secret_manager
        }
        
        for secret_name in required_secrets:
            value = self.get_secret(secret_name)
            if not value:
                results['missing_secrets'].append(secret_name)
                results['valid'] = False
            elif secret_name == 'SECRET_KEY' and value in [
                'dev-secret-key-change-in-production',
                'dev-fallback-key'
            ]:
                results['weak_secrets'].append(secret_name)
                results['valid'] = False
        
        return results
    
    def clear_cache(self):
        """Clear the secrets cache"""
        self._cache.clear()
        logger.info("Secrets cache cleared")


# Global instance
secrets_manager = SecretsManager()

# Convenience functions
def get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    """Get a secret value"""
    return secrets_manager.get_secret(name, default)

def get_database_url() -> str:
    """Get database URL"""
    return secrets_manager.get_database_url()

def get_oauth_credentials() -> Dict[str, Optional[str]]:
    """Get OAuth credentials"""
    return secrets_manager.get_oauth_credentials()

def get_flask_secret_key() -> str:
    """Get Flask secret key"""
    return secrets_manager.get_flask_secret_key()

def validate_configuration() -> Dict[str, Any]:
    """Validate configuration"""
    return secrets_manager.validate_configuration()
