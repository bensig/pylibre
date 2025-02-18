#!/usr/bin/env python3
"""
Script to cancel all orders for a specific account and trading pair.
"""

import sys
import os
import argparse

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.pylibre import LibreClient
from src.pylibre.dex import DexClient

def main():
    """Main function to cancel all orders."""
    parser = argparse.ArgumentParser(description='Cancel all orders for an account')
    
    # Required arguments
    parser.add_argument('--account', required=True, help='Account to cancel orders for')
    
    # Trading pair arguments (either --pair or --base/--quote)
    pair_group = parser.add_mutually_exclusive_group(required=True)
    pair_group.add_argument('--pair', help='Trading pair (e.g., LIBREBTC)')
    base_quote_group = pair_group.add_argument_group()
    base_quote_group.add_argument('--base', help='Base symbol (e.g., LIBRE)')
    base_quote_group.add_argument('--quote', help='Quote symbol (e.g., BTC)')
    
    # Optional arguments
    parser.add_argument('--api-url', default='https://testnet.libre.org', help='API endpoint URL')
    
    args = parser.parse_args()
    
    # Parse trading pair
    base_symbol = None
    quote_symbol = None
    
    if args.pair:
        # Common trading pairs
        if args.pair.upper() == 'LIBREBTC':
            base_symbol = 'LIBRE'
            quote_symbol = 'BTC'
        elif args.pair.upper() == 'LIBREUSDT':
            base_symbol = 'LIBRE'
            quote_symbol = 'USDT'
        elif args.pair.upper() == 'BTCUSDT':
            base_symbol = 'BTC'
            quote_symbol = 'USDT'
        else:
            # Try to split the pair (assuming format is BASEQOUTE)
            for i in range(1, len(args.pair)):
                potential_base = args.pair[:i].upper()
                potential_quote = args.pair[i:].upper()
                if potential_base in ['LIBRE', 'BTC', 'ETH'] and potential_quote in ['BTC', 'USDT', 'ETH']:
                    base_symbol = potential_base
                    quote_symbol = potential_quote
                    break
            
            if not base_symbol or not quote_symbol:
                print(f"Error: Could not parse trading pair '{args.pair}'")
                print("Please use format like LIBREBTC or specify --base and --quote separately")
                sys.exit(1)
    else:
        if not args.base or not args.quote:
            print("Error: Both --base and --quote must be specified if --pair is not used")
            sys.exit(1)
        base_symbol = args.base.upper()
        quote_symbol = args.quote.upper()
    
    print(f"🔍 Using trading pair: {base_symbol}/{quote_symbol}")
    
    # Initialize client
    client = LibreClient(api_url=args.api_url, verbose=True)
    dex = DexClient(client)
    
    # Cancel all orders
    print(f"🔍 Cancelling all orders for {args.account} on {base_symbol}/{quote_symbol}...")
    
    # Cancel orders
    result = dex.cancel_all_orders(
        account=args.account,
        quote_symbol=quote_symbol,
        base_symbol=base_symbol
    )
    
    # Print result
    if result.get('success'):
        print(f"📊 Final Summary:")
        print(f"✅ Total successfully cancelled: {result.get('successful', 0)}")
        if result.get('failed', 0) > 0:
            print(f"❌ Total failed to cancel: {result.get('failed', 0)}")
    else:
        print(f"❌ Failed to cancel orders: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main() 