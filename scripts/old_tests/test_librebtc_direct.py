#!/usr/bin/env python3
"""
Test script for LIBRE/BTC trading pair using direct contract calls.
This script bypasses the DexClient and uses direct contract calls to test if the issue is with the client or the contract.
"""

import sys
import os
import time
from decimal import Decimal

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pylibre.client import LibreClient

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
    print(f"Testing LIBRE/BTC Trading Pair with {account} using direct contract calls")
    print(f"{'='*50}")
    
    # Check initial balances
    print("\nChecking initial balances...")
    libre_contract = "eosio.token"
    btc_contract = "btc.libre"
    
    print(f"Using contract: {libre_contract} for symbol: {base_symbol}")
    print(f"Using contract: {btc_contract} for symbol: {quote_symbol}")
    
    libre_balance = client.get_currency_balance(account, base_symbol)
    btc_balance = client.get_currency_balance(account, quote_symbol)
    
    print(f"{account} {base_symbol} balance: {libre_balance} {base_symbol}")
    print(f"{account} {quote_symbol} balance: {btc_balance} {quote_symbol}")
    
    # Try to directly query the orderbook table
    print("\nAttempting to directly query the orderbook table...")
    try:
        # The scope for the orderbook is typically the pair name in lowercase
        pair_scope = f"{base_symbol.lower()}{quote_symbol.lower()}"
        
        response = client.get_table_rows(
            code=dex_contract,
            table="orderbook2",
            scope=pair_scope,
            limit=10
        )
        
        if response.get("success"):
            rows = response.get("rows", [])
            print(f"Successfully queried orderbook table. Found {len(rows)} rows.")
            for row in rows[:3]:
                print(f"  Order: {row}")
        else:
            print(f"Failed to query orderbook table: {response.get('error')}")
            
            # Try alternative table names
            print("\nTrying alternative table names...")
            for table_name in ["orderbook", "orders", "dexorders"]:
                response = client.get_table_rows(
                    code=dex_contract,
                    table=table_name,
                    scope=pair_scope,
                    limit=10
                )
                
                if response.get("success"):
                    rows = response.get("rows", [])
                    print(f"Successfully queried {table_name} table. Found {len(rows)} rows.")
                    break
                else:
                    print(f"Failed to query {table_name} table: {response.get('error')}")
    except Exception as e:
        print(f"Error querying orderbook table: {str(e)}")
    
    # Test 1: Selling LIBRE for BTC using direct transfer
    print("\nTest 1: Selling 10 LIBRE at 0.0000000055 BTC using direct transfer")
    sell_quantity = "10.0000"  # LIBRE
    sell_price = "0.0000000055"  # BTC per LIBRE
    
    # Create the memo with the correct format
    memo = f"sell:{sell_quantity} {base_symbol}:{sell_price} {quote_symbol}"
    
    print(f"Placing sell order:")
    print(f"  From: {account}")
    print(f"  To: {dex_contract}")
    print(f"  Amount: {sell_quantity} {base_symbol}")
    print(f"  Memo: {memo}")
    
    print("\nTransfer Details:")
    print(f"From: {account}")
    print(f"To: {dex_contract}")
    print(f"Amount: {sell_quantity} {base_symbol}")
    print(f"Contract: {libre_contract}")
    print(f"Memo: {memo}")
    
    try:
        result = client.transfer(
            from_account=account,
            to_account=dex_contract,
            quantity=f"{sell_quantity} {base_symbol}",
            memo=memo,
            contract=libre_contract
        )
        
        if result.get("success"):
            print("✅ Sell order placed successfully")
            print(f"Transaction ID: {result.get('data', {}).get('transaction_id')}")
        else:
            print(f"❌ Failed to place sell order: {result.get('error')}")
    except Exception as e:
        print(f"❌ Error placing sell order: {str(e)}")
    
    # Wait a moment
    time.sleep(2)
    
    # Test 2: Buying LIBRE with BTC using direct transfer
    print("\nTest 2: Buying 10 LIBRE at 0.0000000055 BTC using direct transfer")
    buy_quantity = "10.0000"  # LIBRE
    buy_price = "0.0000000055"  # BTC per LIBRE
    
    # Calculate the amount of BTC to send
    buy_amount_btc = Decimal(buy_quantity) * Decimal(buy_price)
    buy_amount_btc_str = f"{buy_amount_btc:.8f}"
    
    # Create the memo with the correct format
    memo = f"buy:{buy_quantity} {base_symbol}:{buy_price} {quote_symbol}"
    
    print(f"Placing buy order:")
    print(f"  From: {account}")
    print(f"  To: {dex_contract}")
    print(f"  Amount: {buy_amount_btc_str} {quote_symbol}")
    print(f"  Memo: {memo}")
    
    print("\nTransfer Details:")
    print(f"From: {account}")
    print(f"To: {dex_contract}")
    print(f"Amount: {buy_amount_btc_str} {quote_symbol}")
    print(f"Contract: {btc_contract}")
    print(f"Memo: {memo}")
    
    try:
        result = client.transfer(
            from_account=account,
            to_account=dex_contract,
            quantity=f"{buy_amount_btc_str} {quote_symbol}",
            memo=memo,
            contract=btc_contract
        )
        
        if result.get("success"):
            print("✅ Buy order placed successfully")
            print(f"Transaction ID: {result.get('data', {}).get('transaction_id')}")
        else:
            print(f"❌ Failed to place buy order: {result.get('error')}")
    except Exception as e:
        print(f"❌ Error placing buy order: {str(e)}")
    
    # Check final balances
    print("\nChecking final balances...")
    libre_balance_after = client.get_currency_balance(account, base_symbol)
    btc_balance_after = client.get_currency_balance(account, quote_symbol)
    
    print(f"{account} {base_symbol} balance: {libre_balance_after} {base_symbol}")
    print(f"{account} {quote_symbol} balance: {btc_balance_after} {quote_symbol}")
    
    # Print summary
    print("\nLIBRE/BTC trading test summary:")
    print(f"Sell order (10 LIBRE @ 0.0000000055 BTC): {'Success' if libre_balance != libre_balance_after else 'Failed'}")
    print(f"Buy order (10 LIBRE @ 0.0000000055 BTC): {'Success' if btc_balance != btc_balance_after else 'Failed'}")
    
    print("\nLIBRE/BTC trading test completed!")

if __name__ == "__main__":
    main() 