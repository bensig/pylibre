#!/usr/bin/env python3
"""
Script to check balances of all accounts in the config file.
"""

import sys
import os
import yaml
from decimal import Decimal

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pylibre.client import LibreClient

def load_accounts_from_config(config_path='config/config.yaml'):
    """Load accounts from the config file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Get accounts from the testnet network
        accounts = []
        if 'networks' in config and 'testnet' in config['networks']:
            if 'private_keys' in config['networks']['testnet']:
                accounts = list(config['networks']['testnet']['private_keys'].keys())
        
        return accounts
    except Exception as e:
        print(f"Error loading config: {str(e)}")
        return []

def check_balances(client, accounts, tokens=None):
    """Check balances for all accounts and tokens."""
    if tokens is None:
        tokens = ["LIBRE", "BTC", "USDT"]
    
    results = {}
    
    for account in accounts:
        results[account] = {}
        print(f"\nChecking balances for account: {account}")
        
        for token in tokens:
            try:
                balance = client.get_currency_balance(account, token)
                results[account][token] = balance
                print(f"  {token}: {balance}")
            except Exception as e:
                print(f"  Error getting {token} balance: {str(e)}")
                results[account][token] = "Error"
    
    return results

def main():
    # Initialize client
    print("Initializing LibreClient...")
    client = LibreClient(network='testnet', verbose=True)
    
    # Load accounts from config
    print("\nLoading accounts from config...")
    accounts = load_accounts_from_config()
    print(f"Found {len(accounts)} accounts: {', '.join(accounts)}")
    
    # Check balances
    print("\nChecking balances for all accounts...")
    balances = check_balances(client, accounts)
    
    # Print summary
    print("\nBalance Summary:")
    print("=" * 50)
    for account, tokens in balances.items():
        print(f"\n{account}:")
        for token, balance in tokens.items():
            print(f"  {token}: {balance}")
    
    print("\nBalance check completed!")

if __name__ == "__main__":
    main() 