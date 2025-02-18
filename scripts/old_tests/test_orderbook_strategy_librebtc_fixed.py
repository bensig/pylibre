#!/usr/bin/env python3
"""
Test script for OrderBookMakerStrategy with LIBRE/BTC trading pair.
This script tests creating a spread of orders around a fixed price.
Fixed version with proper memo formatting and balance handling.
"""

import sys
import os
import time
import random
from decimal import Decimal

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pylibre.client import LibreClient
from pylibre.dex import DexClient

def place_sell_order(client, account, quantity, price, base_symbol, quote_symbol, dex_contract):
    """Place a sell order for a specific trading pair."""
    print(f"\nPlacing sell order: {quantity} {base_symbol} @ {price} {quote_symbol}")
    
    # Determine the contract for the base symbol
    base_contract = "eosio.token" if base_symbol == "LIBRE" else f"{base_symbol.lower()}.libre"
    
    # Create the memo with the correct format
    memo = f"sell:{quantity} {base_symbol}:{price} {quote_symbol}"
    
    print(f"Transfer Details:")
    print(f"From: {account}")
    print(f"To: {dex_contract}")
    print(f"Amount: {quantity} {base_symbol}")
    print(f"Contract: {base_contract}")
    print(f"Memo: {memo}")
    
    try:
        result = client.transfer(
            from_account=account,
            to_account=dex_contract,
            quantity=f"{quantity} {base_symbol}",
            memo=memo,
            contract=base_contract
        )
        
        if result.get("success"):
            print("✅ Sell order placed successfully")
            print(f"Transaction ID: {result.get('data', {}).get('transaction_id')}")
            return True
        else:
            print(f"❌ Failed to place sell order: {result.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Error placing sell order: {str(e)}")
        return False

def place_buy_order(client, account, quantity, price, base_symbol, quote_symbol, dex_contract):
    """Place a buy order for a specific trading pair."""
    print(f"\nPlacing buy order: {quantity} {base_symbol} @ {price} {quote_symbol}")
    
    # Calculate the amount of quote currency to send
    quote_amount = Decimal(str(quantity)) * Decimal(str(price))
    quote_amount_str = f"{quote_amount:.8f}"
    
    # Determine the contract for the quote symbol
    quote_contract = f"{quote_symbol.lower()}.libre"
    
    # Create the memo with the correct format
    memo = f"buy:{quantity} {base_symbol}:{price} {quote_symbol}"
    
    print(f"Transfer Details:")
    print(f"From: {account}")
    print(f"To: {dex_contract}")
    print(f"Amount: {quote_amount_str} {quote_symbol}")
    print(f"Contract: {quote_contract}")
    print(f"Memo: {memo}")
    
    try:
        result = client.transfer(
            from_account=account,
            to_account=dex_contract,
            quantity=f"{quote_amount_str} {quote_symbol}",
            memo=memo,
            contract=quote_contract
        )
        
        if result.get("success"):
            print("✅ Buy order placed successfully")
            print(f"Transaction ID: {result.get('data', {}).get('transaction_id')}")
            return True
        else:
            print(f"❌ Failed to place buy order: {result.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Error placing buy order: {str(e)}")
        return False

