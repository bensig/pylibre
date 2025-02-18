#!/usr/bin/env python3
"""
Test script for BTC/USDT trading pair only.
Places a small number of buy and sell orders at intervals from the market price.
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
logger = logging.getLogger("BTCUSDTTest")

def test_btcusdt_trading(dex, account, num_orders=5):
    """Test BTC/USDT trading with a small number of orders."""
    base_symbol = "BTC"
    quote_symbol = "USDT"
    
    print(f"\n{'='*50}")
    print(f"Testing BTC/USDT Trading")
    print(f"{'='*50}")
    
    # Check initial balances
    print("\nChecking initial balances...")
    client = dex.client
    btc_balance = client.get_currency_balance(account, "BTC")
    usdt_balance = client.get_currency_balance(account, "USDT")
    
    print(f"{account} BTC balance: {btc_balance}")
    print(f"{account} USDT balance: {usdt_balance}")
    
    # Check initial orderbook
    print("\nChecking initial orderbook...")
    orderbook = dex.fetch_order_book(quote_symbol=quote_symbol, base_symbol=base_symbol)
    
    if orderbook:
        print(f"Initial orderbook has {len(orderbook['bids'])} bids and {len(orderbook['offers'])} offers")
        
        # Count our orders
        our_bids = [bid for bid in orderbook['bids'] if bid['account'] == account]
        our_offers = [offer for offer in orderbook['offers'] if offer['account'] == account]
        
        print(f"We have {len(our_bids)} buy orders and {len(our_offers)} sell orders")
        
        # Print some of our orders
        if our_bids:
            print("\nSample of our existing buy orders:")
            for bid in our_bids[:3]:
                print(f"  Buy {bid['quantity']} BTC at {bid['price']} USDT")
        
        if our_offers:
            print("\nSample of our existing sell orders:")
            for offer in our_offers[:3]:
                print(f"  Sell {offer['quantity']} BTC at {offer['price']} USDT")
    
    # Define market price and ranges
    market_price = Decimal("30000.00000000")  # Fixed price for BTC/USDT
    min_spread = Decimal("0.05")  # 5%
    max_spread = Decimal("0.10")  # 10%
    
    min_price = market_price * (Decimal('1') - min_spread)
    max_price = market_price * (Decimal('1') + max_spread)
    
    print(f"\nUsing market price: {market_price} USDT")
    print(f"Price range: {min_price} to {max_price} USDT")
    
    # Define small quantities for orders
    quantity = Decimal("0.00005000")  # Very small BTC amount
    
    # Calculate price steps
    buy_price_step = (market_price - min_price) / (num_orders - 1) if num_orders > 1 else Decimal("0")
    sell_price_step = (max_price - market_price) / (num_orders - 1) if num_orders > 1 else Decimal("0")
    
    # Place buy orders
    print(f"\nPlacing {num_orders} buy orders...")
    buy_tx_ids = []
    
    for i in range(num_orders):
        # Calculate price for this order
        price = min_price + (buy_price_step * i)
        price_str = f"{price:.8f}"
        quantity_str = f"{quantity:.8f}"
        
        print(f"Placing buy order {i+1}/{num_orders}: {quantity_str} BTC @ {price_str} USDT")
        
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
        time.sleep(1)
    
    # Place sell orders
    print(f"\nPlacing {num_orders} sell orders...")
    sell_tx_ids = []
    
    for i in range(num_orders):
        # Calculate price for this order
        price = market_price + (sell_price_step * i)
        price_str = f"{price:.8f}"
        quantity_str = f"{quantity:.8f}"
        
        print(f"Placing sell order {i+1}/{num_orders}: {quantity_str} BTC @ {price_str} USDT")
        
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
        time.sleep(1)
    
    # Wait for orders to be processed
    print("\nWaiting for orders to be processed...")
    time.sleep(5)
    
    # Check final orderbook
    print("\nChecking final orderbook...")
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
                print(f"  Buy {bid['quantity']} BTC at {bid['price']} USDT")
        
        if our_offers:
            print("\nSample of our sell orders:")
            for offer in our_offers[:5]:
                print(f"  Sell {offer['quantity']} BTC at {offer['price']} USDT")
    
    # Check final balances
    print("\nChecking final balances...")
    btc_balance_after = client.get_currency_balance(account, "BTC")
    usdt_balance_after = client.get_currency_balance(account, "USDT")
    
    print(f"{account} BTC balance: {btc_balance_after}")
    print(f"{account} USDT balance: {usdt_balance_after}")
    
    # Summary
    print(f"\nOrder placement summary:")
    print(f"Buy orders placed: {len(buy_tx_ids)}/{num_orders}")
    print(f"Sell orders placed: {len(sell_tx_ids)}/{num_orders}")
    
    print(f"\nBTC/USDT trading test completed!")

def main():
    # Define account to test
    account = "bentester"
    
    # Initialize client
    print("Initializing LibreClient...")
    client = LibreClient(network='testnet', verbose=True)
    
    # Initialize DexClient
    print("Initializing DexClient...")
    dex = DexClient(client)
    
    # Test BTC/USDT trading
    test_btcusdt_trading(dex, account, num_orders=5)
    
    print("\nTesting completed!")

if __name__ == "__main__":
    main() 