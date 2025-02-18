#!/usr/bin/env python3
"""
Test script for DexClient functionality.
Tests placing orders and fetching the orderbook.
"""

import sys
import os
import time
from decimal import Decimal

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pylibre.client import LibreClient
from pylibre.dex import DexClient

def main():
    # Initialize client with verbose output
    print("Initializing LibreClient...")
    client = LibreClient(network='testnet', verbose=True)
    
    # Initialize DexClient
    print("Initializing DexClient...")
    dex = DexClient(client)
    
    # Define account to test
    account = "bentester"
    
    # Test 1: Fetch orderbook
    print("\n1. Testing fetch_order_book")
    orderbook = dex.fetch_order_book(quote_symbol="BTC", base_symbol="LIBRE")
    
    if orderbook:
        print(f"Orderbook fetched successfully")
        print(f"Number of bids: {len(orderbook['bids'])}")
        print(f"Number of offers: {len(orderbook['offers'])}")
        
        # Print a few offers if available
        if orderbook['offers']:
            print("\nSample offers:")
            for offer in orderbook['offers'][:3]:
                print(f"  {offer['account']} selling {offer['quantity']} LIBRE at {offer['price']} BTC")
        
        # Print a few bids if available
        if orderbook['bids']:
            print("\nSample bids:")
            for bid in orderbook['bids'][:3]:
                print(f"  {bid['account']} buying {bid['quantity']} LIBRE at {bid['price']} BTC")
    else:
        print("Failed to fetch orderbook")
    
    # Test 2: Place a small buy order
    print("\n2. Testing place_order (buy)")
    
    # Calculate a price slightly below the lowest offer
    price = "0.00000001"  # 1 satoshi per LIBRE
    quantity = "10.0000"  # 10 LIBRE
    
    # Place the order
    tx_id = dex.place_order(
        account=account,
        order_type="buy",
        quantity=quantity,
        price=price,
        quote_symbol="BTC",
        base_symbol="LIBRE"
    )
    
    if tx_id:
        print(f"Buy order placed successfully. Transaction ID: {tx_id}")
        
        # Wait a moment for the blockchain to process
        print("Waiting for blockchain to process transaction...")
        time.sleep(2)
        
        # Fetch the orderbook again to see our order
        print("\nFetching updated orderbook...")
        updated_orderbook = dex.fetch_order_book(quote_symbol="BTC", base_symbol="LIBRE")
        
        if updated_orderbook:
            print(f"Updated orderbook fetched successfully")
            print(f"Number of bids: {len(updated_orderbook['bids'])}")
            
            # Try to find our order
            our_orders = [bid for bid in updated_orderbook['bids'] if bid['account'] == account]
            if our_orders:
                print(f"Found {len(our_orders)} orders from {account}")
                for order in our_orders:
                    print(f"  Order ID: {order['identifier']}, buying {order['quantity']} LIBRE at {order['price']} BTC")
            else:
                print(f"No orders found for {account}")
    else:
        print("Failed to place buy order")
    
    print("\nDEX testing completed!")

if __name__ == "__main__":
    main() 