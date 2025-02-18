#!/usr/bin/env python3
"""
Test script for OrderBookFillerStrategy with fixed quantity calculations.
Fills the orderbook with 15 buy and 15 sell orders at intervals from the market price.
"""

import sys
import os
import time
from decimal import Decimal
import logging
import json
import random

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pylibre.client import LibreClient
from pylibre.dex import DexClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("OrderBookTest")

def place_orders(dex, account, base_symbol, quote_symbol, num_orders=15):
    """Place buy and sell orders at intervals from the market price."""
    print(f"\n{'='*50}")
    print(f"Testing order placement for {base_symbol}/{quote_symbol}")
    print(f"{'='*50}")
    
    # Check initial orderbook
    print(f"\nChecking initial orderbook for {base_symbol}/{quote_symbol}...")
    orderbook = dex.fetch_order_book(quote_symbol=quote_symbol, base_symbol=base_symbol)
    
    if orderbook:
        print(f"Initial orderbook has {len(orderbook['bids'])} bids and {len(orderbook['offers'])} offers")
        
        # Count our orders
        our_bids = [bid for bid in orderbook['bids'] if bid['account'] == account]
        our_offers = [offer for offer in orderbook['offers'] if offer['account'] == account]
        
        print(f"We have {len(our_bids)} buy orders and {len(our_offers)} sell orders")
    
    # Define market price
    if base_symbol == "BTC" and quote_symbol == "USDT":
        market_price = Decimal("30000.00000000")  # Fixed price for BTC/USDT
    elif base_symbol == "LIBRE" and quote_symbol == "BTC":
        market_price = Decimal("0.00000001")  # Fixed price for LIBRE/BTC (1 satoshi)
    else:
        market_price = Decimal("1.00000000")  # Default
    
    print(f"Using market price for {base_symbol}/{quote_symbol}: {market_price}")
    
    # Define spread percentages
    min_spread = Decimal("0.06")  # 6%
    max_spread = Decimal("0.20")  # 20%
    
    # Calculate price ranges
    min_price = market_price * (Decimal('1') - min_spread)
    max_price = market_price * (Decimal('1') + max_spread)
    
    print(f"Price range: {min_price} to {max_price}")
    
    # Define order quantities based on trading pair
    if base_symbol == "BTC" and quote_symbol == "USDT":
        buy_quantities = [Decimal("0.00010000") for _ in range(num_orders)]
        sell_quantities = [Decimal("0.00010000") for _ in range(num_orders)]
    elif base_symbol == "LIBRE" and quote_symbol == "BTC":
        buy_quantities = [Decimal("10.0000") for _ in range(num_orders)]
        sell_quantities = [Decimal("10.0000") for _ in range(num_orders)]
    else:
        buy_quantities = [Decimal("1.00000000") for _ in range(num_orders)]
        sell_quantities = [Decimal("1.00000000") for _ in range(num_orders)]
    
    # Calculate price steps
    buy_price_step = (market_price - min_price) / (num_orders - 1) if num_orders > 1 else Decimal("0")
    sell_price_step = (max_price - market_price) / (num_orders - 1) if num_orders > 1 else Decimal("0")
    
    # Place buy orders
    print(f"\nPlacing {num_orders} buy orders...")
    buy_tx_ids = []
    
    for i in range(num_orders):
        # Calculate price for this order
        price = min_price + (buy_price_step * i)
        
        # Format price with correct precision
        if quote_symbol == "USDT":
            price_str = f"{price:.8f}"
        else:  # BTC
            price_str = f"{price:.8f}"
        
        # Format quantity with correct precision
        if base_symbol == "LIBRE":
            quantity_str = f"{buy_quantities[i]:.4f}"
        else:  # BTC
            quantity_str = f"{buy_quantities[i]:.8f}"
        
        print(f"Placing buy order {i+1}/{num_orders}: {quantity_str} {base_symbol} @ {price_str} {quote_symbol}")
        
        # Place the order
        tx_id = dex.place_order(
            account=account,
            order_type="buy",
            quantity=quantity_str,
            price=price_str,
            quote_symbol=quote_symbol,
            base_symbol=base_symbol
        )
        
        if tx_id:
            print(f"Buy order {i+1} placed successfully. Transaction ID: {tx_id}")
            buy_tx_ids.append(tx_id)
        else:
            print(f"Failed to place buy order {i+1}")
        
        # Small delay between orders
        time.sleep(0.5)
    
    # Place sell orders
    print(f"\nPlacing {num_orders} sell orders...")
    sell_tx_ids = []
    
    for i in range(num_orders):
        # Calculate price for this order
        price = market_price + (sell_price_step * i)
        
        # Format price with correct precision
        if quote_symbol == "USDT":
            price_str = f"{price:.8f}"
        else:  # BTC
            price_str = f"{price:.8f}"
        
        # Format quantity with correct precision
        if base_symbol == "LIBRE":
            quantity_str = f"{sell_quantities[i]:.4f}"
        else:  # BTC
            quantity_str = f"{sell_quantities[i]:.8f}"
        
        print(f"Placing sell order {i+1}/{num_orders}: {quantity_str} {base_symbol} @ {price_str} {quote_symbol}")
        
        # Place the order
        tx_id = dex.place_order(
            account=account,
            order_type="sell",
            quantity=quantity_str,
            price=price_str,
            quote_symbol=quote_symbol,
            base_symbol=base_symbol
        )
        
        if tx_id:
            print(f"Sell order {i+1} placed successfully. Transaction ID: {tx_id}")
            sell_tx_ids.append(tx_id)
        else:
            print(f"Failed to place sell order {i+1}")
        
        # Small delay between orders
        time.sleep(0.5)
    
    # Wait for orders to be processed
    print("\nWaiting for orders to be processed...")
    time.sleep(5)
    
    # Check final orderbook
    print(f"\nChecking final orderbook for {base_symbol}/{quote_symbol}...")
    final_orderbook = dex.fetch_order_book(quote_symbol=quote_symbol, base_symbol=base_symbol)
    
    if final_orderbook:
        print(f"Final orderbook has {len(final_orderbook['bids'])} bids and {len(final_orderbook['offers'])} offers")
        
        # Count our orders
        our_bids = [bid for bid in final_orderbook['bids'] if bid['account'] == account]
        our_offers = [offer for offer in final_orderbook['offers'] if offer['account'] == account]
        
        print(f"We now have {len(our_bids)} buy orders and {len(our_offers)} sell orders")
        
        # Print some of our orders
        if our_bids:
            print("\nSample of our buy orders:")
            for bid in our_bids[:5]:
                print(f"  Buy {bid['quantity']} {base_symbol} at {bid['price']} {quote_symbol}")
        
        if our_offers:
            print("\nSample of our sell orders:")
            for offer in our_offers[:5]:
                print(f"  Sell {offer['quantity']} {base_symbol} at {offer['price']} {quote_symbol}")
    else:
        print(f"Failed to fetch final orderbook for {base_symbol}/{quote_symbol}")
    
    # Summary
    print(f"\nOrder placement summary for {base_symbol}/{quote_symbol}:")
    print(f"Buy orders placed: {len(buy_tx_ids)}/{num_orders}")
    print(f"Sell orders placed: {len(sell_tx_ids)}/{num_orders}")
    
    print(f"\nOrder placement test for {base_symbol}/{quote_symbol} completed!")

def main():
    # Define account to test
    account = "bentester"
    
    # Initialize client
    print("Initializing LibreClient...")
    client = LibreClient(network='testnet', verbose=True)
    
    # Initialize DexClient
    print("Initializing DexClient...")
    dex = DexClient(client)
    
    # Test BTC/USDT trading pair
    place_orders(dex, account, "BTC", "USDT", num_orders=15)
    
    # Test LIBRE/BTC trading pair
    place_orders(dex, account, "LIBRE", "BTC", num_orders=15)
    
    print("\nOrderbook testing completed!")

if __name__ == "__main__":
    main() 