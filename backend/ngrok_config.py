import os
from pyngrok import conf, ngrok
from dotenv import load_dotenv
import logging
from services.config_service import ConfigService

logger = logging.getLogger(__name__)

class NgrokManager:
    def __init__(self):
        load_dotenv()
        self.auth_token = os.getenv("NGROK_AUTH_TOKEN")
        self.tunnel = None
        self.config_service = ConfigService()
        
    def start(self, port=8000):
        try:
            # Cấu hình ngrok
            if not self.auth_token:
                raise ValueError("NGROK_AUTH_TOKEN không tìm thấy trong file .env")
            
            conf.get_default().auth_token = self.auth_token
            
            # Đóng tất cả tunnels hiện có
            ngrok.kill()
            
            # Tạo tunnel mới
            self.tunnel = ngrok.connect(port)
            public_url = self.tunnel.public_url
            
            # In URL rõ ràng
            logger.info("=" * 50)
            logger.info(f"🚀 Ngrok tunnel started successfully!")
            logger.info(f"📡 Public URL: {public_url}")
            logger.info("=" * 50)
            
            return public_url
            
        except Exception as e:
            logger.error(f"❌ Ngrok startup error: {str(e)}")
            raise

    def stop(self):
        if self.tunnel:
            ngrok.disconnect(self.tunnel.public_url)

    def create_tunnels(self):
        try:
            # Kill any existing tunnels
            ngrok.kill()
            
            # Create tunnels with HTTPS
            self.tunnels = {
                'backend': ngrok.connect(5000, bind_tls=True).public_url,
                'frontend': ngrok.connect(3000, bind_tls=True).public_url
            }
            
            print("\n" + "=" * 50)
            print(f"Backend API accessible at: {self.tunnels['backend']}")
            print(f"Frontend accessible at: {self.tunnels['frontend']}")
            print("=" * 50 + "\n")
            
            # Update config with new URLs
            self.config_service.update_urls(
                self.tunnels['backend'],
                self.tunnels['frontend']
            )
            
            return self.tunnels
            
        except Exception as e:
            print(f"Error creating ngrok tunnels: {str(e)}")
            raise