#!/usr/bin/env python3
"""
Test script for DEX functionality with different trading pairs.
Tests orderbook fetching and order placement for BTC/USDT and LIBRE/BTC pairs.
"""

import sys
import os
import time
from decimal import Decimal

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pylibre.client import LibreClient
from pylibre.dex import DexClient

def test_trading_pair(dex, account, base_symbol, quote_symbol, buy_quantity, buy_price, sell_quantity, sell_price):
    """Test a specific trading pair by fetching orderbook and placing orders."""
    print(f"\n{'='*50}")
    print(f"Testing {base_symbol}/{quote_symbol} trading pair")
    print(f"{'='*50}")
    
    # Fetch orderbook
    print(f"\n1. Fetching {base_symbol}/{quote_symbol} orderbook")
    orderbook = dex.fetch_order_book(quote_symbol=quote_symbol, base_symbol=base_symbol)
    
    if orderbook:
        print(f"Orderbook fetched successfully")
        print(f"Number of bids: {len(orderbook['bids'])}")
        print(f"Number of offers: {len(orderbook['offers'])}")
        
        # Print a few offers if available
        if orderbook['offers']:
            print("\nSample offers:")
            for offer in orderbook['offers'][:3]:
                print(f"  {offer['account']} selling {offer['quantity']} {base_symbol} at {offer['price']} {quote_symbol}")
        
        # Print a few bids if available
        if orderbook['bids']:
            print("\nSample bids:")
            for bid in orderbook['bids'][:3]:
                print(f"  {bid['account']} buying {bid['quantity']} {base_symbol} at {bid['price']} {quote_symbol}")
    else:
        print(f"Failed to fetch {base_symbol}/{quote_symbol} orderbook")
    
    # Place a small buy order
    print(f"\n2. Placing buy order for {base_symbol}/{quote_symbol}")
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
        
        # Wait a moment for the blockchain to process
        print("Waiting for blockchain to process transaction...")
        time.sleep(2)
    else:
        print(f"Failed to place buy order for {base_symbol}/{quote_symbol}")
    
    # Place a small sell order
    print(f"\n3. Placing sell order for {base_symbol}/{quote_symbol}")
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
        
        # Wait a moment for the blockchain to process
        print("Waiting for blockchain to process transaction...")
        time.sleep(2)
    else:
        print(f"Failed to place sell order for {base_symbol}/{quote_symbol}")
    
    # Fetch the orderbook again to see our orders
    print(f"\n4. Fetching updated {base_symbol}/{quote_symbol} orderbook")
    updated_orderbook = dex.fetch_order_book(quote_symbol=quote_symbol, base_symbol=base_symbol)
    
    if updated_orderbook:
        print(f"Updated orderbook fetched successfully")
        print(f"Number of bids: {len(updated_orderbook['bids'])}")
        print(f"Number of offers: {len(updated_orderbook['offers'])}")
        
        # Try to find our orders
        our_bids = [bid for bid in updated_orderbook['bids'] if bid['account'] == account]
        our_offers = [offer for offer in updated_orderbook['offers'] if offer['account'] == account]
        
        if our_bids:
            print(f"Found {len(our_bids)} buy orders from {account}")
            for order in our_bids[:3]:  # Show at most 3
                print(f"  Order ID: {order['identifier']}, buying {order['quantity']} {base_symbol} at {order['price']} {quote_symbol}")
        else:
            print(f"No buy orders found for {account}")
            
        if our_offers:
            print(f"Found {len(our_offers)} sell orders from {account}")
            for order in our_offers[:3]:  # Show at most 3
                print(f"  Order ID: {order['identifier']}, selling {order['quantity']} {base_symbol} at {order['price']} {quote_symbol}")
        else:
            print(f"No sell orders found for {account}")
    else:
        print(f"Failed to fetch updated {base_symbol}/{quote_symbol} orderbook")

def main():
    # Initialize client with verbose output
    print("Initializing LibreClient...")
    client = LibreClient(network='testnet', verbose=True)
    
    # Initialize DexClient
    print("Initializing DexClient...")
    dex = DexClient(client)
    
    # Define account to test
    account = "bentester"
    
    # Test BTC/USDT trading pair
    test_trading_pair(
        dex=dex,
        account=account,
        base_symbol="BTC",
        quote_symbol="USDT",
        buy_quantity="0.00001000",  # Small BTC amount
        buy_price="30000.00000000",  # Price in USDT per BTC
        sell_quantity="0.00001000",  # Small BTC amount
        sell_price="35000.00000000"  # Price in USDT per BTC
    )
    
    # Test LIBRE/BTC trading pair
    test_trading_pair(
        dex=dex,
        account=account,
        base_symbol="LIBRE",
        quote_symbol="BTC",
        buy_quantity="10.0000",      # LIBRE amount
        buy_price="0.00000001",      # Price in BTC per LIBRE (1 satoshi)
        sell_quantity="10.0000",     # LIBRE amount
        sell_price="0.00000002"      # Price in BTC per LIBRE (2 satoshis)
    )
    
    print("\nTrading pairs testing completed!")

if __name__ == "__main__":
    main() 