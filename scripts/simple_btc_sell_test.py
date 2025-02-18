#!/usr/bin/env python
"""
Simple test script for BTC sell orders with enhanced error handling
"""
import sys
import traceback
from decimal import Decimal
from pylibre.client import LibreClient
from pylibre.dex import DexClient

def main():
    """Main test function with robust error handling"""
    try:
        print("Initializing LibreClient...")
        client = LibreClient(verbose=True)
        
        print("Initializing DexClient...")
        dex = DexClient(client)
        
        print("\n=== Testing Direct BTC Transfer (CLI Equivalent) ===")
        # This is the exact equivalent of the CLI command that works
        transfer_result = client.transfer(
            from_account="bentester",
            to_account="dex.libre",
            quantity="0.00010000 BTC",
            memo="sell:0.00010000 BTC:80000.00000000 USDT",
            contract="btc.libre"
        )
        
        print(f"\nDirect BTC Transfer Result:")
        print(f"Success: {transfer_result.get('success', False)}")
        if transfer_result.get('success', False):
            print(f"Transaction ID: {transfer_result.get('data', {}).get('transaction_id', 'Unknown')}")
        else:
            print(f"Error: {transfer_result.get('error', 'Unknown error')}")
        
        # Wait for user input before continuing
        input("\nPress Enter to continue to the next test...\n")
        
        print("\n=== Testing BTC Sell Order via DexClient ===")
        sell_result = dex.place_order(
            account="bentester",
            order_type="sell",
            quantity="0.00010000",
            price="80000.00000000",
            quote_symbol="USDT",
            base_symbol="BTC"
        )
        
        print(f"\nBTC Sell Order Result: {sell_result}")
        
        return 0
    
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
        return 1
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
