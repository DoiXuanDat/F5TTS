import json
from pathlib import Path
from typing import Dict

class ConfigService:
    def __init__(self):
        self.config_path = Path(__file__).parent.parent.parent / "frontend" / "public" / "config.json"
        self.config: Dict = {}
        
    def update_urls(self, backend_url: str, frontend_url: str):
        self.config = {
            "backendUrl": backend_url,
            "frontendUrl": frontend_url
        }
        
        # Ensure directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write config
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)