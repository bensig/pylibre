#!/usr/bin/env python3
"""
Test script for OrderBookMakerStrategy with LIBRE/BTC trading pair.
This script respects the minimum values from the config file.
"""

import sys
import os
import time
import random
import yaml
from decimal import Decimal

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pylibre.client import LibreClient
from pylibre.dex import DexClient

def load_config(config_path='config/config.yaml'):
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        return config
    except Exception as e:
        print(f"Error loading config: {str(e)}")
        # Use default values if config can't be loaded
        return {
            "strategies": {
                "LIBRE/BTC": {
                    "min_order_value_libre": 100.0000,
                    "max_order_value_libre": 1000.0000,
                    "min_order_value_btc": 0.00001000,
                    "max_order_value_btc": 0.00100000
                }
            }
        }

def create_order_book_spread(client, account, base_symbol, quote_symbol, 
                            center_price, num_orders, min_spread, max_spread,
                            min_base_value, max_base_value, min_quote_value, max_quote_value):
    """
    Create a spread of orders around a center price, respecting minimum values.
    
    Args:
        client: LibreClient instance
        account: Account to place orders from
        base_symbol: Base currency symbol (e.g., "LIBRE")
        quote_symbol: Quote currency symbol (e.g., "BTC")
        center_price: Center price for the spread
        num_orders: Number of orders to place on each side
        min_spread: Minimum spread percentage (e.g., 0.01 for 1%)
        max_spread: Maximum spread percentage (e.g., 0.05 for 5%)
        min_base_value: Minimum value in base currency (e.g., 100.0000 LIBRE)
        max_base_value: Maximum value in base currency (e.g., 1000.0000 LIBRE)
        min_quote_value: Minimum value in quote currency (e.g., 0.00001000 BTC)
        max_quote_value: Maximum value in quote currency (e.g., 0.00100000 BTC)
    """
    print(f"\n{'='*50}")
    print(f"Creating OrderBook Spread for {base_symbol}/{quote_symbol}")
    print(f"{'='*50}")
    print(f"Center Price: {center_price} {quote_symbol}")
    print(f"Number of Orders: {num_orders} on each side")
    print(f"Spread Range: {min_spread*100}% to {max_spread*100}%")
    print(f"Min {base_symbol} Value: {min_base_value}")
    print(f"Max {base_symbol} Value: {max_base_value}")
    print(f"Min {quote_symbol} Value: {min_quote_value}")
    print(f"Max {quote_symbol} Value: {max_quote_value}")
    
    # Convert all values to Decimal to avoid type errors
    min_base_value = Decimal(str(min_base_value))
    max_base_value = Decimal(str(max_base_value))
    min_quote_value = Decimal(str(min_quote_value))
    max_quote_value = Decimal(str(max_quote_value))
    
    dex_contract = "dex.libre"
    
    # Initialize DexClient
    dex = DexClient(client)
    
    # Check initial balances
    print("\nChecking initial balances...")
    base_balance = client.get_currency_balance(account, base_symbol)
    quote_balance = client.get_currency_balance(account, quote_symbol)
    
    print(f"{account} {base_symbol} balance: {base_balance}")
    print(f"{account} {quote_symbol} balance: {quote_balance}")
    
    # Calculate price range
    center_price_dec = Decimal(str(center_price))
    min_price = center_price_dec * (Decimal('1') - Decimal(str(max_spread)))
    max_price = center_price_dec * (Decimal('1') + Decimal(str(max_spread)))
    
    print(f"\nPrice Range:")
    print(f"Min Price: {min_price:.10f} {quote_symbol}")
    print(f"Max Price: {max_price:.10f} {quote_symbol}")
    
    # Generate sell orders (offers)
    print(f"\nGenerating {num_orders} sell orders...")
    sell_orders = []
    
    # Calculate price step for linear distribution
    price_step = (max_price - center_price_dec) / Decimal(str(num_orders))
    
    for i in range(num_orders):
        # Linear price distribution above center price
        price = center_price_dec + (price_step * Decimal(str(i + 1)))
        
        # Random quantity between min and max LIBRE value, ensuring it meets minimum BTC value
        min_quantity = max(min_base_value, min_quote_value / price)
        max_quantity = min(max_base_value, max_quote_value / price)
        
        if min_quantity > max_quantity:
            print(f"Warning: Cannot generate valid quantity for price {price:.10f} {quote_symbol}")
            print(f"Min quantity {min_quantity} > Max quantity {max_quantity}")
            continue
        
        quantity = Decimal(str(random.uniform(float(min_quantity), float(max_quantity)))).quantize(Decimal('0.0001'))
        
        # Verify the order meets minimum requirements
        quote_value = quantity * price
        if quote_value < min_quote_value:
            print(f"Warning: Order value {quote_value:.8f} {quote_symbol} is below minimum {min_quote_value} {quote_symbol}")
            print(f"Adjusting quantity to meet minimum value...")
            quantity = (min_quote_value / price).quantize(Decimal('0.0001'))
            quote_value = quantity * price
        
        if quantity < min_base_value:
            print(f"Warning: Order quantity {quantity:.4f} {base_symbol} is below minimum {min_base_value} {base_symbol}")
            print(f"Adjusting quantity to meet minimum value...")
            quantity = min_base_value.quantize(Decimal('0.0001'))
            quote_value = quantity * price
        
        sell_orders.append({
            "price": price,
            "quantity": quantity,
            "quote_value": quote_value
        })
    
    # Generate buy orders (bids)
    print(f"\nGenerating {num_orders} buy orders...")
    buy_orders = []
    
    # Calculate price step for linear distribution
    price_step = (center_price_dec - min_price) / Decimal(str(num_orders))
    
    for i in range(num_orders):
        # Linear price distribution below center price
        price = center_price_dec - (price_step * Decimal(str(i + 1)))
        
        # Random quantity between min and max LIBRE value, ensuring it meets minimum BTC value
        min_quantity = max(min_base_value, min_quote_value / price)
        max_quantity = min(max_base_value, max_quote_value / price)
        
        if min_quantity > max_quantity:
            print(f"Warning: Cannot generate valid quantity for price {price:.10f} {quote_symbol}")
            print(f"Min quantity {min_quantity} > Max quantity {max_quantity}")
            continue
        
        quantity = Decimal(str(random.uniform(float(min_quantity), float(max_quantity)))).quantize(Decimal('0.0001'))
        
        # Verify the order meets minimum requirements
        quote_value = quantity * price
        if quote_value < min_quote_value:
            print(f"Warning: Order value {quote_value:.8f} {quote_symbol} is below minimum {min_quote_value} {quote_symbol}")
            print(f"Adjusting quantity to meet minimum value...")
            quantity = (min_quote_value / price).quantize(Decimal('0.0001'))
            quote_value = quantity * price
        
        if quantity < min_base_value:
            print(f"Warning: Order quantity {quantity:.4f} {base_symbol} is below minimum {min_base_value} {base_symbol}")
            print(f"Adjusting quantity to meet minimum value...")
            quantity = min_base_value.quantize(Decimal('0.0001'))
            quote_value = quantity * price
        
        buy_orders.append({
            "price": price,
            "quantity": quantity,
            "quote_value": quote_value
        })
    
    # Place sell orders
    print(f"\nPlacing {len(sell_orders)} sell orders...")
    sell_success_count = 0
    
    for i, order in enumerate(sell_orders):
        price_str = f"{order['price']:.10f}"
        quantity_str = f"{order['quantity']:.4f}"
        quote_value_str = f"{order['quote_value']:.8f}"
        
        print(f"\nSell Order {i+1}/{len(sell_orders)}:")
        print(f"  Price: {price_str} {quote_symbol}")
        print(f"  Quantity: {quantity_str} {base_symbol}")
        print(f"  Value: {quote_value_str} {quote_symbol}")
        
        result = dex.place_order(
            account=account,
            order_type="sell",
            quantity=quantity_str,
            price=price_str,
            quote_symbol=quote_symbol,
            base_symbol=base_symbol
        )
        
        if result:
            print(f"  ✅ Order placed successfully")
            sell_success_count += 1
        else:
            print(f"  ❌ Failed to place order")
        
        # Small delay to avoid rate limiting
        time.sleep(0.5)
    
    # Place buy orders
    print(f"\nPlacing {len(buy_orders)} buy orders...")
    buy_success_count = 0
    
    for i, order in enumerate(buy_orders):
        price_str = f"{order['price']:.10f}"
        quantity_str = f"{order['quantity']:.4f}"
        quote_value_str = f"{order['quote_value']:.8f}"
        
        print(f"\nBuy Order {i+1}/{len(buy_orders)}:")
        print(f"  Price: {price_str} {quote_symbol}")
        print(f"  Quantity: {quantity_str} {base_symbol}")
        print(f"  Value: {quote_value_str} {quote_symbol}")
        
        result = dex.place_order(
            account=account,
            order_type="buy",
            quantity=quantity_str,
            price=price_str,
            quote_symbol=quote_symbol,
            base_symbol=base_symbol
        )
        
        if result:
            print(f"  ✅ Order placed successfully")
            buy_success_count += 1
        else:
            print(f"  ❌ Failed to place order")
        
        # Small delay to avoid rate limiting
        time.sleep(0.5)
    
    # Check final balances
    print("\nChecking final balances...")
    base_balance_after = client.get_currency_balance(account, base_symbol)
    quote_balance_after = client.get_currency_balance(account, quote_symbol)
    
    print(f"{account} {base_symbol} balance: {base_balance_after}")
    print(f"{account} {quote_symbol} balance: {quote_balance_after}")
    
    # Calculate balance changes safely
    try:
        base_balance_num = float(base_balance.split()[0])
        base_balance_after_num = float(base_balance_after.split()[0])
        base_change = base_balance_num - base_balance_after_num
        
        quote_balance_num = float(quote_balance.split()[0])
        quote_balance_after_num = float(quote_balance_after.split()[0])
        quote_change = quote_balance_num - quote_balance_after_num
    except (ValueError, IndexError):
        base_change = "Unable to calculate"
        quote_change = "Unable to calculate"
    
    # Print summary
    print(f"\nOrderBook Spread Summary:")
    print(f"Sell Orders: {sell_success_count}/{len(sell_orders)} placed successfully")
    print(f"Buy Orders: {buy_success_count}/{len(buy_orders)} placed successfully")
    print(f"{base_symbol} Balance Change: {base_change}")
    print(f"{quote_symbol} Balance Change: {quote_change}")
    
    return {
        "sell_success": sell_success_count,
        "buy_success": buy_success_count,
        "total_orders": len(sell_orders) + len(buy_orders)
    }

