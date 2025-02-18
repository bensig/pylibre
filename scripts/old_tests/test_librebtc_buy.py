#!/usr/bin/env python3
"""
Test script for LIBRE/BTC buy orders with different parameters.
This script tests various buy order configurations to identify what works.
"""

import sys
import os
import time
from decimal import Decimal

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pylibre.client import LibreClient

def place_buy_order(client, account, quantity, price, base_symbol, quote_symbol, dex_contract):
    """Place a buy order for a specific trading pair."""
    print(f"\nPlacing buy order: {quantity} {base_symbol} @ {price} {quote_symbol}")
    
    # Calculate the amount of quote currency to send
    quote_amount = Decimal(str(quantity)) * Decimal(str(price))
    quote_amount_str = f"{quote_amount:.8f}"
    
    # Determine the contract for the quote symbol
    quote_contract = f"{quote_symbol.lower()}.libre"
    
    # Create the memo with the correct format
    memo = f"buy:{quantity} {base_symbol}:{price} {quote_symbol}"
    
    print(f"Transfer Details:")
    print(f"From: {account}")
    print(f"To: {dex_contract}")
    print(f"Amount: {quote_amount_str} {quote_symbol}")
    print(f"Contract: {quote_contract}")
    print(f"Memo: {memo}")
    
    try:
        result = client.transfer(
            from_account=account,
            to_account=dex_contract,
            quantity=f"{quote_amount_str} {quote_symbol}",
            memo=memo,
            contract=quote_contract
        )
        
        if result.get("success"):
            print("✅ Buy order placed successfully")
            print(f"Transaction ID: {result.get('data', {}).get('transaction_id')}")
            return True
        else:
            print(f"❌ Failed to place buy order: {result.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Error placing buy order: {str(e)}")
        return False

def main():
    # Initialize client
    print("Initializing LibreClient...")
    client = LibreClient(network='testnet', verbose=True)
    
    # Define account to test
    account = "bentest3"
    
    # Define trading pair parameters
    base_symbol = "LIBRE"
    quote_symbol = "BTC"
    dex_contract = "dex.libre"
    
    print(f"\n{'='*50}")
    print(f"Testing LIBRE/BTC Buy Orders with {account}")
    print(f"{'='*50}")
    
    # Check initial balances
    print("\nChecking initial balances...")
    base_contract = "eosio.token" if base_symbol == "LIBRE" else f"{base_symbol.lower()}.libre"
    quote_contract = f"{quote_symbol.lower()}.libre"
    
    print(f"Using contract: {base_contract} for symbol: {base_symbol}")
    print(f"Using contract: {quote_contract} for symbol: {quote_symbol}")
    
    base_balance = client.get_currency_balance(account, base_symbol)
    quote_balance = client.get_currency_balance(account, quote_symbol)
    
    print(f"{account} {base_symbol} balance: {base_balance}")
    print(f"{account} {quote_symbol} balance: {quote_balance}")
    
    # Test different buy order parameters
    test_cases = [
        # Test 1: Small quantity, standard price
        {"quantity": "1.0000", "price": "0.00000001"},
        
        # Test 2: Larger quantity, standard price
        {"quantity": "10.0000", "price": "0.00000001"},
        
        # Test 3: Small quantity, higher price
        {"quantity": "1.0000", "price": "0.00000010"},
        
        # Test 4: Very small quantity, standard price
        {"quantity": "0.1000", "price": "0.00000001"},
        
        # Test 5: Standard quantity, very small price
        {"quantity": "1.0000", "price": "0.00000000"},
    ]
    
    results = []
    
    for i, test in enumerate(test_cases):
        print(f"\nTest {i+1}: Buy {test['quantity']} LIBRE @ {test['price']} BTC")
        
        success = place_buy_order(
            client=client,
            account=account,
            quantity=test["quantity"],
            price=test["price"],
            base_symbol=base_symbol,
            quote_symbol=quote_symbol,
            dex_contract=dex_contract
        )
        
        results.append({
            "test_number": i+1,
            "quantity": test["quantity"],
            "price": test["price"],
            "success": success
        })
        
        # Wait a moment between tests
        time.sleep(1)
    
    # Check final balances
    print("\nChecking final balances...")
    base_balance_after = client.get_currency_balance(account, base_symbol)
    quote_balance_after = client.get_currency_balance(account, quote_symbol)
    
    print(f"{account} {base_symbol} balance: {base_balance_after}")
    print(f"{account} {quote_symbol} balance: {quote_balance_after}")
    
    # Print summary
    print("\nBuy Order Test Summary:")
    for result in results:
        status = "✅ Success" if result["success"] else "❌ Failed"
        print(f"Test {result['test_number']}: Buy {result['quantity']} LIBRE @ {result['price']} BTC - {status}")
    
    print("\nBuy order testing completed!")

if __name__ == "__main__":
    main() 