import os
import yaml
from typing import Optional, Dict, Any, List

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

    def get_strategy_defaults(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """Get default parameters for a strategy."""
        return self.config.get("strategies", {}).get("defaults", {}).get(strategy_name)

    def get_pair_parameters(self, pair: str) -> Optional[Dict[str, Any]]:
        """Get pair-specific parameters."""
        return self.config.get("strategies", {}).get(pair)

    def get_strategy_parameters(self, strategy_name: str, pair: str) -> Dict[str, Any]:
        """Get combined strategy parameters (defaults + pair specific)."""
        # Get default parameters for the strategy
        defaults = self.get_strategy_defaults(strategy_name) or {}
        
        # Get pair-specific parameters for the strategy
        pair_params = self.get_pair_parameters(pair)
        if pair_params and strategy_name in pair_params:
            strategy_pair_params = pair_params[strategy_name]
        else:
            strategy_pair_params = {}
        
        # Combine defaults with pair-specific parameters
        combined_params = {**defaults, **strategy_pair_params}
        
        # Debugging: Print the combined parameters
        print(f"Retrieved parameters for {strategy_name} and {pair}: {combined_params}")
        
        return combined_params
            
    def get_strategy_group(self, group_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a strategy group."""
        group = self.config.get("strategy_groups", {}).get(group_name)
        if not group:
            return None

        # Enhance the group config with strategy parameters
        if "strategies" in group:
            for strategy in group["strategies"]:
                pair = group["pairs"][0]  # Currently assuming one pair per group
                strategy["parameters"] = self.get_strategy_parameters(strategy["name"], pair)

        return group
        
    def get_network_config(self, network: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a network."""
        return self.config.get("networks", {}).get(network)
        
    def get_account_config(self, account: str) -> Optional[Dict[str, Any]]:
        """Get configuration for an account."""
        return self.config.get("accounts", {}).get(account)

    def get_price_sources(self, group_name: str) -> Optional[Dict[str, Any]]:
        """Get price sources for a strategy group."""
        group = self.get_strategy_group(group_name)
        return group.get("price_sources") if group else None