def main():
    # Load configuration
    config = load_config()
    
    # Get minimum values from config
    try:
        pair_config = config["strategies"]["LIBRE/BTC"]
        min_libre_value = pair_config["min_order_value_libre"]
        max_libre_value = pair_config["max_order_value_libre"]
        min_btc_value = pair_config["min_order_value_btc"]
        max_btc_value = pair_config["max_order_value_btc"]
    except (KeyError, TypeError):
        print("Warning: Could not load LIBRE/BTC config, using default values")
        min_libre_value = 100.0000
        max_libre_value = 1000.0000
        min_btc_value = 0.00001000
        max_btc_value = 0.00100000
    
    print(f"Using configuration values:")
    print(f"  Minimum LIBRE order value: {min_libre_value}")
    print(f"  Maximum LIBRE order value: {max_libre_value}")
    print(f"  Minimum BTC order value: {min_btc_value}")
    print(f"  Maximum BTC order value: {max_btc_value}")
    
    # Initialize client
    print("\nInitializing LibreClient...")
    client = LibreClient(network='testnet', verbose=True)
    
    # Define account to test
    account = "bentest3"
    
    # Define trading pair parameters
    base_symbol = "LIBRE"
    quote_symbol = "BTC"
    
    # Define strategy parameters
    center_price = "0.00000001"  # 1 satoshi per LIBRE
    num_orders = 5  # Number of orders on each side
    min_spread = 0.01  # 1%
    max_spread = 0.05  # 5%
    
    # Create order book spread
    result = create_order_book_spread(
        client=client,
        account=account,
        base_symbol=base_symbol,
        quote_symbol=quote_symbol,
        center_price=center_price,
        num_orders=num_orders,
        min_spread=min_spread,
        max_spread=max_spread,
        min_base_value=min_libre_value,
        max_base_value=max_libre_value,
        min_quote_value=min_btc_value,
        max_quote_value=max_btc_value
    )
    
    print(f"\nStrategy test completed with {result['sell_success'] + result['buy_success']}/{result['total_orders']} orders placed successfully")

if __name__ == "__main__":
    main() 