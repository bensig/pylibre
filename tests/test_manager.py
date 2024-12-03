import unittest
from unittest.mock import patch, mock_open
import json
from pylibre.manager.account_manager import AccountManager

class TestAccountManager(unittest.TestCase):
    def setUp(self):
        self.test_accounts = {
            "bentester": {
                "wallet_name": "bentester",
                "wallet_password_file": "bentester_wallet.pwd",
                "allowed_strategies": [
                    "RandomWalkStrategy",
                    "MeanReversionStrategy"
                ],
                "allowed_pairs": [
                    "LIBRE/BTC",
                    "LIBRE/USDT"
                ],
                "default_settings": {
                    "interval": 5,
                    "quantity": "100.00000000",
                    "min_change_percentage": 0.01,
                    "max_change_percentage": 0.20,
                    "spread_percentage": 0.02
                },
                "strategy_settings": {
                    "RandomWalkStrategy": {
                        "interval": 5,
                        "quantity": "100.00000000"
                    }
                }
            }
        }

    @patch("builtins.open", new_callable=mock_open)
    def test_load_accounts(self, mock_file):
        # Mock the JSON file content
        mock_file.return_value.read.return_value = json.dumps(self.test_accounts)
        
        manager = AccountManager()
        self.assertEqual(manager.accounts, self.test_accounts)

    def test_get_account_config(self):
        with patch("builtins.open", mock_open(read_data=json.dumps(self.test_accounts))):
            manager = AccountManager()
            
            # Test existing account
            config = manager.get_account_config("bentester")
            self.assertIsNotNone(config)
            self.assertEqual(config["wallet_name"], "bentester")
            
            # Test non-existent account
            config = manager.get_account_config("nonexistent")
            self.assertIsNone(config)

    def test_validate_account(self):
        with patch("builtins.open", mock_open(read_data=json.dumps(self.test_accounts))):
            manager = AccountManager()
            
            # Test valid configuration
            self.assertTrue(
                manager.validate_account(
                    "bentester", 
                    "RandomWalkStrategy",
                    "BTC",
                    "LIBRE"
                )
            )
            
            # Test invalid strategy
            self.assertFalse(
                manager.validate_account(
                    "bentester",
                    "InvalidStrategy",
                    "BTC",
                    "LIBRE"
                )
            )
            
            # Test invalid pair
            self.assertFalse(
                manager.validate_account(
                    "bentester",
                    "RandomWalkStrategy",
                    "ETH",
                    "LIBRE"
                )
            )

    def test_get_trading_config(self):
        with patch("builtins.open", mock_open(read_data=json.dumps(self.test_accounts))):
            manager = AccountManager()
            
            # Test getting config for existing strategy
            config = manager.get_trading_config("bentester", "RandomWalkStrategy")
            self.assertEqual(config["interval"], 5)
            self.assertEqual(config["quantity"], "100.00000000")
            
            # Test default values are included
            self.assertIn("spread_percentage", config)
            self.assertEqual(config["spread_percentage"], 0.02)

if __name__ == '__main__':
    unittest.main() 