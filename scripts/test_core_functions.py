#!/usr/bin/env python
"""
Test script for core functions in client.py and dex.py
"""
import json
import time
from decimal import Decimal
from pylibre.client import LibreClient
from pylibre.dex import DexClient

def test_client_transfer():
    """Test the transfer method in LibreClient"""
    print("\n=== Testing LibreClient.transfer ===")
    client = LibreClient(verbose=True)
    
    # Test BTC transfer
    print("\n--- Testing BTC transfer ---")
    btc_result = client.transfer(
        from_account="bentester",
        to_account="dex.libre",
        quantity="0.00010000 BTC",
        memo="test transfer",
        contract="btc.libre"
    )
    print(f"BTC transfer result: {json.dumps(btc_result, indent=2)}")
    
    # Test USDT transfer
    print("\n--- Testing USDT transfer ---")
    usdt_result = client.transfer(
        from_account="bentester",
        to_account="dex.libre",
        quantity="0.10000000 USDT",
        memo="test transfer",
        contract="usdt.libre"
    )
    print(f"USDT transfer result: {json.dumps(usdt_result, indent=2)}")
    
    return btc_result, usdt_result

def test_raw_blockchain_call():
    """Test raw blockchain API call to understand response format"""
    print("\n=== Testing Raw Blockchain Call ===")
    client = LibreClient(verbose=True)
    
    # Get the raw API response for a BTC transfer
    print("\n--- Testing Raw BTC Transfer API Call ---")
    try:
        # Prepare action data
        data = {
            "from": "bentester",
            "to": "dex.libre",
            "quantity": "0.00010000 BTC",
            "memo": "test raw call"
        }
        
        # Get the transaction data
        trx = client.get_signed_transaction(
            account="bentester",
            contract="btc.libre",
            action="transfer",
            data=data
        )
        
        # Push the transaction directly
        response = client.push_transaction(trx)
        print(f"Raw API response: {json.dumps(response, indent=2)}")
        
        return response
    except Exception as e:
        print(f"Error in raw blockchain call: {str(e)}")
        return None

def test_dex_place_order():
    """Test the place_order method in DexClient"""
    print("\n=== Testing DexClient.place_order ===")
    client = LibreClient(verbose=True)
    dex = DexClient(client)
    
    # Test BTC buy order
    print("\n--- Testing BTC buy order ---")
    buy_result = dex.place_order(
        account="bentester",
        order_type="buy",
        quantity="0.00010000",
        price="80000.00000000",
        quote_symbol="USDT",
        base_symbol="BTC"
    )
    print(f"BTC buy order result: {buy_result}")
    
    # Wait a bit before placing the sell order
    time.sleep(2)
    
    # Test BTC sell order
    print("\n--- Testing BTC sell order ---")
    sell_result = dex.place_order(
        account="bentester",
        order_type="sell",
        quantity="0.00010000",
        price="80000.00000000",
        quote_symbol="USDT",
        base_symbol="BTC"
    )
    print(f"BTC sell order result: {sell_result}")
    
    return buy_result, sell_result

def test_cli_equivalent():
    """Test the exact CLI equivalent in Python"""
    print("\n=== Testing CLI Equivalent in Python ===")
    client = LibreClient(verbose=True)
    
    # This is the exact equivalent of:
    # test.sh push action btc.libre transfer '["bentester", "dex.libre", "0.00010000 BTC", "sell:0.00010000 BTC:80000.00000000 USDT"]' -p bentester@active
    
    data = {
        "from": "bentester",
        "to": "dex.libre",
        "quantity": "0.00010000 BTC",
        "memo": "sell:0.00010000 BTC:80000.00000000 USDT"
    }
    
    result = client.execute_action(
        account="bentester",
        contract="btc.libre",
        action="transfer",
        data=data
    )
    
    print(f"CLI equivalent result: {json.dumps(result, indent=2)}")
    return result

def compare_results(cli_result, python_result):
    """Compare CLI and Python results"""
    print("\n=== Comparing CLI and Python Results ===")
    
    # Print the results side by side
    print(f"CLI Result Success: {cli_result.get('success', False)}")
    print(f"Python Result Success: {python_result.get('success', False)}")
    
    # Check for differences in the response structure
    cli_keys = set(cli_result.keys())
    python_keys = set(python_result.keys())
    
    print(f"\nCLI Result Keys: {cli_keys}")
    print(f"Python Result Keys: {python_keys}")
    
    # Check for differences in error messages if present
    if not cli_result.get('success', False):
        print(f"CLI Error: {cli_result.get('error', 'No error')}")
    
    if not python_result.get('success', False):
        print(f"Python Error: {python_result.get('error', 'No error')}")

if __name__ == "__main__":
    print("Starting core function tests...")
    
    # Test the client transfer function
    btc_transfer, usdt_transfer = test_client_transfer()
    
    # Test raw blockchain call
    raw_result = test_raw_blockchain_call()
    
    # Test the dex place_order function
    buy_order, sell_order = test_dex_place_order()
    
    # Test CLI equivalent in Python
    cli_equiv = test_cli_equivalent()
    
    # Compare CLI and Python results if both are available
    if cli_equiv and raw_result:
        compare_results(cli_equiv, raw_result)
    
    print("\nAll tests completed.")