def create_order_book_spread(client, account, base_symbol, quote_symbol, 
                            center_price, num_orders, min_spread, max_spread):
    """
    Create a spread of orders around a center price.
    
    Args:
        client: LibreClient instance
        account: Account to place orders from
        base_symbol: Base currency symbol (e.g., "LIBRE")
        quote_symbol: Quote currency symbol (e.g., "BTC")
        center_price: Center price for the spread
        num_orders: Number of orders to place on each side
        min_spread: Minimum spread percentage (e.g., 0.01 for 1%)
        max_spread: Maximum spread percentage (e.g., 0.05 for 5%)
    """
    print(f"\n{'='*50}")
    print(f"Creating OrderBook Spread for {base_symbol}/{quote_symbol}")
    print(f"{'='*50}")
    print(f"Center Price: {center_price} {quote_symbol}")
    print(f"Number of Orders: {num_orders} on each side")
    print(f"Spread Range: {min_spread*100}% to {max_spread*100}%")
    
    dex_contract = "dex.libre"
    
    # Check initial balances
    base_contract = "eosio.token" if base_symbol == "LIBRE" else f"{base_symbol.lower()}.libre"
    quote_contract = f"{quote_symbol.lower()}.libre"
    
    print(f"\nChecking initial balances...")
    print(f"Using contract: {base_contract} for symbol: {base_symbol}")
    print(f"Using contract: {quote_contract} for symbol: {quote_symbol}")
    
    base_balance = client.get_currency_balance(account, base_symbol)
    quote_balance = client.get_currency_balance(account, quote_symbol)
    
    print(f"\nInitial Balances:")
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
        
        # Random quantity between 10 and 100 LIBRE
        quantity = Decimal(str(random.uniform(10, 100))).quantize(Decimal('0.0001'))
        
        sell_orders.append({
            "price": price,
            "quantity": quantity
        })
    
    # Generate buy orders (bids)
    print(f"\nGenerating {num_orders} buy orders...")
    buy_orders = []
    
    # Calculate price step for linear distribution
    price_step = (center_price_dec - min_price) / Decimal(str(num_orders))
    
    for i in range(num_orders):
        # Linear price distribution below center price
        price = center_price_dec - (price_step * Decimal(str(i + 1)))
        
        # Random quantity between 10 and 100 LIBRE
        quantity = Decimal(str(random.uniform(10, 100))).quantize(Decimal('0.0001'))
        
        buy_orders.append({
            "price": price,
            "quantity": quantity
        })
    
    # Place sell orders
    print(f"\nPlacing {len(sell_orders)} sell orders...")
    sell_success_count = 0
    
    for i, order in enumerate(sell_orders):
        price_str = f"{order['price']:.10f}"
        quantity_str = f"{order['quantity']:.4f}"
        
        print(f"\nSell Order {i+1}/{len(sell_orders)}:")
        print(f"  Price: {price_str} {quote_symbol}")
        print(f"  Quantity: {quantity_str} {base_symbol}")
        
        success = place_sell_order(
            client=client,
            account=account,
            quantity=quantity_str,
            price=price_str,
            base_symbol=base_symbol,
            quote_symbol=quote_symbol,
            dex_contract=dex_contract
        )
        
        if success:
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
        
        print(f"\nBuy Order {i+1}/{len(buy_orders)}:")
        print(f"  Price: {price_str} {quote_symbol}")
        print(f"  Quantity: {quantity_str} {base_symbol}")
        
        success = place_buy_order(
            client=client,
            account=account,
            quantity=quantity_str,
            price=price_str,
            base_symbol=base_symbol,
            quote_symbol=quote_symbol,
            dex_contract=dex_contract
        )
        
        if success:
            print(f"  ✅ Order placed successfully")
            buy_success_count += 1
        else:
            print(f"  ❌ Failed to place order")
        
        # Small delay to avoid rate limiting
        time.sleep(0.5)
    
    # Check final balances
    print(f"\nChecking final balances...")
    print(f"Using contract: {base_contract} for symbol: {base_symbol}")
    print(f"Using contract: {quote_contract} for symbol: {quote_symbol}")
    
    base_balance_after = client.get_currency_balance(account, base_symbol)
    quote_balance_after = client.get_currency_balance(account, quote_symbol)
    
    print(f"\nFinal Balances:")
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
    # Initialize client
    print("Initializing LibreClient...")
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
        max_spread=max_spread
    )
    
    print(f"\nStrategy test completed with {result['sell_success'] + result['buy_success']}/{result['total_orders']} orders placed successfully")

if __name__ == "__main__":
    main() 