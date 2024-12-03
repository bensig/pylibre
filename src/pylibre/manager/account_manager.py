from typing import Dict, Any, Optional
import json
import os
from pathlib import Path

class AccountManager:
    def __init__(self, accounts_file: str = "accounts/accounts.json"):
        self.accounts_file = accounts_file
        self.accounts = self._load_accounts()

    def _load_accounts(self) -> Dict[str, Any]:
        """Load accounts configuration from JSON file."""
        try:
            with open(self.accounts_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️  No accounts file found at {self.accounts_file}")
            return {}
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing accounts file: {e}")
            return {}

    def get_account_config(self, account_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific account."""
        return self.accounts.get(account_name)

    def validate_account(self, account_name: str, strategy_name: str, 
                        quote_symbol: str, base_symbol: str) -> bool:
        """
        Validate if an account is properly configured for a strategy and trading pair.
        
        Args:
            account_name: Name of the trading account
            strategy_name: Name of the strategy to run
            quote_symbol: Quote asset symbol (e.g., 'BTC')
            base_symbol: Base asset symbol (e.g., 'LIBRE')
        """
        account = self.get_account_config(account_name)
        if not account:
            print(f"❌ Account {account_name} not found in configuration")
            return False

        # Check if strategy is allowed for this account
        if strategy_name not in account.get('allowed_strategies', []):
            print(f"❌ Strategy {strategy_name} not allowed for account {account_name}")
            return False

        # Check if trading pair is allowed (in format BASE/QUOTE)
        pair = f"{base_symbol}/{quote_symbol}"
        if pair not in account.get('allowed_pairs', []):
            print(f"❌ Trading pair {pair} not allowed for account {account_name}")
            return False

        # Validate wallet configuration
        if not account.get('wallet_name'):
            print(f"❌ No wallet name configured for account {account_name}")
            return False

        wallet_pwd_file = account.get('wallet_password_file')
        if not wallet_pwd_file or not os.path.exists(wallet_pwd_file):
            print(f"❌ Wallet password file not found for account {account_name}")
            return False

        return True

    def get_trading_config(self, account_name: str, strategy_name: str) -> Dict[str, Any]:
        """
        Get trading configuration for an account and strategy combination.
        
        Returns default values merged with account-specific and strategy-specific settings.
        """
        account = self.get_account_config(account_name)
        if not account:
            return {}

        # Start with default configuration
        config = {
            'interval': 5,
            'quantity': '100.00000000',
            'min_change_percentage': 0.01,
            'max_change_percentage': 0.20,
            'spread_percentage': 0.02,
        }

        # Merge with account-level settings
        config.update(account.get('default_settings', {}))

        # Merge with strategy-specific settings
        strategy_config = account.get('strategy_settings', {}).get(strategy_name, {})
        config.update(strategy_config)

        return config