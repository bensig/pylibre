from typing import Dict, Any, Optional
import json
from pathlib import Path

class AccountManager:
    def __init__(self, accounts_file='accounts.json'):
        self.accounts_file = accounts_file
        self.accounts = self.load_accounts()

    def load_accounts(self):
        """Load account configurations from JSON file."""
        try:
            with open(self.accounts_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ Accounts file not found: {self.accounts_file}")
            return {}
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON in accounts file: {self.accounts_file}")
            return {}

    def get_account_settings(self, account):
        """Get settings for a specific account."""
        return self.accounts.get(account)

    def validate_account(self, account, strategy, base_symbol, quote_symbol):
        """Validate account settings for a strategy and trading pair."""
        settings = self.get_account_settings(account)
        if not settings:
            print(f"❌ Account not found: {account}")
            return False

        # Check if strategy is allowed
        if strategy not in settings.get('allowed_strategies', []):
            print(f"❌ Strategy {strategy} not allowed for account {account}")
            return False

        # Check if trading pair is allowed
        pair = f"{base_symbol}/{quote_symbol}"
        if pair not in settings.get('allowed_pairs', []):
            print(f"❌ Trading pair {pair} not allowed for account {account}")
            return False

        return True