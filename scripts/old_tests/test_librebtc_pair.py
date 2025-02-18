#!/usr/bin/env python3
"""
Test script for LIBRE/BTC trading pair.
Tests direct buy and sell orders with specific quantities and prices.
"""

import sys
import os
import time
from decimal import Decimal
import logging

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pylibre.client import LibreClient
from pylibre.dex import DexClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LibreBTCTest")

def test_librebtc_pair(dex, account):
    """Test LIBRE/BTC trading pair with specific orders."""
    base_symbol = "LIBRE"
    quote_symbol = "BTC"
    
    print(f"\n{'='*50}")
    print(f"Testing LIBRE/BTC Trading Pair")
    print(f"{'='*50}")
    
    # Check initial balances
    print("\nChecking initial balances...")
    client = dex.client
    libre_balance = client.get_currency_balance(account, "LIBRE")
    btc_balance = client.get_currency_balance(account, "BTC")
    
    print(f"{account} LIBRE balance: {libre_balance}")
    print(f"{account} BTC balance: {btc_balance}")
    
    # Try to fetch orderbook (may fail based on previous tests)
    print("\nAttempting to fetch orderbook...")
    try:
        orderbook = dex.fetch_order_book(quote_symbol=quote_symbol, base_symbol=base_symbol)
        if orderbook:
            print(f"Orderbook has {len(orderbook['bids'])} bids and {len(orderbook['offers'])} offers")
            
            # Count our orders
            our_bids = [bid for bid in orderbook['bids'] if bid['account'] == account]
            our_offers = [offer for offer in orderbook['offers'] if offer['account'] == account]
            
            print(f"We have {len(our_bids)} buy orders and {len(our_offers)} sell orders")
    except Exception as e:
        print(f"Error fetching orderbook: {str(e)}")
        print("Continuing with testing despite orderbook fetch error...")
    
    # Test 1: Sell 100 LIBRE at 0.00000001 BTC
    print("\nTest 1: Selling 100 LIBRE at 0.00000001 BTC")
    sell_quantity = "100.0000"  # LIBRE
    sell_price = "0.00000001"   # BTC per LIBRE
    
    print(f"Placing sell order: {sell_quantity} LIBRE @ {sell_price} BTC")
    sell_tx_id = dex.place_order(
        account=account,
        order_type="sell",
        quantity=sell_quantity,
        price=sell_price,
        quote_symbol=quote_symbol,
        base_symbol=base_symbol
    )
    
    if sell_tx_id:
        print(f"Sell order placed successfully. Transaction ID: {sell_tx_id}")
    else:
        print("Failed to place sell order")
    
    # Wait a moment
    time.sleep(2)
    
    # Test 2: Buy 1000 LIBRE at 0.00000001 BTC
    print("\nTest 2: Buying 1000 LIBRE at 0.00000001 BTC")
    buy_quantity = "1000.0000"  # LIBRE
    buy_price = "0.00000001"    # BTC per LIBRE
    
    print(f"Placing buy order: {buy_quantity} LIBRE @ {buy_price} BTC")
    buy_tx_id = dex.place_order(
        account=account,
        order_type="buy",
        quantity=buy_quantity,
        price=buy_price,
        quote_symbol=quote_symbol,
        base_symbol=base_symbol
    )
    
    if buy_tx_id:
        print(f"Buy order placed successfully. Transaction ID: {buy_tx_id}")
    else:
        print("Failed to place buy order")
    
    # Wait a moment
    time.sleep(2)
    
    # Check final balances
    print("\nChecking final balances...")
    libre_balance_after = client.get_currency_balance(account, "LIBRE")
    btc_balance_after = client.get_currency_balance(account, "BTC")
    
    print(f"{account} LIBRE balance: {libre_balance_after}")
    print(f"{account} BTC balance: {btc_balance_after}")
    
    # Try to fetch orderbook again
    print("\nAttempting to fetch final orderbook...")
    try:
        final_orderbook = dex.fetch_order_book(quote_symbol=quote_symbol, base_symbol=base_symbol)
        if final_orderbook:
            print(f"Final orderbook has {len(final_orderbook['bids'])} bids and {len(final_orderbook['offers'])} offers")
            
            # Count our orders
            our_bids = [bid for bid in final_orderbook['bids'] if bid['account'] == account]
            our_offers = [offer for offer in final_orderbook['offers'] if offer['account'] == account]
            
            print(f"We now have {len(our_bids)} buy orders and {len(our_offers)} sell orders")
    except Exception as e:
        print(f"Error fetching final orderbook: {str(e)}")
    
    # Summary
    print("\nLIBRE/BTC trading test summary:")
    print(f"Sell order (100 LIBRE @ 0.00000001 BTC): {'Success' if sell_tx_id else 'Failed'}")
    print(f"Buy order (1000 LIBRE @ 0.00000001 BTC): {'Success' if buy_tx_id else 'Failed'}")
    
    print("\nLIBRE/BTC trading test completed!")

def main():
    # Define account to test
    account = "bentester"
    
    # Initialize client
    print("Initializing LibreClient...")
    client = LibreClient(network='testnet', verbose=True)
    
    # Initialize DexClient
    print("Initializing DexClient...")
    dex = DexClient(client)
    
    # Test LIBRE/BTC trading pair
    test_librebtc_pair(dex, account)
    
    print("\nTesting completed!")

if __name__ == "__main__":
    main() 