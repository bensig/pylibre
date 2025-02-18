#!/usr/bin/env python3
"""
Test script for LIBRE/BTC trading pair respecting minimum values from config.
This script ensures that orders meet the minimum requirements specified in the config.
"""

import sys
import os
import time
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

def place_sell_order(client, account, quantity, price, base_symbol, quote_symbol, dex_contract, min_value):
    """Place a sell order for a specific trading pair respecting minimum values."""
    print(f"\nPlacing sell order: {quantity} {base_symbol} @ {price} {quote_symbol}")
    
    # Check if the order meets minimum requirements
    quantity_dec = Decimal(str(quantity))
    if quantity_dec < Decimal(str(min_value)):
        print(f"❌ Order quantity {quantity} {base_symbol} is below minimum of {min_value} {base_symbol}")
        return False
    
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

def place_buy_order(client, account, quantity, price, base_symbol, quote_symbol, dex_contract, min_value):
    """Place a buy order for a specific trading pair respecting minimum values."""
    print(f"\nPlacing buy order: {quantity} {base_symbol} @ {price} {quote_symbol}")
    
    # Calculate the amount of quote currency to send
    quote_amount = Decimal(str(quantity)) * Decimal(str(price))
    quote_amount_str = f"{quote_amount:.8f}"
    
    # Check if the order meets minimum requirements
    if quote_amount < Decimal(str(min_value)):
        print(f"❌ Order value {quote_amount_str} {quote_symbol} is below minimum of {min_value} {quote_symbol}")
        return False
    
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
    dex_contract = "dex.libre"
    
    print(f"\n{'='*50}")
    print(f"Testing LIBRE/BTC Trading Pair with {account}")
    print(f"{'='*50}")
    
    # Check initial balances
    print("\nChecking initial balances...")
    base_contract = "eosio.token" if base_symbol == "LIBRE" else f"{base_symbol.lower()}.libre"
    quote_contract = f"{quote_symbol.lower()}.libre"
    
    print(f"Using contract: {base_contract} for symbol: {base_symbol}")
    print(f"Using contract: {quote_contract} for symbol: {quote_symbol}")
    
    base_balance = client.get_currency_balance(account, base_symbol)
    quote_balance = client.get_currency_balance(account, quote_symbol)
    
    print(f"{account} {base_symbol} balance: {base_balance}")
    print(f"{account} {quote_symbol} balance: {quote_balance}")
    
    # Test 1: Sell order with minimum LIBRE value
    print(f"\nTest 1: Sell order with minimum LIBRE value ({min_libre_value} LIBRE)")
    sell_quantity = f"{min_libre_value:.4f}"
    sell_price = "0.00000001"  # 1 satoshi per LIBRE
    
    sell_success = place_sell_order(
        client=client,
        account=account,
        quantity=sell_quantity,
        price=sell_price,
        base_symbol=base_symbol,
        quote_symbol=quote_symbol,
        dex_contract=dex_contract,
        min_value=min_libre_value
    )
    
    # Wait a moment
    time.sleep(2)
    
    # Test 2: Buy order with minimum BTC value
    # Calculate LIBRE quantity based on minimum BTC value
    btc_price = Decimal("0.00000001")  # 1 satoshi per LIBRE
    libre_quantity = Decimal(str(min_btc_value)) / btc_price
    
    print(f"\nTest 2: Buy order with minimum BTC value ({min_btc_value} BTC)")
    buy_quantity = f"{libre_quantity:.4f}"
    buy_price = "0.00000001"  # 1 satoshi per LIBRE
    
    buy_success = place_buy_order(
        client=client,
        account=account,
        quantity=buy_quantity,
        price=buy_price,
        base_symbol=base_symbol,
        quote_symbol=quote_symbol,
        dex_contract=dex_contract,
        min_value=min_btc_value
    )
    
    # Check final balances
    print("\nChecking final balances...")
    base_balance_after = client.get_currency_balance(account, base_symbol)
    quote_balance_after = client.get_currency_balance(account, quote_symbol)
    
    print(f"{account} {base_symbol} balance: {base_balance_after}")
    print(f"{account} {quote_symbol} balance: {quote_balance_after}")
    
    # Print summary
    print("\nLIBRE/BTC trading test summary:")
    print(f"Sell order ({sell_quantity} LIBRE @ {sell_price} BTC): {'Success' if sell_success else 'Failed'}")
    print(f"Buy order ({buy_quantity} LIBRE @ {buy_price} BTC): {'Success' if buy_success else 'Failed'}")
    
    print("\nLIBRE/BTC trading test completed!")

if __name__ == "__main__":
    main() 