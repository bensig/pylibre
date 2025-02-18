#!/usr/bin/env python3
"""
Test script to directly examine the raw API response when placing LIBRE/BTC buy orders.
This script bypasses the LibreClient's error handling to see the raw response.
"""

import sys
import os
import time
import json
import requests
from decimal import Decimal

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pylibre.client import LibreClient

def get_raw_api_response(client, account, quantity, price, base_symbol, quote_symbol, dex_contract):
    """Get the raw API response when placing a buy order."""
    print(f"\nPreparing buy order: {quantity} {base_symbol} @ {price} {quote_symbol}")
    
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
        # Get the private key for the account
        private_key = client.get_private_key(account)
        if not private_key:
            print(f"❌ No private key found for account: {account}")
            return None
        
        # Prepare the action data
        action_data = {
            "from": account,
            "to": dex_contract,
            "quantity": f"{quote_amount_str} {quote_symbol}",
            "memo": memo
        }
        
        # Prepare the action
        action = {
            "account": quote_contract,
            "name": "transfer",
            "authorization": [{"actor": account, "permission": "active"}],
            "data": action_data
        }
        
        # Get blockchain info
        info_response = requests.post(f"{client.api_url}/v1/chain/get_info")
        info = info_response.json()
        
        # Print raw blockchain info
        print("\nBlockchain Info:")
        print(json.dumps(info, indent=2))
        
        # Prepare transaction
        transaction = {
            "expiration": (time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(time.time() + 60))),
            "ref_block_num": info["last_irreversible_block_num"] & 0xFFFF,
            "ref_block_prefix": info["last_irreversible_block_id"],
            "max_net_usage_words": 0,
            "max_cpu_usage_ms": 0,
            "delay_sec": 0,
            "context_free_actions": [],
            "actions": [action],
            "transaction_extensions": [],
            "signatures": [],
            "context_free_data": []
        }
        
        # Print transaction details
        print("\nTransaction Details:")
        print(json.dumps(transaction, indent=2))
        
        # Try to push the transaction directly
        print("\nPushing transaction directly to API...")
        push_response = requests.post(
            f"{client.api_url}/v1/chain/push_transaction",
            json=transaction
        )
        
        # Print raw API response
        print("\nRaw API Response:")
        print(f"Status Code: {push_response.status_code}")
        try:
            response_json = push_response.json()
            print(json.dumps(response_json, indent=2))
            return response_json
        except:
            print(f"Raw Response Text: {push_response.text}")
            return push_response.text
        
    except Exception as e:
        print(f"❌ Error in API request: {str(e)}")
        return None

def main():
    # Initialize client
    print("Initializing LibreClient...")
    client = LibreClient(network='testnet', verbose=True)
    
    # Define account to test
    account = "bentest3"
    
    # Define trading pair parameters
    base_symbol = "LIBRE"
    quote_symbol = "BTC"
    dex_contract = "dex.libre"
    
    print(f"\n{'='*50}")
    print(f"Testing LIBRE/BTC Buy Order with Raw API Response")
    print(f"{'='*50}")
    
    # Check initial balances
    print("\nChecking initial balances...")
    base_balance = client.get_currency_balance(account, base_symbol)
    quote_balance = client.get_currency_balance(account, quote_symbol)
    
    print(f"{account} {base_symbol} balance: {base_balance}")
    print(f"{account} {quote_symbol} balance: {quote_balance}")
    
    # Test a buy order with minimum BTC value
    quantity = "1000.0000"  # LIBRE
    price = "0.00000010"    # BTC per LIBRE (0.00010000 BTC total)
    
    print(f"\nTesting buy order: {quantity} {base_symbol} @ {price} {quote_symbol}")
    print(f"Total value: {Decimal(quantity) * Decimal(price):.8f} {quote_symbol}")
    
    # Get raw API response
    response = get_raw_api_response(
        client=client,
        account=account,
        quantity=quantity,
        price=price,
        base_symbol=base_symbol,
        quote_symbol=quote_symbol,
        dex_contract=dex_contract
    )
    
    # Print summary
    print("\nAPI Test Summary:")
    if response:
        print("Raw API response captured successfully")
    else:
        print("Failed to capture raw API response")
    
    print("\nTesting completed!")

if __name__ == "__main__":
    main() 