import os
import json
from pyngrok import conf, ngrok
from dotenv import load_dotenv
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class NgrokManager:
    def __init__(self):
        load_dotenv()
        self.auth_token = os.getenv("NGROK_AUTH_TOKEN")
        self.tunnels = {}
        
        # Create config directory if it doesn't exist
        self.config_path = Path(__file__).parent.parent / "static" / "config.json"
        os.makedirs(self.config_path.parent, exist_ok=True)
    
    def create_tunnels(self):
        try:
            # Kill any existing tunnels
            ngrok.kill()
            
            # Create tunnels with HTTPS
            self.tunnels = {
                'backend': ngrok.connect(8000, bind_tls=True),
                'frontend': ngrok.connect(3000, bind_tls=True)  # Giả sử frontend chạy ở cổng 3000
            }
            
            print("\n" + "=" * 50)
            print(f"Backend API accessible at: {self.tunnels['backend'].public_url}")
            print(f"Frontend accessible at: {self.tunnels['frontend'].public_url}")
            print("=" * 50 + "\n")
            
            return {
                'backend': self.tunnels['backend'].public_url,
                'frontend': self.tunnels['frontend'].public_url
            }
            
        except Exception as e:
            print(f"Error creating ngrok tunnels: {str(e)}")
            raise
        
    def start(self, port=8000):
        try:
            # Configure ngrok
            if not self.auth_token:
                raise ValueError("NGROK_AUTH_TOKEN not found in .env file")
            
            conf.get_default().auth_token = self.auth_token
            
            # Close existing tunnels
            ngrok.kill()
            
            # Create a new tunnel
            self.tunnels['backend'] = ngrok.connect(port, bind_tls=True)
            public_url = self.tunnels['backend'].public_url
            
            # Save the URL to a config file that frontend can access
            self.update_config(public_url)
            
            # Print clear URL
            logger.info("=" * 50)
            logger.info(f"🚀 Ngrok tunnel started successfully!")
            logger.info(f"📡 Public URL: {public_url}")
            logger.info("=" * 50)
            
            return public_url
            
        except Exception as e:
            logger.error(f"❌ Ngrok startup error: {str(e)}")
            raise

    def stop(self):
        ngrok.kill()
        logger.info("Ngrok tunnels stopped")

    def update_config(self, public_url):
        """Save ngrok URL to a config file that can be accessed by the frontend"""
        try:
            config = {
                "apiBaseUrl": public_url,
                "timestamp": str(datetime.now())
            }
            
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
            logger.info(f"✅ Updated config at {self.config_path} with URL: {public_url}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update config: {e}")