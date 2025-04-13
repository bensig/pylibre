#!/usr/bin/env python3
"""
Script to preview what orders would be created by the OrderBookMakerStrategy
without actually placing them on the blockchain.
"""

import sys
import os
import argparse
import yaml
import decimal
from decimal import Decimal
import random

# Add the parent directory to the path so we can import the pylibre module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.pylibre.strategies.orderbookmaker import OrderBookMakerStrategy
from src.pylibre.strategies.marketpricetracker import MarketPriceTrackerStrategy

class MockClient:
    """Mock client for simulating API calls without actual blockchain interaction."""
    
    def __init__(self):
        self.orders = []
    
    def place_order(self, account, base_symbol, quote_symbol, price, quantity, order_type):
        """Mock method to simulate placing an order."""
        order = {
            'account': account,
            'base_symbol': base_symbol,
            'quote_symbol': quote_symbol,
            'price': float(price),
            'quantity': float(quantity),
            'order_type': order_type
        }
        self.orders.append(order)
        return {'order_id': f'mock_order_{len(self.orders)}'}
    
    def get_orders(self):
        """Return all mock orders that would be placed."""
        return self.orders

def load_config(config_path):
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config from {config_path}: {e}")
        return {}

def preview_orders(base, quote, account, config_path, num_orders=None, center_price=None):
    """Preview what orders would be created by the OrderBookMakerStrategy."""
    # Load configuration
    config = load_config(config_path)
    
    # Get trading pair key
    pair_key = f"{base}{quote}"
    
    # Check if the pair exists in the config
    if pair_key not in config.get('trading_pairs', {}):
        print(f"Trading pair {pair_key} not found in configuration")
        return
    
    # Get market maker parameters
    market_maker_params = config['trading_pairs'][pair_key].get('market_maker', {})
    
    # Override num_orders if specified
    if num_orders is not None:
        market_maker_params['num_orders'] = num_orders
    
    # Create mock client
    mock_client = MockClient()
    
    # If center price is not provided, use price tracker or fallback
    if center_price is None:
        price_tracker_params = config['trading_pairs'][pair_key].get('price_tracker', {})
        price_source = price_tracker_params.get('source') or price_tracker_params.get('price_source')
        
        print(f"Price tracker params: {price_tracker_params}")
        print(f"Price source: {price_source}")
        
        if price_source == 'fixed':
            center_price = Decimal(str(price_tracker_params.get('fallback_price', 0.0)))
            print(f"Using fixed fallback price: {center_price}")
        else:
            # For preview purposes, we'll use a random price around BTC market price
            # In a real scenario, this would come from an external source
            if pair_key == 'BTCUSDT':
                center_price = Decimal('65000') * (1 + Decimal(random.uniform(-0.01, 0.01)))
            elif pair_key == 'LIBREBTC':
                center_price = Decimal('0.000000008') * (1 + Decimal(random.uniform(-0.01, 0.01)))
            else:
                center_price = Decimal('1.0')
            print(f"Using simulated market price: {center_price}")
    else:
        center_price = Decimal(str(center_price))
        print(f"Using provided center price: {center_price}")
    
    print(f"Market maker parameters: {market_maker_params}")
    
    # Create strategy instance
    strategy = OrderBookMakerStrategy(
        client=mock_client,
        account=account,
        base_symbol=base,
        quote_symbol=quote,
        parameters=market_maker_params
    )
    
    # Set the center price
    strategy.center_price = center_price
    
    # Generate orders without placing them
    strategy._generate_orders()
    
    # Get the orders that would be created
    orders = mock_client.get_orders()
    
    # Print order summary
    print("\n" + "=" * 80)
    print(f"Order Preview for {base}/{quote} using account {account}")
    print(f"Center Price: {center_price}")
    print("=" * 80 + "\n")
    
    # Sort orders by price
    buy_orders = [o for o in orders if o['order_type'] == 'buy']
    sell_orders = [o for o in orders if o['order_type'] == 'sell']
    
    buy_orders.sort(key=lambda x: x['price'], reverse=True)
    sell_orders.sort(key=lambda x: x['price'])
    
    # Print buy orders
    print("BUY ORDERS:")
    print("-" * 80)
    print(f"{'Price':<15} {'Quantity':<15} {'Total Value':<15}")
    print("-" * 80)
    for order in buy_orders:
        price = order['price']
        quantity = order['quantity']
        total = price * quantity
        print(f"{price:<15.8f} {quantity:<15.8f} {total:<15.8f}")
    
    # Print sell orders
    print("\nSELL ORDERS:")
    print("-" * 80)
    print(f"{'Price':<15} {'Quantity':<15} {'Total Value':<15}")
    print("-" * 80)
    for order in sell_orders:
        price = order['price']
        quantity = order['quantity']
        total = price * quantity
        print(f"{price:<15.8f} {quantity:<15.8f} {total:<15.8f}")
    
    # Print summary
    print("\nSUMMARY:")
    print("-" * 80)
    print(f"Total Buy Orders: {len(buy_orders)}")
    print(f"Total Sell Orders: {len(sell_orders)}")
    print(f"Total Orders: {len(orders)}")
    
    buy_value = sum(o['price'] * o['quantity'] for o in buy_orders)
    sell_value = sum(o['price'] * o['quantity'] for o in sell_orders)
    
    print(f"Total Buy Value: {buy_value:.8f} {quote}")
    print(f"Total Sell Value: {sell_value:.8f} {quote}")
    
    buy_quantity = sum(o['quantity'] for o in buy_orders)
    sell_quantity = sum(o['quantity'] for o in sell_orders)
    
    print(f"Total Buy Quantity: {buy_quantity:.8f} {base}")
    print(f"Total Sell Quantity: {sell_quantity:.8f} {base}")

def main():
    """Main function to preview orders."""
    parser = argparse.ArgumentParser(description='Preview orders that would be created by the OrderBookMakerStrategy')
    
    # Required arguments
    parser.add_argument('--base', required=True, help='Base symbol (e.g., LIBRE, BTC)')
    parser.add_argument('--quote', required=True, help='Quote symbol (e.g., BTC, USDT)')
    
    # Optional arguments
    parser.add_argument('--account', help='Account to use for orders')
    parser.add_argument('--config', default='config/strategies.yaml', help='Path to config file')
    parser.add_argument('--num-orders', type=int, help='Override number of orders to generate')
    parser.add_argument('--center-price', type=float, help='Override center price')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Get account from config if not provided
    account = args.account
    if account is None:
        pair_key = f"{args.base}{args.quote}"
        if pair_key in config.get('accounts', {}):
            account = config['accounts'][pair_key].get('liquidity_provider')
        else:
            account = config.get('accounts', {}).get('main')
    
    if account is None:
        print("Error: No account specified and none found in configuration")
        return
    
    # Preview orders
    preview_orders(
        args.base,
        args.quote,
        account,
        args.config,
        args.num_orders,
        args.center_price
    )

if __name__ == "__main__":
    main()
