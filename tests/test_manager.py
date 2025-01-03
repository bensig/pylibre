import unittest
from unittest.mock import Mock, patch
from pylibre.manager.account_manager import AccountManager
import json
import os

class TestAccountManager(unittest.TestCase):
    def setUp(self):
        self.test_accounts = {
            "bentester": {
                "allowed_strategies": ["RandomWalkStrategy"],
                "allowed_pairs": ["LIBRE/BTC", "BTC/USDT"],
                "default_settings": {
                    "interval": 5,
                    "quantity": "100.00000000"
                }
            }
        }
        
        # Create a temporary accounts.json file
        with open('accounts.json', 'w') as f:
            json.dump(self.test_accounts, f)
            
    def tearDown(self):
        # Clean up the temporary file
        if os.path.exists('accounts.json'):
            os.remove('accounts.json')

    def test_load_accounts(self):
        manager = AccountManager()
        self.assertEqual(manager.accounts, self.test_accounts)

    def test_get_account_settings(self):
        manager = AccountManager()
        settings = manager.get_account_settings("bentester")
        self.assertEqual(settings, self.test_accounts["bentester"])

    def test_get_nonexistent_account(self):
        manager = AccountManager()
        settings = manager.get_account_settings("nonexistent")
        self.assertIsNone(settings)

    def test_validate_account(self):
        manager = AccountManager()
        # Test with valid account and strategy
        self.assertTrue(
            manager.validate_account(
                "bentester",
                "RandomWalkStrategy",
                "BTC",
                "USDT"
            )
        )

    def test_validate_invalid_account(self):
        manager = AccountManager()
        # Test with invalid account
        self.assertFalse(
            manager.validate_account(
                "nonexistent",
                "RandomWalkStrategy",
                "BTC",
                "USDT"
            )
        )

    def test_validate_invalid_strategy(self):
        manager = AccountManager()
        # Test with invalid strategy
        self.assertFalse(
            manager.validate_account(
                "bentester",
                "NonexistentStrategy",
                "BTC",
                "USDT"
            )
        )

    def test_validate_invalid_pair(self):
        manager = AccountManager()
        # Test with invalid trading pair
        self.assertFalse(
            manager.validate_account(
                "bentester",
                "RandomWalkStrategy",
                "INVALID",
                "PAIR"
            )
        )

if __name__ == '__main__':
    unittest.main() 