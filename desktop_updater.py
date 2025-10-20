"""
Auto-update checker for Calendar Harvest Integration Desktop App
Checks GitHub releases for new versions and notifies user
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from packaging import version

logger = logging.getLogger(__name__)

# Current app version
APP_VERSION = "1.0.0"
GITHUB_REPO = "DvorakJosef/Calendar-Harvest-Integration"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# Cache file for update check (check once per day)
CACHE_DIR = Path.home() / '.calendar_harvest_integration'
UPDATE_CACHE_FILE = CACHE_DIR / 'update_check.json'


class UpdateChecker:
    """Checks for application updates"""
    
    def __init__(self):
        self.current_version = APP_VERSION
        self.latest_version = None
        self.download_url = None
        self.release_notes = None
        self.update_available = False
        
    def check_for_updates(self, force=False):
        """
        Check for updates from GitHub releases
        
        Args:
            force: If True, skip cache and check immediately
            
        Returns:
            dict: Update information or None if no update available
        """
        # Check cache first
        if not force and self._is_cache_valid():
            logger.info("Using cached update check result")
            return self._load_cache()
        
        try:
            logger.info(f"Checking for updates from {GITHUB_API_URL}")
            response = requests.get(GITHUB_API_URL, timeout=5)
            response.raise_for_status()
            
            release_data = response.json()
            self.latest_version = release_data.get('tag_name', '').lstrip('v')
            self.release_notes = release_data.get('body', '')
            
            # Find .dmg download URL
            for asset in release_data.get('assets', []):
                if asset['name'].endswith('.dmg'):
                    self.download_url = asset['browser_download_url']
                    break
            
            # Compare versions
            self.update_available = self._is_newer_version(
                self.latest_version,
                self.current_version
            )
            
            # Cache the result
            self._save_cache()
            
            if self.update_available:
                logger.info(f"Update available: {self.latest_version}")
                return {
                    'available': True,
                    'current_version': self.current_version,
                    'latest_version': self.latest_version,
                    'download_url': self.download_url,
                    'release_notes': self.release_notes,
                }
            else:
                logger.info(f"App is up to date (v{self.current_version})")
                return {'available': False}
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to check for updates: {e}")
            return None
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            return None
    
    def _is_newer_version(self, latest, current):
        """Compare version strings"""
        try:
            return version.parse(latest) > version.parse(current)
        except Exception as e:
            logger.warning(f"Error comparing versions: {e}")
            return False
    
    def _is_cache_valid(self):
        """Check if cached update check is still valid (24 hours)"""
        if not UPDATE_CACHE_FILE.exists():
            return False
        
        try:
            with open(UPDATE_CACHE_FILE, 'r') as f:
                cache = json.load(f)
            
            cache_time = datetime.fromisoformat(cache.get('timestamp', ''))
            if datetime.now() - cache_time < timedelta(hours=24):
                return True
        except Exception as e:
            logger.warning(f"Error reading cache: {e}")
        
        return False
    
    def _save_cache(self):
        """Save update check result to cache"""
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'current_version': self.current_version,
                'latest_version': self.latest_version,
                'update_available': self.update_available,
                'download_url': self.download_url,
            }
            
            with open(UPDATE_CACHE_FILE, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving cache: {e}")
    
    def _load_cache(self):
        """Load cached update check result"""
        try:
            with open(UPDATE_CACHE_FILE, 'r') as f:
                cache = json.load(f)
            
            self.latest_version = cache.get('latest_version')
            self.update_available = cache.get('update_available', False)
            self.download_url = cache.get('download_url')
            
            return {
                'available': self.update_available,
                'current_version': self.current_version,
                'latest_version': self.latest_version,
                'download_url': self.download_url,
            }
        except Exception as e:
            logger.warning(f"Error loading cache: {e}")
            return None


def check_for_updates_background():
    """
    Background update check (can be called on app startup)
    Returns update info if available
    """
    checker = UpdateChecker()
    return checker.check_for_updates()

