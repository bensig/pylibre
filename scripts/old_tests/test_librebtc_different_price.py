#!/usr/bin/env python3
"""
Test script for LIBRE/BTC trading pair with different prices.
Tests direct buy and sell orders with specific quantities and prices.
"""

import sys
import os
import time
from decimal import Decimal
import logging

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pylibre.client import LibreClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LibreBTCTest")

def place_order_direct(client, account, order_type, quantity, price, base_symbol, quote_symbol):
    """Place an order directly using the transfer method with the correct memo format."""
    # Define precision for base and quote symbols
    base_precision = 4 if base_symbol == 'LIBRE' else 8
    quote_precision = 8  # USDT and BTC use 8 decimal places
    
    # Parse quantity to get amount only (without symbol)
    quantity_parts = quantity.split()
    quantity_amount = Decimal(quantity_parts[0])
    
    # Format with correct precision
    if order_type == 'buy':
        # For buy orders, we send quote currency (e.g., BTC)
        send_amount = quantity_amount * Decimal(price)
        send_symbol = quote_symbol
        send_precision = quote_precision
    else:  # sell
        # For sell orders, we send base currency (e.g., LIBRE)
        send_amount = quantity_amount
        send_symbol = base_symbol
        send_precision = base_precision
    
    # Format the send amount with correct precision
    send_quantity = f"{send_amount:.{send_precision}f} {send_symbol}"
    
    # Create the action memo with correct format
    # Format: "buy:100.0000 LIBRE:0.00000001 BTC" or "sell:100.0000 LIBRE:0.00000001 BTC"
    memo = f"{order_type}:{quantity_amount:.{base_precision}f} {base_symbol}:{Decimal(price):.{quote_precision}f} {quote_symbol}"
    
    print(f"Placing {order_type} order: {quantity} @ {price} {quote_symbol}")
    print(f"Transfer details:")
    print(f"  From: {account}")
    print(f"  To: dex.libre")
    print(f"  Amount: {send_quantity}")
    print(f"  Memo: {memo}")
    
    # Execute the transfer to place the order
    result = client.transfer(
        from_account=account,
        to_account="dex.libre",
        quantity=send_quantity,
        memo=memo
    )
    
    return result

def test_librebtc_pair(client, account):
    """Test LIBRE/BTC trading pair with different prices."""
    base_symbol = "LIBRE"
    quote_symbol = "BTC"
    
    print(f"\n{'='*50}")
    print(f"Testing LIBRE/BTC Trading Pair with Different Prices")
    print(f"{'='*50}")
    
    # Check initial balances
    print("\nChecking initial balances...")
    libre_balance = client.get_currency_balance(account, "LIBRE")
    btc_balance = client.get_currency_balance(account, "BTC")
    
    print(f"{account} LIBRE balance: {libre_balance}")
    print(f"{account} BTC balance: {btc_balance}")
    
    # Test different prices
    prices = [
        "0.00000002",  # 2 satoshis
        "0.00000010",  # 10 satoshis
        "0.00000100",  # 100 satoshis
        "0.00001000",  # 1000 satoshis
    ]
    
    sell_results = []
    buy_results = []
    
    # Test sell orders with different prices
    print("\nTesting sell orders with different prices...")
    for price in prices:
        print(f"\nSelling 10 LIBRE at {price} BTC")
        sell_quantity = "10.0000 LIBRE"
        
        sell_result = place_order_direct(
            client=client,
            account=account,
            order_type="sell",
            quantity=sell_quantity,
            price=price,
            base_symbol=base_symbol,
            quote_symbol=quote_symbol
        )
        
        if sell_result["success"]:
            print(f"Sell order placed successfully. Transaction ID: {sell_result['data']['transaction_id']}")
        else:
            print(f"Failed to place sell order: {sell_result['error']}")
        
        sell_results.append((price, sell_result["success"]))
        time.sleep(1)
    
    # Test buy orders with different prices
    print("\nTesting buy orders with different prices...")
    for price in prices:
        print(f"\nBuying 10 LIBRE at {price} BTC")
        buy_quantity = "10.0000 LIBRE"
        
        buy_result = place_order_direct(
            client=client,
            account=account,
            order_type="buy",
            quantity=buy_quantity,
            price=price,
            base_symbol=base_symbol,
            quote_symbol=quote_symbol
        )
        
        if buy_result["success"]:
            print(f"Buy order placed successfully. Transaction ID: {buy_result['data']['transaction_id']}")
        else:
            print(f"Failed to place buy order: {buy_result['error']}")
        
        buy_results.append((price, buy_result["success"]))
        time.sleep(1)
    
    # Check final balances
    print("\nChecking final balances...")
    libre_balance_after = client.get_currency_balance(account, "LIBRE")
    btc_balance_after = client.get_currency_balance(account, "BTC")
    
    print(f"{account} LIBRE balance: {libre_balance_after}")
    print(f"{account} BTC balance: {btc_balance_after}")
    
    # Summary
    print("\nLIBRE/BTC trading test summary:")
    print("\nSell orders:")
    for price, success in sell_results:
        print(f"  Price {price} BTC: {'Success' if success else 'Failed'}")
    
    print("\nBuy orders:")
    for price, success in buy_results:
        print(f"  Price {price} BTC: {'Success' if success else 'Failed'}")
    
    print("\nLIBRE/BTC trading test completed!")

def main():
    # Define account to test
    account = "bentester"
    
    # Initialize client
    print("Initializing LibreClient...")
    client = LibreClient(network='testnet', verbose=True)
    
    # Test LIBRE/BTC trading pair
    test_librebtc_pair(client, account)
    
    print("\nTesting completed!")

if __name__ == "__main__":
    main() 