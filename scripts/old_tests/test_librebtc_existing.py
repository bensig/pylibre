#!/usr/bin/env python3
"""
Test script for LIBRE/BTC trading pair using direct contract calls.
This script checks existing orders and tries to place new orders with different parameters.
"""

import sys
import os
import time
from decimal import Decimal

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pylibre.client import LibreClient

def check_orderbook(client, base_symbol, quote_symbol, dex_contract):
    """Check the orderbook for a specific trading pair."""
    print(f"\nChecking {base_symbol}/{quote_symbol} orderbook...")
    
    # The scope for the orderbook is typically the pair name in lowercase
    pair_scope = f"{base_symbol.lower()}{quote_symbol.lower()}"
    
    try:
        response = client.get_table_rows(
            code=dex_contract,
            table="orderbook2",
            scope=pair_scope,
            limit=20
        )
        
        if response.get("success"):
            rows = response.get("rows", [])
            print(f"Successfully queried orderbook table. Found {len(rows)} rows.")
            
            # Group orders by type
            sell_orders = [row for row in rows if row.get("type") == "sell"]
            buy_orders = [row for row in rows if row.get("type") == "buy"]
            
            print(f"Found {len(sell_orders)} sell orders and {len(buy_orders)} buy orders.")
            
            # Print a few orders
            if sell_orders:
                print("\nSample sell orders:")
                for order in sell_orders[:3]:
                    print(f"  ID: {order.get('identifier')}, Account: {order.get('account')}, "
                          f"Amount: {order.get('baseAsset')}, Price: {order.get('price')}")
            
            if buy_orders:
                print("\nSample buy orders:")
                for order in buy_orders[:3]:
                    print(f"  ID: {order.get('identifier')}, Account: {order.get('account')}, "
                          f"Amount: {order.get('baseAsset')}, Price: {order.get('price')}")
            
            return rows
        else:
            print(f"Failed to query orderbook table: {response.get('error')}")
            return []
    except Exception as e:
        print(f"Error querying orderbook table: {str(e)}")
        return []

def place_sell_order(client, account, quantity, price, base_symbol, quote_symbol, dex_contract):
    """Place a sell order for a specific trading pair."""
    print(f"\nPlacing sell order: {quantity} {base_symbol} @ {price} {quote_symbol}")
    
    # Determine the contract for the base symbol
    base_contract = "eosio.token" if base_symbol == "LIBRE" else f"{base_symbol.lower()}.libre"
    
    # Create the memo with the correct format
    memo = f"sell:{quantity} {base_symbol}:{price} {quote_symbol}"
    
    print(f"Transfer Details:")
    print(f"From: {account}")
    print(f"To: {dex_contract}")
    print(f"Amount: {quantity} {base_symbol}")
    print(f"Contract: {base_contract}")
    print(f"Memo: {memo}")
    
    try:
        result = client.transfer(
            from_account=account,
            to_account=dex_contract,
            quantity=f"{quantity} {base_symbol}",
            memo=memo,
            contract=base_contract
        )
        
        if result.get("success"):
            print("✅ Sell order placed successfully")
            print(f"Transaction ID: {result.get('data', {}).get('transaction_id')}")
            return True
        else:
            print(f"❌ Failed to place sell order: {result.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Error placing sell order: {str(e)}")
        return False

def place_buy_order(client, account, quantity, price, base_symbol, quote_symbol, dex_contract):
    """Place a buy order for a specific trading pair."""
    print(f"\nPlacing buy order: {quantity} {base_symbol} @ {price} {quote_symbol}")
    
    # Calculate the amount of quote currency to send
    quote_amount = Decimal(quantity) * Decimal(price)
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
    print(f"Testing LIBRE/BTC Trading Pair with {account}")
    print(f"{'='*50}")
    
    # Check initial balances
    print("\nChecking initial balances...")
    libre_balance = client.get_currency_balance(account, base_symbol)
    btc_balance = client.get_currency_balance(account, quote_symbol)
    
    print(f"{account} {base_symbol} balance: {libre_balance} {base_symbol}")
    print(f"{account} {quote_symbol} balance: {btc_balance} {quote_symbol}")
    
    # Check existing orderbook
    existing_orders = check_orderbook(client, base_symbol, quote_symbol, dex_contract)
    
    # Try to place a sell order with a different price
    sell_quantity = "5.0000"  # LIBRE
    sell_price = "0.00000002"  # BTC per LIBRE (higher than existing orders)
    
    sell_success = place_sell_order(
        client=client,
        account=account,
        quantity=sell_quantity,
        price=sell_price,
        base_symbol=base_symbol,
        quote_symbol=quote_symbol,
        dex_contract=dex_contract
    )
    
    # Wait a moment
    time.sleep(2)
    
    # Try to place a buy order with a different price
    buy_quantity = "5.0000"  # LIBRE
    buy_price = "0.00000001"  # BTC per LIBRE (same as existing orders)
    
    buy_success = place_buy_order(
        client=client,
        account=account,
        quantity=buy_quantity,
        price=buy_price,
        base_symbol=base_symbol,
        quote_symbol=quote_symbol,
        dex_contract=dex_contract
    )
    
    # Wait a moment
    time.sleep(2)
    
    # Check orderbook again to see if our orders were added
    print("\nChecking orderbook after placing orders...")
    updated_orders = check_orderbook(client, base_symbol, quote_symbol, dex_contract)
    
    # Check if the number of orders increased
    new_orders_count = len(updated_orders) - len(existing_orders)
    print(f"\nNumber of new orders added: {new_orders_count}")
    
    # Check final balances
    print("\nChecking final balances...")
    libre_balance_after = client.get_currency_balance(account, base_symbol)
    btc_balance_after = client.get_currency_balance(account, quote_symbol)
    
    print(f"{account} {base_symbol} balance: {libre_balance_after} {base_symbol}")
    print(f"{account} {quote_symbol} balance: {btc_balance_after} {quote_symbol}")
    
    # Print summary
    print("\nLIBRE/BTC trading test summary:")
    print(f"Sell order (5 LIBRE @ 0.00000002 BTC): {'Success' if sell_success else 'Failed'}")
    print(f"Buy order (5 LIBRE @ 0.00000001 BTC): {'Success' if buy_success else 'Failed'}")
    print(f"LIBRE balance change: {Decimal(libre_balance) - Decimal(libre_balance_after)} LIBRE")
    print(f"BTC balance change: {Decimal(btc_balance) - Decimal(btc_balance_after)} BTC")
    
    print("\nLIBRE/BTC trading test completed!")

if __name__ == "__main__":
    main() 