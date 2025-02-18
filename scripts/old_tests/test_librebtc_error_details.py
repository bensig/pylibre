#!/usr/bin/env python3
"""
Test script to capture and display the exact error message from the blockchain
when placing LIBRE/BTC buy orders.
"""

import sys
import os
import time
import json
from decimal import Decimal

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pylibre.client import LibreClient

def place_buy_order_with_details(client, account, quantity, price, base_symbol, quote_symbol, dex_contract):
    """Place a buy order and capture detailed error information."""
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
        # Set verbose to True to get detailed API responses
        client.verbose = True
        
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
            return True, None
        else:
            error = result.get("error", "Unknown error")
            print(f"❌ Failed to place buy order: {error}")
            
            # Try to extract detailed error information
            if isinstance(error, dict):
                print("\nDetailed Error Information:")
                print(json.dumps(error, indent=2))
            elif isinstance(error, str) and "error" in error.lower():
                try:
                    # Try to parse the error string as JSON
                    error_json = json.loads(error)
                    print("\nDetailed Error Information:")
                    print(json.dumps(error_json, indent=2))
                except json.JSONDecodeError:
                    print("\nRaw Error Message:")
                    print(error)
            
            return False, error
    except Exception as e:
        print(f"❌ Error placing buy order: {str(e)}")
        return False, str(e)

def main():
    # Initialize client with verbose output
    print("Initializing LibreClient...")
    client = LibreClient(network='testnet', verbose=True)
    
    # Define account to test
    account = "bentest3"
    
    # Define trading pair parameters
    base_symbol = "LIBRE"
    quote_symbol = "BTC"
    dex_contract = "dex.libre"
    
    print(f"\n{'='*50}")
    print(f"Testing LIBRE/BTC Buy Order with Detailed Error Capture")
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
    
    # Test a buy order with minimum BTC value
    quantity = "1000.0000"  # LIBRE
    price = "0.00000010"    # BTC per LIBRE (0.00010000 BTC total)
    
    print(f"\nTesting buy order: {quantity} {base_symbol} @ {price} {quote_symbol}")
    print(f"Total value: {Decimal(quantity) * Decimal(price):.8f} {quote_symbol}")
    
    success, error = place_buy_order_with_details(
        client=client,
        account=account,
        quantity=quantity,
        price=price,
        base_symbol=base_symbol,
        quote_symbol=quote_symbol,
        dex_contract=dex_contract
    )
    
    # Check final balances
    print("\nChecking final balances...")
    base_balance_after = client.get_currency_balance(account, base_symbol)
    quote_balance_after = client.get_currency_balance(account, quote_symbol)
    
    print(f"{account} {base_symbol} balance: {base_balance_after}")
    print(f"{account} {quote_symbol} balance: {quote_balance_after}")
    
    # Print summary
    print("\nBuy Order Test Summary:")
    status = "✅ Success" if success else "❌ Failed"
    print(f"Buy order ({quantity} {base_symbol} @ {price} {quote_symbol}): {status}")
    
    if not success and error:
        print("\nError Details:")
        if isinstance(error, dict):
            print(json.dumps(error, indent=2))
        else:
            print(error)
    
    print("\nTesting completed!")

if __name__ == "__main__":
    main() 