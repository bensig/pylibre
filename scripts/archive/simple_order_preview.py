#!/usr/bin/env python3
"""
Simple script to preview what orders would be created for LIBREBTC
without actually placing them on the blockchain.
"""

import sys
import os
import argparse
import yaml
from decimal import Decimal
import random

def generate_orders(center_price, num_orders=30, min_spread=0.01, max_spread=0.15, 
                    min_base_value=10, max_base_value=1000, 
                    min_quote_value=0.0001, max_quote_value=0.01):
    """Generate a list of orders around a center price."""
    orders = []
    orders_per_side = num_orders // 2
    
    # Calculate price range for buy orders (below center price)
    buy_min_price = center_price * (1 - max_spread)
    buy_max_price = center_price * (1 - min_spread)
    
    # Calculate price range for sell orders (above center price)
    sell_min_price = center_price * (1 + min_spread)
    sell_max_price = center_price * (1 + max_spread)
    
    # Generate buy orders
    for i in range(orders_per_side):
        # Linear distribution of prices
        price_factor = i / (orders_per_side - 1) if orders_per_side > 1 else 0.5
        price = buy_min_price + (buy_max_price - buy_min_price) * price_factor
        
        # Random quantity that meets minimum and maximum value constraints
        max_quantity_by_quote = max_quote_value / price
        min_quantity_by_quote = min_quote_value / price
        
        # Ensure we respect both base and quote limits
        min_quantity = max(min_base_value, min_quantity_by_quote)
        max_quantity = min(max_base_value, max_quantity_by_quote)
        
        # If min > max, use the minimum value
        if min_quantity > max_quantity:
            quantity = min_quantity
        else:
            # Random quantity between min and max
            quantity = min_quantity + (max_quantity - min_quantity) * random.random()
        
        # Add the buy order
        orders.append({
            'price': price,
            'quantity': quantity,
            'order_type': 'buy',
            'total_value': price * quantity
        })
    
    # Generate sell orders
    for i in range(orders_per_side):
        # Linear distribution of prices
        price_factor = i / (orders_per_side - 1) if orders_per_side > 1 else 0.5
        price = sell_min_price + (sell_max_price - sell_min_price) * price_factor
        
        # Random quantity that meets minimum and maximum value constraints
        max_quantity_by_quote = max_quote_value / price
        min_quantity_by_quote = min_quote_value / price
        
        # Ensure we respect both base and quote limits
        min_quantity = max(min_base_value, min_quantity_by_quote)
        max_quantity = min(max_base_value, max_quantity_by_quote)
        
        # If min > max, use the minimum value
        if min_quantity > max_quantity:
            quantity = min_quantity
        else:
            # Random quantity between min and max
            quantity = min_quantity + (max_quantity - min_quantity) * random.random()
        
        # Add the sell order
        orders.append({
            'price': price,
            'quantity': quantity,
            'order_type': 'sell',
            'total_value': price * quantity
        })
    
    return orders

def load_config(config_path):
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config from {config_path}: {e}")
        return {}

