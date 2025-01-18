import unittest
from pathlib import Path
import yaml
from src.pylibre.manager.config_manager import ConfigManager

class TestConfigManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test configuration."""
        cls.test_config_path = Path("tests/fixtures/test_config.yaml")
        cls.test_config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Sample test configuration matching new structure
        test_config = {
            "networks": {
                "testnet": {
                    "api_url": "https://testnet.libre.org",
                    "private_keys": {
                        "bentester": "PRIVATE_KEY_PLACEHOLDER"
                    }
                }
            },
            "strategies": {
                "defaults": {
                    "OrderBookMakerStrategy": {
                        "update_interval_ms": 500,
                        "min_spread_percentage": 0.06,
                        "max_spread_percentage": 0.10,
                        "num_orders": 20,
                        "quantity_distribution": "equal",
                        "order_spacing": "linear"
                    },
                    "MarketRateStrategy": {
                        "update_interval_ms": 500,
                        "spread_percentage": 0.02
                    }
                },
                "BTC/USDT": {
                    "OrderBookMakerStrategy": {
                        "min_order_value_usd": 10.0,
                        "max_order_value_usd": 100.0
                    }
                }
            },
            "strategy_groups": {
                "btc_market_making": {
                    "description": "BTC/USDT market making",
                    "pairs": ["BTC/USDT"],
                    "price_sources": {
                        "BTC/USDT": {
                            "source": "binance",
                            "reference_symbol": "BTCUSDT",
                            "update_interval_ms": 100
                        }
                    },
                    "strategies": [
                        {
                            "name": "OrderBookMakerStrategy",
                            "account": "bentester"
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
            }
        }
        
        with open(cls.test_config_path, 'w') as f:
            yaml.dump(test_config, f)
            
        cls.config_manager = ConfigManager(str(cls.test_config_path))

    def test_load_config(self):
        """Test configuration loading."""
        self.assertIsNotNone(self.config_manager.config)
        self.assertIn("networks", self.config_manager.config)
        self.assertIn("strategies", self.config_manager.config)
        self.assertIn("strategy_groups", self.config_manager.config)
        self.assertIn("accounts", self.config_manager.config)

    def test_get_strategy_defaults(self):
        """Test strategy default parameters retrieval."""
        defaults = self.config_manager.get_strategy_defaults("OrderBookMakerStrategy")
        self.assertIsNotNone(defaults)
        self.assertEqual(defaults["update_interval_ms"], 500)
        self.assertEqual(defaults["min_spread_percentage"], 0.06)

    def test_get_pair_parameters(self):
        """Test pair-specific parameters retrieval."""
        pair_params = self.config_manager.get_pair_parameters("BTC/USDT")
        self.assertIsNotNone(pair_params)
        self.assertIn("OrderBookMakerStrategy", pair_params)
        self.assertEqual(pair_params["OrderBookMakerStrategy"]["min_order_value_usd"], 10.0)

    def test_get_strategy_parameters(self):
        """Test combined strategy parameters retrieval."""
        params = self.config_manager.get_strategy_parameters("OrderBookMakerStrategy", "BTC/USDT")
        self.assertIsNotNone(params)
        # Check default parameters
        self.assertEqual(params["update_interval_ms"], 500)
        self.assertEqual(params["min_spread_percentage"], 0.06)
        # Check pair-specific parameters
        self.assertEqual(params["min_order_value_usd"], 10.0)
        self.assertEqual(params["max_order_value_usd"], 100.0)

    def test_get_strategy_group(self):
        """Test strategy group configuration retrieval."""
        group = self.config_manager.get_strategy_group("btc_market_making")
        self.assertIsNotNone(group)
        self.assertEqual(group["pairs"], ["BTC/USDT"])
        # Verify strategy parameters are populated
        self.assertIn("parameters", group["strategies"][0])
        self.assertEqual(group["strategies"][0]["account"], "bentester")

    def test_get_network_config(self):
        """Test network configuration retrieval."""
        network_config = self.config_manager.get_network_config("testnet")
        self.assertIsNotNone(network_config)
        self.assertEqual(network_config["api_url"], "https://testnet.libre.org")

    def test_get_account_config(self):
        """Test account configuration retrieval."""
        account_config = self.config_manager.get_account_config("bentester")
        self.assertIsNotNone(account_config)
        self.assertTrue(account_config["networks"]["testnet"]["enabled"])
        self.assertEqual(account_config["networks"]["testnet"]["max_orders"], 50)

    def test_get_price_sources(self):
        """Test price sources retrieval."""
        price_sources = self.config_manager.get_price_sources("btc_market_making")
        self.assertIsNotNone(price_sources)
        self.assertIn("BTC/USDT", price_sources)
        self.assertEqual(price_sources["BTC/USDT"]["source"], "binance")

    def test_invalid_strategy_defaults(self):
        """Test invalid strategy defaults handling."""
        defaults = self.config_manager.get_strategy_defaults("InvalidStrategy")
        self.assertIsNone(defaults)

    def test_invalid_pair_parameters(self):
        """Test invalid pair parameters handling."""
        pair_params = self.config_manager.get_pair_parameters("INVALID/PAIR")
        self.assertIsNone(pair_params)

    def test_invalid_strategy_group(self):
        """Test invalid strategy group handling."""
        group = self.config_manager.get_strategy_group("invalid_group")
        self.assertIsNone(group)

    @classmethod
    def tearDownClass(cls):
        """Clean up test files."""
        if cls.test_config_path.exists():
            cls.test_config_path.unlink()

if __name__ == '__main__':
    unittest.main()