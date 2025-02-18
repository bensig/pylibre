#!/usr/bin/env python3
"""
Script to check if the LIBRE/BTC orderbook exists and if there are any orders.
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
    # Initialize client
    print("Initializing LibreClient...")
    client = LibreClient(network='testnet', verbose=True)
    
    # Initialize DexClient
    print("Initializing DexClient...")
    dex = DexClient(client)
    
    # Check LIBRE/BTC orderbook
    print("\nChecking LIBRE/BTC orderbook...")
    try:
        orderbook = dex.fetch_order_book(quote_symbol="BTC", base_symbol="LIBRE")
        
        if orderbook:
            print(f"Orderbook fetched successfully")
            print(f"Number of bids: {len(orderbook['bids'])}")
            print(f"Number of offers: {len(orderbook['offers'])}")
            
            # Print a few offers if available
            if orderbook['offers']:
                print("\nSample offers:")
                for offer in orderbook['offers'][:5]:
                    print(f"  {offer['account']} selling {offer['quantity']} LIBRE at {offer['price']} BTC")
            else:
                print("No offers found in the orderbook")
            
            # Print a few bids if available
            if orderbook['bids']:
                print("\nSample bids:")
                for bid in orderbook['bids'][:5]:
                    print(f"  {bid['account']} buying {bid['quantity']} LIBRE at {bid['price']} BTC")
            else:
                print("No bids found in the orderbook")
        else:
            print(f"Failed to fetch LIBRE/BTC orderbook")
    except Exception as e:
        print(f"Error checking orderbook: {str(e)}")
    
    # Check BTC/USDT orderbook for comparison
    print("\nChecking BTC/USDT orderbook for comparison...")
    try:
        orderbook = dex.fetch_order_book(quote_symbol="USDT", base_symbol="BTC")
        
        if orderbook:
            print(f"Orderbook fetched successfully")
            print(f"Number of bids: {len(orderbook['bids'])}")
            print(f"Number of offers: {len(orderbook['offers'])}")
            
            # Print a few offers if available
            if orderbook['offers']:
                print("\nSample offers:")
                for offer in orderbook['offers'][:5]:
                    print(f"  {offer['account']} selling {offer['quantity']} BTC at {offer['price']} USDT")
            else:
                print("No offers found in the orderbook")
            
            # Print a few bids if available
            if orderbook['bids']:
                print("\nSample bids:")
                for bid in orderbook['bids'][:5]:
                    print(f"  {bid['account']} buying {bid['quantity']} BTC at {bid['price']} USDT")
            else:
                print("No bids found in the orderbook")
        else:
            print(f"Failed to fetch BTC/USDT orderbook")
    except Exception as e:
        print(f"Error checking orderbook: {str(e)}")
    
    print("\nOrderbook check completed!")

if __name__ == "__main__":
    main() 