def preview_orders(base, quote, account, center_price, num_orders=30, 
                  min_spread=0.01, max_spread=0.15, 
                  min_base_value=10, max_base_value=1000, 
                  min_quote_value=0.0001, max_quote_value=0.01):
    """Preview what orders would be created."""
    
    # Generate orders
    orders = generate_orders(
        center_price=center_price,
        num_orders=num_orders,
        min_spread=min_spread,
        max_spread=max_spread,
        min_base_value=min_base_value,
        max_base_value=max_base_value,
        min_quote_value=min_quote_value,
        max_quote_value=max_quote_value
    )
    
    # Sort orders by price
    buy_orders = [o for o in orders if o['order_type'] == 'buy']
    sell_orders = [o for o in orders if o['order_type'] == 'sell']
    
    buy_orders.sort(key=lambda x: x['price'], reverse=True)
    sell_orders.sort(key=lambda x: x['price'])
    
    # Print order summary
    print("\n" + "=" * 80)
    print(f"Order Preview for {base}/{quote} using account {account}")
    print(f"Center Price: {center_price}")
    print("=" * 80 + "\n")
    
    # Print buy orders
    print("BUY ORDERS:")
    print("-" * 80)
    print(f"{'Price':<20} {'Quantity':<20} {'Total Value':<20}")
    print("-" * 80)
    for order in buy_orders:
        price = order['price']
        quantity = order['quantity']
        total = order['total_value']
        print(f"{price:<20.10f} {quantity:<20.4f} {total:<20.10f}")
    
    # Print sell orders
    print("\nSELL ORDERS:")
    print("-" * 80)
    print(f"{'Price':<20} {'Quantity':<20} {'Total Value':<20}")
    print("-" * 80)
    for order in sell_orders:
        price = order['price']
        quantity = order['quantity']
        total = order['total_value']
        print(f"{price:<20.10f} {quantity:<20.4f} {total:<20.10f}")
    
    # Print summary
    print("\nSUMMARY:")
    print("-" * 80)
    print(f"Total Buy Orders: {len(buy_orders)}")
    print(f"Total Sell Orders: {len(sell_orders)}")
    print(f"Total Orders: {len(orders)}")
    
    buy_value = sum(o['total_value'] for o in buy_orders)
    sell_value = sum(o['total_value'] for o in sell_orders)
    
    print(f"Total Buy Value: {buy_value:.10f} {quote}")
    print(f"Total Sell Value: {sell_value:.10f} {quote}")
    
    buy_quantity = sum(o['quantity'] for o in buy_orders)
    sell_quantity = sum(o['quantity'] for o in sell_orders)
    
    print(f"Total Buy Quantity: {buy_quantity:.4f} {base}")
    print(f"Total Sell Quantity: {sell_quantity:.4f} {base}")

def main():
    """Main function to preview orders."""
    parser = argparse.ArgumentParser(description='Preview orders for LIBREBTC')
    
    # Required arguments
    parser.add_argument('--base', default='LIBRE', help='Base symbol (default: LIBRE)')
    parser.add_argument('--quote', default='BTC', help='Quote symbol (default: BTC)')
    
    # Optional arguments
    parser.add_argument('--account', default='jecashking', help='Account to use for orders')
    parser.add_argument('--config', default='config/strategies.mainnet.yaml', help='Path to config file')
    parser.add_argument('--center-price', type=float, default=0.000000008, help='Center price')
    parser.add_argument('--num-orders', type=int, default=30, help='Number of orders to generate')
    parser.add_argument('--min-spread', type=float, default=0.01, help='Minimum spread percentage')
    parser.add_argument('--max-spread', type=float, default=0.15, help='Maximum spread percentage')
    parser.add_argument('--min-base-value', type=float, default=10, help=f'Minimum base value')
    parser.add_argument('--max-base-value', type=float, default=1000, help=f'Maximum base value')
    parser.add_argument('--min-quote-value', type=float, default=0.0001, help=f'Minimum quote value')
    parser.add_argument('--max-quote-value', type=float, default=0.01, help=f'Maximum quote value')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Get parameters from config if available
    pair_key = f"{args.base}{args.quote}"
    if pair_key in config.get('trading_pairs', {}):
        market_maker_params = config['trading_pairs'][pair_key].get('market_maker', {})
        
        # Override defaults with config values if not specified in command line
        if 'num_orders' in market_maker_params and args.num_orders == 30:
            args.num_orders = market_maker_params['num_orders']
        
        if 'min_spread_percentage' in market_maker_params and args.min_spread == 0.01:
            args.min_spread = float(market_maker_params['min_spread_percentage'])
        
        if 'max_spread_percentage' in market_maker_params and args.max_spread == 0.15:
            args.max_spread = float(market_maker_params['max_spread_percentage'])
    
    # Get account from config if available
    if pair_key in config.get('accounts', {}) and args.account == 'jecashking':
        args.account = config['accounts'][pair_key].get('liquidity_provider', args.account)
    
    # Preview orders
    preview_orders(
        args.base,
        args.quote,
        args.account,
        Decimal(str(args.center_price)),
        args.num_orders,
        args.min_spread,
        args.max_spread,
        args.min_base_value,
        args.max_base_value,
        args.min_quote_value,
        args.max_quote_value
    )

if __name__ == "__main__":
    main()
