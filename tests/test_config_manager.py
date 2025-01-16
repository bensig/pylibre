import unittest
from pathlib import Path
import yaml
from src.pylibre.manager.config_manager import ConfigManager

class TestConfigManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test configuration."""
        # Create a test config file
        cls.test_config_path = Path("tests/fixtures/test_config.yaml")
        cls.test_config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Sample test configuration
        test_config = {
            "networks": {
                "testnet": {
                    "api_url": "https://testnet.libre.org",
                    "private_keys": {
                        "bentester": "PRIVATE_KEY_PLACEHOLDER"
                    }
                }
            },
            "strategy_groups": {
                "btc_market_making": {
                    "description": "Test BTC/USDT market making",
                    "network": "testnet",
                    "pairs": ["BTC/USDT"],
                    "strategies": [
                        {
                            "name": "OrderBookMakerStrategy",
                            "accounts": ["bentester"],
                            "parameters": {
                                "update_interval_ms": 500
                            }
                        }
                    ]
                }
            },
            "accounts": {
                "bentester": {
                    "description": "Test account",
                    "networks": {
                        "testnet": {
                            "enabled": True,
                            "max_orders": 50
                        }
                    }
                }
            },
            "global_settings": {
                "log_level": "INFO"
            }
        }
        
        with open(cls.test_config_path, 'w') as f:
            yaml.dump(test_config, f)
            
        cls.config_manager = ConfigManager(str(cls.test_config_path))

    def test_load_config(self):
        """Test configuration loading."""
        self.assertIsNotNone(self.config_manager.config)
        self.assertIn("networks", self.config_manager.config)
        self.assertIn("strategy_groups", self.config_manager.config)
        self.assertIn("accounts", self.config_manager.config)
        self.assertIn("global_settings", self.config_manager.config)

    def test_get_network_config(self):
        """Test network configuration retrieval."""
        testnet_config = self.config_manager.get_network_config("testnet")
        self.assertIsNotNone(testnet_config)
        self.assertEqual(testnet_config["api_url"], "https://testnet.libre.org")

    def test_get_strategy_group(self):
        """Test strategy group configuration retrieval."""
        strategy_group = self.config_manager.get_strategy_group("btc_market_making")
        self.assertIsNotNone(strategy_group)
        self.assertEqual(strategy_group["network"], "testnet")
        self.assertEqual(strategy_group["pairs"], ["BTC/USDT"])

    def test_get_account_config(self):
        """Test account configuration retrieval."""
        account_config = self.config_manager.get_account_config("bentester")
        self.assertIsNotNone(account_config)
        self.assertTrue(account_config["networks"]["testnet"]["enabled"])
        self.assertEqual(account_config["networks"]["testnet"]["max_orders"], 50)

    def test_invalid_network(self):
        """Test invalid network handling."""
        network_config = self.config_manager.get_network_config("invalid_network")
        self.assertIsNone(network_config)

    def test_invalid_strategy_group(self):
        """Test invalid strategy group handling."""
        strategy_group = self.config_manager.get_strategy_group("invalid_group")
        self.assertIsNone(strategy_group)

    def test_invalid_account(self):
        """Test invalid account handling."""
        account_config = self.config_manager.get_account_config("invalid_account")
        self.assertIsNone(account_config)

    @classmethod
    def tearDownClass(cls):
        """Clean up test files."""
        if cls.test_config_path.exists():
            cls.test_config_path.unlink()

if __name__ == '__main__':
    unittest.main() 