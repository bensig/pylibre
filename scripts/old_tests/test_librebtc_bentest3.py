#!/usr/bin/env python3
"""
Test script for LIBRE/BTC trading pair using the bentest3 account.
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

def place_sell_order(client, account, quantity, price):
    """Place a sell order with the exact format provided."""
    # Parse quantity to get amount only (without symbol)
    quantity_parts = quantity.split()
    quantity_amount = Decimal(quantity_parts[0])
    symbol = quantity_parts[1]
    
    # Format with correct precision
    precision = 4 if symbol == 'LIBRE' else 8
    formatted_quantity = f"{quantity_amount:.{precision}f} {symbol}"
    
    # Create the memo with exact format
    memo = f"sell:{quantity_amount:.{precision}f} {symbol}:{price} BTC"
    
    print(f"Placing sell order:")
    print(f"  From: {account}")
    print(f"  To: dex.libre")
    print(f"  Amount: {formatted_quantity}")
    print(f"  Memo: {memo}")
    
    # Execute the transfer to place the order
    result = client.transfer(
        from_account=account,
        to_account="dex.libre",
        quantity=formatted_quantity,
        memo=memo
    )
    
    return result

def place_buy_order(client, account, quantity, price):
    """Place a buy order with the exact format provided."""
    # Parse quantity to get amount only (without symbol)
    quantity_parts = quantity.split()
    quantity_amount = Decimal(quantity_parts[0])
    symbol = quantity_parts[1]
    
    # Calculate BTC amount to send
    btc_amount = quantity_amount * Decimal(price)
    
    # Format with correct precision
    precision = 4 if symbol == 'LIBRE' else 8
    formatted_btc = f"{btc_amount:.8f} BTC"
    
    # Create the memo with exact format
    memo = f"buy:{quantity_amount:.{precision}f} {symbol}:{price} BTC"
    
    print(f"Placing buy order:")
    print(f"  From: {account}")
    print(f"  To: dex.libre")
    print(f"  Amount: {formatted_btc}")
    print(f"  Memo: {memo}")
    
    # Execute the transfer to place the order
    result = client.transfer(
        from_account=account,
        to_account="dex.libre",
        quantity=formatted_btc,
        memo=memo
    )
    
    return result

def test_librebtc_pair(client, account):
    """Test LIBRE/BTC trading pair with specific orders."""
    print(f"\n{'='*50}")
    print(f"Testing LIBRE/BTC Trading Pair with {account}")
    print(f"{'='*50}")
    
    # Check initial balances
    print("\nChecking initial balances...")
    libre_balance = client.get_currency_balance(account, "LIBRE")
    btc_balance = client.get_currency_balance(account, "BTC")
    
    print(f"{account} LIBRE balance: {libre_balance}")
    print(f"{account} BTC balance: {btc_balance}")
    
    # Test 1: Sell 10 LIBRE at 0.0000000055 BTC (using the exact format provided)
    print("\nTest 1: Selling 10 LIBRE at 0.0000000055 BTC")
    sell_quantity = "10.0000 LIBRE"
    sell_price = "0.0000000055"  # BTC per LIBRE
    
    sell_result = place_sell_order(
        client=client,
        account=account,
        quantity=sell_quantity,
        price=sell_price
    )
    
    if sell_result["success"]:
        print(f"Sell order placed successfully. Transaction ID: {sell_result['data']['transaction_id']}")
    else:
        print(f"Failed to place sell order: {sell_result['error']}")
    
    # Wait a moment
    time.sleep(2)
    
    # Test 2: Buy 10 LIBRE at 0.0000000055 BTC
    print("\nTest 2: Buying 10 LIBRE at 0.0000000055 BTC")
    buy_quantity = "10.0000 LIBRE"
    buy_price = "0.0000000055"  # BTC per LIBRE
    
    buy_result = place_buy_order(
        client=client,
        account=account,
        quantity=buy_quantity,
        price=buy_price
    )
    
    if buy_result["success"]:
        print(f"Buy order placed successfully. Transaction ID: {buy_result['data']['transaction_id']}")
    else:
        print(f"Failed to place buy order: {buy_result['error']}")
    
    # Wait a moment
    time.sleep(2)
    
    # Check final balances
    print("\nChecking final balances...")
    libre_balance_after = client.get_currency_balance(account, "LIBRE")
    btc_balance_after = client.get_currency_balance(account, "BTC")
    
    print(f"{account} LIBRE balance: {libre_balance_after}")
    print(f"{account} BTC balance: {btc_balance_after}")
    
    # Summary
    print("\nLIBRE/BTC trading test summary:")
    print(f"Sell order (10 LIBRE @ 0.0000000055 BTC): {'Success' if sell_result['success'] else 'Failed'}")
    print(f"Buy order (10 LIBRE @ 0.0000000055 BTC): {'Success' if buy_result['success'] else 'Failed'}")
    
    print("\nLIBRE/BTC trading test completed!")

def main():
    # Define account to test
    account = "bentest3"
    
    # Initialize client
    print("Initializing LibreClient...")
    client = LibreClient(network='testnet', verbose=True)
    
    # Test LIBRE/BTC trading pair
    test_librebtc_pair(client, account)
    
    print("\nTesting completed!")

if __name__ == "__main__":
    main() 