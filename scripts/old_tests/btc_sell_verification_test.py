#!/usr/bin/env python3
"""
Focused test script to verify BTC sell order functionality.
This test specifically focuses on the issue we fixed with BTC sell orders.
"""

import sys
import os
import time
import logging
from decimal import Decimal, getcontext

# Set higher precision for decimal calculations
getcontext().prec = 28

# Add the parent directory to the path so we can import the pylibre module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.pylibre.client import LibreClient
from src.pylibre.dex import DexClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BTCSellTest")

def test_cli_equivalent():
    """Test the exact CLI equivalent in Python."""
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
    
    print(f"CLI equivalent result: {result}")
    return result, client

def test_direct_transfer(client):
    """Test direct BTC transfer with sell order memo."""
    print("\n=== Testing Direct BTC Transfer with Sell Order Memo ===")
    
    result = client.transfer(
        from_account="bentester",
        to_account="dex.libre",
        quantity="0.00010000 BTC",
        memo="sell:0.00010000 BTC:80000.00000000 USDT",
        contract="btc.libre"
    )
    
    print(f"Direct transfer result: {result}")
    return result

def test_dex_sell_order(client):
    """Test placing a BTC sell order via DexClient."""
    print("\n=== Testing BTC Sell Order via DexClient ===")
    
    dex = DexClient(client)
    
    result = dex.place_order(
        account="bentester",
        order_type="sell",
        quantity="0.00010000",
        price="80000.00000000",
        quote_symbol="USDT",
        base_symbol="BTC"
    )
    
    print(f"DexClient sell order result: {result}")
    return result, dex

def test_dex_buy_order(client, dex):
    """Test placing a BTC buy order via DexClient for comparison."""
    print("\n=== Testing BTC Buy Order via DexClient ===")
    
    result = dex.place_order(
        account="bentester",
        order_type="buy",
        quantity="0.00010000",
        price="80000.00000000",
        quote_symbol="USDT",
        base_symbol="BTC"
    )
    
    print(f"DexClient buy order result: {result}")
    return result

def main():
    """Run the BTC sell verification test."""
    print("\n" + "=" * 80)
    print("BTC SELL ORDER VERIFICATION TEST")
    print("=" * 80 + "\n")
    
    try:
        # Test CLI equivalent
        cli_result, client = test_cli_equivalent()
        
        # Wait a bit between tests
        time.sleep(2)
        
        # Test direct transfer
        transfer_result = test_direct_transfer(client)
        
        # Wait a bit between tests
        time.sleep(2)
        
        # Test DexClient sell order
        dex_sell_result, dex = test_dex_sell_order(client)
        
        # Wait a bit between tests
        time.sleep(2)
        
        # Test DexClient buy order for comparison
        dex_buy_result = test_dex_buy_order(client, dex)
        
        # Summarize results
        print("\n" + "=" * 80)
        print("TEST RESULTS SUMMARY")
        print("=" * 80)
        
        print(f"\nCLI Equivalent: {'✅ Success' if cli_result.get('success', False) else '❌ Failed'}")
        print(f"Direct Transfer: {'✅ Success' if transfer_result.get('success', False) else '❌ Failed'}")
        print(f"DexClient Sell: {'✅ Success' if dex_sell_result else '❌ Failed'}")
        print(f"DexClient Buy: {'✅ Success' if dex_buy_result else '❌ Failed'}")
        
        print("\n" + "=" * 80)
        print("VERIFICATION TEST COMPLETED")
        print("=" * 80 + "\n")
        
        return 0
    except Exception as e:
        logger.error(f"Error in verification test: {str(e)}", exc_info=True)
        print(f"\n❌ VERIFICATION TEST FAILED: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
