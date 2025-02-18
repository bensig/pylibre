#!/usr/bin/env python3
"""
Test script for OrderBookFillerStrategy.
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
from pylibre.strategies.orderbookfiller import OrderBookFillerStrategy
from pylibre.manager.config_manager import ConfigManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("OrderBookTest")

def create_strategy_parameters(base_symbol, quote_symbol, num_orders=30):
    """Create parameters for the OrderBookFillerStrategy."""
    return {
        'update_interval_ms': 500,
        'min_spread_percentage': 0.06,
        'max_spread_percentage': 0.20,
        'num_orders': num_orders,
        'quantity_distribution': 'random',
        'order_spacing': 'linear',
        'price_source_config': {
            'source': 'fixed',
            'price': '30000.00000000' if quote_symbol == 'USDT' else '0.00000001'
        }
    }

def test_orderbook_strategy(trading_pair, account, num_orders=30):
    """Test the OrderBookFillerStrategy for a specific trading pair."""
    base_symbol, quote_symbol = trading_pair.split('/')
    
    print(f"\n{'='*50}")
    print(f"Testing OrderBookFillerStrategy for {trading_pair}")
    print(f"{'='*50}")
    
    # Initialize client
    print("Initializing LibreClient...")
    client = LibreClient(network='testnet', verbose=True)
    
    # Initialize DexClient
    print("Initializing DexClient...")
    dex = DexClient(client)
    
    # Create strategy parameters
    parameters = create_strategy_parameters(base_symbol, quote_symbol, num_orders)
    
    # Initialize strategy
    print(f"Initializing OrderBookFillerStrategy for {trading_pair}...")
    strategy = OrderBookFillerStrategy(
        client=client,
        account=account,
        base_symbol=base_symbol,
        quote_symbol=quote_symbol,
        parameters=parameters,
        logger=logger
    )
    
    # Check initial orderbook
    print(f"\nChecking initial orderbook for {trading_pair}...")
    orderbook = dex.fetch_order_book(quote_symbol=quote_symbol, base_symbol=base_symbol)
    
    if orderbook:
        print(f"Initial orderbook has {len(orderbook['bids'])} bids and {len(orderbook['offers'])} offers")
        
        # Count our orders
        our_bids = [bid for bid in orderbook['bids'] if bid['account'] == account]
        our_offers = [offer for offer in orderbook['offers'] if offer['account'] == account]
        
        print(f"We have {len(our_bids)} buy orders and {len(our_offers)} sell orders")
    
    # Place orders using the strategy
    print(f"\nPlacing orders for {trading_pair}...")
    
    # Get market price
    market_price = strategy.get_market_price()
    print(f"Market price for {trading_pair}: {market_price}")
    
    # Calculate min and max prices
    min_price = market_price * (Decimal('1') - strategy.min_spread_percentage)
    max_price = market_price * (Decimal('1') + strategy.max_spread_percentage)
    
    print(f"Price range: {min_price} to {max_price}")
    
    # Place buy orders
    print(f"\nPlacing {num_orders//2} buy orders...")
    strategy.place_buy_orders(market_price, min_price, num_orders//2)
    
    # Place sell orders
    print(f"\nPlacing {num_orders//2} sell orders...")
    strategy.place_sell_orders(market_price, max_price, num_orders//2)
    
    # Wait for orders to be processed
    print("\nWaiting for orders to be processed...")
    time.sleep(5)
    
    # Check final orderbook
    print(f"\nChecking final orderbook for {trading_pair}...")
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
    
    print(f"\nOrderBookFillerStrategy test for {trading_pair} completed!")

def main():
    # Define account to test
    account = "bentester"
    
    # Test BTC/USDT trading pair
    test_orderbook_strategy("BTC/USDT", account, num_orders=30)
    
    # Test LIBRE/BTC trading pair
    test_orderbook_strategy("LIBRE/BTC", account, num_orders=30)
    
    print("\nOrderbook strategy testing completed!")

if __name__ == "__main__":
    main() 