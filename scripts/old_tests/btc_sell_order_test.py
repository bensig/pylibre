#!/usr/bin/env python3
"""
Comprehensive test script for BTC sell orders.
This script combines approaches from existing tests and focuses on verifying
that our fixes for BTC sell orders are working correctly.
"""

import sys
import os
import time
from decimal import Decimal, getcontext
import logging
import json

# Set higher precision for decimal calculations
getcontext().prec = 28

# Add the parent directory to the path so we can import the pylibre module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.pylibre.client import LibreClient
from src.pylibre.dex import DexClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BTCSellOrderTest")

def place_order_direct(client, account, order_type, quantity, price, base_symbol, quote_symbol):
    """Place an order directly using the transfer method with the correct memo format.
    This is based on the approach in test_librebtc_fixed.py.
    """
    # Define precision for base and quote symbols
    base_precision = 4 if base_symbol == 'LIBRE' else 8
    quote_precision = 8  # USDT and BTC use 8 decimal places
    
    # Parse quantity to get amount only (without symbol)
    quantity_amount = Decimal(quantity)
    
    # Format with correct precision
    if order_type == 'buy':
        # For buy orders, we send quote currency (e.g., BTC or USDT)
        send_amount = quantity_amount * Decimal(price)
        send_symbol = quote_symbol
        send_precision = quote_precision
        contract = "btc.libre" if quote_symbol == "BTC" else "usdt.libre"
    else:  # sell
        # For sell orders, we send base currency (e.g., LIBRE or BTC)
        send_amount = quantity_amount
        send_symbol = base_symbol
        send_precision = base_precision
        contract = "btc.libre" if base_symbol == "BTC" else "eosio.token"
    
    # Format the send amount with correct precision
    send_quantity = f"{send_amount:.{send_precision}f} {send_symbol}"
    
    # Create the action memo with correct format
    # Format: "buy:100.0000 LIBRE:0.00000001 BTC" or "sell:0.00010000 BTC:80000.00000000 USDT"
    memo = f"{order_type}:{quantity_amount:.{base_precision}f} {base_symbol}:{Decimal(price):.{quote_precision}f} {quote_symbol}"
    
    print(f"Placing {order_type} order: {quantity} {base_symbol} @ {price} {quote_symbol}")
    print(f"Transfer details:")
    print(f"  From: {account}")
    print(f"  To: dex.libre")
    print(f"  Amount: {send_quantity}")
    print(f"  Memo: {memo}")
    print(f"  Contract: {contract}")
    
    # Execute the transfer to place the order
    result = client.transfer(
        from_account=account,
        to_account="dex.libre",
        quantity=send_quantity,
        memo=memo,
        contract=contract
    )
    
    return result

def test_btc_sell_direct_transfer(client, account):
    """Test BTC sell orders using direct transfer approach.
    This is based on the approach in test_librebtc_direct.py.
    """
    print("\n" + "=" * 80)
    print("TESTING BTC SELL ORDERS USING DIRECT TRANSFER")
    print("=" * 80)
    
    base_symbol = "BTC"
    quote_symbol = "USDT"
    dex_contract = "dex.libre"
    btc_contract = "btc.libre"
    
    # Check initial balance
    print("\nChecking initial BTC balance...")
    btc_balance = client.get_currency_balance(account, base_symbol)
    print(f"{account} {base_symbol} balance: {btc_balance}")
    
    # Test 1: Selling BTC for USDT using direct transfer
    print("\nTest 1: Selling 0.00010000 BTC at 80000.00000000 USDT using direct transfer")
    sell_quantity = "0.00010000"  # BTC
    sell_price = "80000.00000000"  # USDT per BTC
    
    # Create the memo with the correct format
    memo = f"sell:{sell_quantity} {base_symbol}:{sell_price} {quote_symbol}"
    
    print(f"Placing sell order:")
    print(f"  From: {account}")
    print(f"  To: {dex_contract}")
    print(f"  Amount: {sell_quantity} {base_symbol}")
    print(f"  Memo: {memo}")
    print(f"  Contract: {btc_contract}")
    
    # Execute the transfer to place the order
    result = client.transfer(
        from_account=account,
        to_account=dex_contract,
        quantity=f"{sell_quantity} {base_symbol}",
        memo=memo,
        contract=btc_contract
    )
    
    print(f"Direct transfer result: {json.dumps(result, indent=2)}")
    
    # Check if the transaction was successful
    if result.get("success"):
        print(f"✅ BTC sell order placed successfully via direct transfer")
        print(f"Transaction ID: {result.get('data', {}).get('transaction_id')}")
    else:
        print(f"❌ BTC sell order failed via direct transfer: {result.get('error')}")
    
    return result

def test_btc_sell_dex_client(client, account):
    """Test BTC sell orders using the DexClient."""
    print("\n" + "=" * 80)
    print("TESTING BTC SELL ORDERS USING DEXCLIENT")
    print("=" * 80)
    
    dex = DexClient(client)
    
    # Test placing a BTC sell order via DexClient
    print("\nPlacing a BTC sell order via DexClient...")
    sell_result = dex.place_order(
        account=account,
        order_type="sell",
        quantity="0.00010000",
        price="80000.00000000",
        quote_symbol="USDT",
        base_symbol="BTC"
    )
    
    if sell_result:
        print(f"✅ BTC sell order placed successfully via DexClient")
        print(f"Transaction ID: {sell_result}")
    else:
        print(f"❌ BTC sell order failed via DexClient")
    
    return sell_result, dex

