"""
Calendar Harvest Integration - Desktop App Wrapper
Uses PyWebView to wrap the Flask application in a native macOS window
"""

import os
import sys
import threading
import time
import logging
from pathlib import Path
from dotenv import load_dotenv
import webview
import requests
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set Flask environment for desktop app
# Use 'development' to load .env.development configuration
os.environ['FLASK_ENV'] = 'development'

# Load environment variables
env_file = '.env.development'
if os.path.exists(env_file):
    load_dotenv(env_file)
    logger.info(f"Loaded configuration from {env_file}")
else:
    load_dotenv('.env')
    logger.info("Loaded configuration from .env")


class FlaskServer:
    """Manages the Flask server in a background thread"""
    
    def __init__(self, port=5001):
        self.port = port
        self.url = f'http://localhost:{port}'
        self.thread = None
        self.running = False
        
    def start(self):
        """Start Flask server in background thread"""
        logger.info(f"Starting Flask server on port {self.port}...")
        
        # Import Flask app here to avoid issues with environment setup
        from main import app
        
        def run_flask():
            try:
                # Disable Flask's default logger to reduce noise
                log = logging.getLogger('werkzeug')
                log.setLevel(logging.ERROR)
                
                app.run(
                    host='127.0.0.1',
                    port=self.port,
                    debug=False,
                    use_reloader=False,
                    threaded=True
                )
            except Exception as e:
                logger.error(f"Flask server error: {e}")
                self.running = False
        
        self.thread = threading.Thread(target=run_flask, daemon=True)
        self.thread.start()
        self.running = True
        
        # Wait for server to be ready
        self._wait_for_server()
        logger.info("Flask server is ready")
    
    def _wait_for_server(self, timeout=30):
        """Wait for Flask server to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f'{self.url}/health', timeout=1)
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(0.5)
        
        logger.warning(f"Server not ready after {timeout} seconds, proceeding anyway")
        return False
    
    def stop(self):
        """Stop Flask server"""
        logger.info("Stopping Flask server...")
        self.running = False


class DesktopApp:
    """Main desktop application class"""
    
    def __init__(self):
        self.server = FlaskServer(port=5001)
        self.window = None
        
    def start(self):
        """Start the desktop application"""
        logger.info("Starting Calendar Harvest Integration Desktop App")
        
        # Start Flask server
        self.server.start()
        
        # Create and show PyWebView window
        self._create_window()
    
    def _create_window(self):
        """Create the PyWebView window"""
        logger.info("Creating application window...")

        self.window = webview.create_window(
            title='Calendar Harvest Integration',
            url=self.server.url,
            width=1400,
            height=900,
            min_size=(1000, 700),
            background_color='#ffffff',
            resizable=True,
            fullscreen=False
        )

        # Set window icon (if available)
        icon_path = Path(__file__).parent / 'static' / 'icon.png'
        if icon_path.exists():
            self.window.icon = str(icon_path)

        # Start the window (blocking call)
        # Note: PyWebView will use the Flask server already running on localhost:5001
        webview.start(debug=False)
    
    def on_close(self):
        """Handle window close event"""
        logger.info("Application closing...")
        self.server.stop()


def main():
    """Main entry point"""
    try:
        app = DesktopApp()
        app.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

