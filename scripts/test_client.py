#!/usr/bin/env python3
"""
Test script for LibreClient functionality.
Tests basic operations like checking balances and transferring tokens.
"""

import sys
import os
import time
import site

# Add site-packages to the Python path
site_packages = site.getsitepackages()
for path in site_packages:
    if path not in sys.path:
        sys.path.insert(0, path)

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Try to import pyntelope directly to check if it's available
try:
    import pyntelope
    print(f"Found pyntelope at: {pyntelope.__file__}")
except ImportError as e:
    print(f"Error importing pyntelope: {e}")
    print("Python path:", sys.path)
    sys.exit(1)

from pylibre.client import LibreClient

def main():
    # Initialize client with verbose output
    print("Initializing LibreClient...")
    client = LibreClient(network='testnet', verbose=True)
    
    # Define accounts to test
    from_account = "bentester"
    to_account = "bentest3"
    
    # Test tokens to transfer
    tokens = ["BTC", "USDT", "LIBRE"]
    
    for token in tokens:
        print(f"\n{'='*50}")
        print(f"Testing {token} transfers")
        print(f"{'='*50}")
        
        # Check initial balances
        print(f"\nChecking initial balances for {token}...")
        try:
            from_balance = client.get_currency_balance(from_account, token)
            to_balance = client.get_currency_balance(to_account, token)
            
            print(f"{from_account} balance: {from_balance}")
            print(f"{to_account} balance: {to_balance}")
            
            # Determine transfer amount (a small fraction of available balance)
            amount = 0
            if token == "BTC":
                amount = "0.00001000"
            elif token == "USDT":
                amount = "0.10000000"
            elif token == "LIBRE":
                amount = "0.1000"
                
            quantity = f"{amount} {token}"
            
            # Execute transfer
            print(f"\nTransferring {quantity} from {from_account} to {to_account}...")
            result = client.transfer(from_account, to_account, quantity, memo="Testing client functionality")
            
            if result["success"]:
                print(f"Transfer successful! Transaction ID: {result['data']['transaction_id']}")
                
                # Wait a moment for the blockchain to process
                print("Waiting for blockchain to process transaction...")
                time.sleep(2)
                
                # Check updated balances
                print(f"\nChecking updated balances for {token}...")
                from_balance_after = client.get_currency_balance(from_account, token)
                to_balance_after = client.get_currency_balance(to_account, token)
                
                print(f"{from_account} balance: {from_balance_after}")
                print(f"{to_account} balance: {to_balance_after}")
            else:
                print(f"Transfer failed: {result['error']}")
                
        except Exception as e:
            print(f"Error testing {token}: {str(e)}")
    
    print("\nClient testing completed!")

if __name__ == "__main__":
    main() 