def test_btc_sell_fixed_approach(client, account):
    """Test BTC sell orders using the fixed approach from test_librebtc_fixed.py."""
    print("\n" + "=" * 80)
    print("TESTING BTC SELL ORDERS USING FIXED APPROACH")
    print("=" * 80)
    
    base_symbol = "BTC"
    quote_symbol = "USDT"
    
    # Test: Sell 0.00010000 BTC at 80000.00000000 USDT
    print("\nSelling 0.00010000 BTC at 80000.00000000 USDT")
    sell_quantity = "0.00010000"  # BTC
    sell_price = "80000.00000000"  # USDT per BTC
    
    sell_result = place_order_direct(
        client=client,
        account=account,
        order_type="sell",
        quantity=sell_quantity,
        price=sell_price,
        base_symbol=base_symbol,
        quote_symbol=quote_symbol
    )
    
    print(f"Fixed approach result: {json.dumps(sell_result, indent=2)}")
    
    # Check if the transaction was successful
    if sell_result.get("success"):
        print(f"✅ BTC sell order placed successfully via fixed approach")
        print(f"Transaction ID: {sell_result.get('data', {}).get('transaction_id')}")
    else:
        print(f"❌ BTC sell order failed via fixed approach: {sell_result.get('error')}")
    
    return sell_result

def test_btc_buy_for_comparison(client, account, dex):
    """Test BTC buy order for comparison with sell orders."""
    print("\n" + "=" * 80)
    print("TESTING BTC BUY ORDER FOR COMPARISON")
    print("=" * 80)
    
    # Test placing a BTC buy order via DexClient
    print("\nPlacing a BTC buy order via DexClient...")
    buy_result = dex.place_order(
        account=account,
        order_type="buy",
        quantity="0.00010000",
        price="75000.00000000",
        quote_symbol="USDT",
        base_symbol="BTC"
    )
    
    if buy_result:
        print(f"✅ BTC buy order placed successfully via DexClient")
        print(f"Transaction ID: {buy_result}")
    else:
        print(f"❌ BTC buy order failed via DexClient")
    
    return buy_result

def verify_orders_in_orderbook(client, account):
    """Verify that orders are present in the orderbook."""
    print("\n" + "=" * 80)
    print("VERIFYING ORDERS IN ORDERBOOK")
    print("=" * 80)
    
    dex_contract = "dex.libre"
    base_symbol = "BTC"
    quote_symbol = "USDT"
    
    # Try to directly query the orderbook table
    print("\nAttempting to directly query the orderbook table...")
    try:
        # The scope for the orderbook is typically the pair name in lowercase
        pair_scope = f"{base_symbol.lower()}{quote_symbol.lower()}"
        
        response = client.get_table_rows(
            code=dex_contract,
            table="orderbook2",
            scope=pair_scope,
            limit=20
        )
        
        if response.get("success"):
            rows = response.get("rows", [])
            print(f"Successfully queried orderbook table. Found {len(rows)} rows.")
            
            # Look for orders from our account
            account_orders = [row for row in rows if row.get("account") == account]
            print(f"Found {len(account_orders)} orders from account {account}:")
            
            for order in account_orders:
                print(f"  Order: {order}")
                
            return account_orders
        else:
            print(f"Failed to query orderbook table: {response.get('error')}")
            return []
    except Exception as e:
        print(f"Error querying orderbook table: {str(e)}")
        return []

def main():
    """Run the BTC sell order test."""
    print("\n" + "=" * 80)
    print("BTC SELL ORDER COMPREHENSIVE TEST")
    print("=" * 80 + "\n")
    
    try:
        # Initialize client
        print("Initializing LibreClient...")
        client = LibreClient(verbose=True)
        
        # Define account to test
        account = "bentester"
        
        # Test BTC sell order using direct transfer
        direct_result = test_btc_sell_direct_transfer(client, account)
        
        # Wait a bit between tests
        time.sleep(2)
        
        # Test BTC sell order using DexClient
        dex_result, dex = test_btc_sell_dex_client(client, account)
        
        # Wait a bit between tests
        time.sleep(2)
        
        # Test BTC sell order using fixed approach
        fixed_result = test_btc_sell_fixed_approach(client, account)
        
        # Wait a bit between tests
        time.sleep(2)
        
        # Test BTC buy order for comparison
        buy_result = test_btc_buy_for_comparison(client, account, dex)
        
        # Wait a bit for orders to be processed
        time.sleep(5)
        
        # Verify orders in orderbook
        account_orders = verify_orders_in_orderbook(client, account)
        
        # Summarize results
        print("\n" + "=" * 80)
        print("TEST RESULTS SUMMARY")
        print("=" * 80)
        
        print(f"\nDirect Transfer: {'✅ Success' if direct_result.get('success', False) else '❌ Failed'}")
        print(f"DexClient: {'✅ Success' if dex_result else '❌ Failed'}")
        print(f"Fixed Approach: {'✅ Success' if fixed_result.get('success', False) else '❌ Failed'}")
        print(f"Buy Order: {'✅ Success' if buy_result else '❌ Failed'}")
        print(f"Orders in Orderbook: {'✅ Found ' + str(len(account_orders)) if account_orders else '❌ None found'}")
        
        print("\n" + "=" * 80)
        print("COMPREHENSIVE TEST COMPLETED")
        print("=" * 80 + "\n")
        
        return 0
    except Exception as e:
        logger.error(f"Error in comprehensive test: {str(e)}", exc_info=True)
        print(f"\n❌ COMPREHENSIVE TEST FAILED: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
