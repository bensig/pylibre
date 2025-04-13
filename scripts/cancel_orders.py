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
    parser.add_argument('--network', default='mainnet', choices=['mainnet', 'testnet'], help='Network to use (mainnet or testnet)')
    
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
    print(f"🔍 Connecting to {args.api_url} ({args.network}) using config from config/config.yaml")
    client = LibreClient(
        api_url=args.api_url, 
        verbose=True,
        network=args.network,
        config_path='config/config.yaml'
    )
    
    # Verify account has a private key
    if not client.has_account_key(args.account):
        print(f"❌ ERROR: No private key found for account {args.account} in the configuration.")
        print(f"   Please ensure {args.account} is configured in config/config.yaml with a private key.")
        sys.exit(1)
    
    dex = DexClient(client)
    
    # Cancel all orders
    print(f"🔍 Cancelling all orders for {args.account} on {base_symbol}/{quote_symbol}...")
    
    # Fetch order book first to see what orders exist
    print("📊 Fetching order book...")
    order_book = dex.fetch_order_book(quote_symbol=quote_symbol, base_symbol=base_symbol)
    
    # Count user's orders
    user_bids = [bid for bid in order_book.get("bids", []) if bid.get("account") == args.account]
    user_asks = [ask for ask in order_book.get("offers", []) if ask.get("account") == args.account]
    print(f"📈 Found {len(user_bids)} bids and {len(user_asks)} asks for {args.account}")
    
    if not user_bids and not user_asks:
        print("✅ No orders to cancel!")
        sys.exit(0)
    
    # Set client and DexClient to verbose for detailed logs
    client.verbose = True
    
    # Cancel orders with timeout
    import threading
    import time
    
    result = None
    cancel_thread = None
    
    def cancel_with_timeout():
        global result
        result = dex.cancel_all_orders(
            account=args.account,
            quote_symbol=quote_symbol,
            base_symbol=base_symbol
        )
    
    # Start cancellation in a thread
    cancel_thread = threading.Thread(target=cancel_with_timeout)
    cancel_thread.daemon = True
    cancel_thread.start()
    
    # Wait with a progress indicator
    timeout = 60  # 60 seconds timeout
    start_time = time.time()
    while cancel_thread.is_alive() and time.time() - start_time < timeout:
        print("⏳ Cancelling orders... (press Ctrl+C to stop)", end="\r")
        time.sleep(1)
    
    print("")  # New line after progress indicator
    
    if cancel_thread.is_alive():
        print("⚠️ Cancellation taking too long! You may need to check the blockchain explorer")
        sys.exit(1)
    
    # Print result
    if result and result.get('success'):
        print(f"📊 Final Summary:")
        print(f"✅ Total successfully cancelled: {result.get('successful', 0)}")
        if result.get('failed', 0) > 0:
            print(f"❌ Total failed to cancel: {result.get('failed', 0)}")
            
            # Print details of failed cancellations
            print("\nFailed cancellations:")
            for detail in result.get('details', []):
                if not detail.get('success'):
                    order_id = detail.get('order_id')
                    order_type = detail.get('type')
                    error = detail.get('error', 'Unknown error')
                    print(f"  - Order {order_id} ({order_type}): {error}")
    else:
        error_msg = result.get('error', 'Unknown error') if result else "Cancellation failed or timed out"
        print(f"❌ Failed to cancel orders: {error_msg}")

if __name__ == "__main__":
    main() 