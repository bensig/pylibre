import os
import yaml
from typing import Optional, Dict, Any

class ConfigManager:
    """Manages configuration loading and access."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize with config file path."""
        self.config_path = config_path
        self.config = self.load_config()
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
            
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise Exception(f"Error loading config: {str(e)}")
            
    def get_strategy_group(self, group_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a strategy group."""
        return self.config.get("strategy_groups", {}).get(group_name)
        
    def get_network_config(self, network: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a network."""
        return self.config.get("networks", {}).get(network)
        
    def get_account_config(self, account: str) -> Optional[Dict[str, Any]]:
        """Get configuration for an account."""
        return self.config.get("accounts", {}).get(account)