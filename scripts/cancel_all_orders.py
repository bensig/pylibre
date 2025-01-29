#!/usr/bin/env python3
import sys
from pathlib import Path
import argparse
import time
from pylibre.dex import DexClient
from pylibre.client import LibreClient
from pylibre.manager.config_manager import ConfigManager

def cancel_order_direct(client: LibreClient, account: str, order_id: int, pair: str):
    """Cancel an order using DexClient."""
    try:
        base_symbol, quote_symbol = pair.split('/')
        dex = DexClient(client)
        result = dex.cancel_order(
            account=account,
            order_id=order_id,
            quote_symbol=quote_symbol,
            base_symbol=base_symbol
        )
        
        if not result.get("success"):
            print(f"❌ Failed to cancel order {order_id}: {result.get('error')}")
            return False
            
        print(f"✅ Cancelled order {order_id}")
        time.sleep(1)  # Small delay between cancellations
        return True
            
    except Exception as e:
        print(f"❌ Error cancelling order {order_id}: {e}")
        return False

def get_orders_to_cancel(client: LibreClient, account: str, pair: str) -> list:
    """Get list of orders that need to be cancelled."""
    try:
        base_symbol, quote_symbol = pair.split('/')
        dex = DexClient(client)
        
        order_book = dex.fetch_order_book(
            quote_symbol=quote_symbol,
            base_symbol=base_symbol
        )
        
        if not order_book:
            return []
            
        our_orders = (
            [order for order in order_book["bids"] if order["account"] == account] +
            [order for order in order_book["offers"] if order["account"] == account]
        )
        
        return our_orders
        
    except Exception as e:
        print(f"❌ Error fetching orders: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description='Cancel all orders for an account')
    parser.add_argument('--account', required=True, help='Account name')
    parser.add_argument('--pair', required=True, help='Trading pair (e.g., BTC/USDT)')
    parser.add_argument('--network', default='testnet', help='Network (testnet/mainnet)')
    parser.add_argument('--config', default='config/config.yaml', help='Path to config file')
    args = parser.parse_args()

    try:
        # Load configuration
        config_manager = ConfigManager(args.config)
        network_config = config_manager.get_network_config(args.network)
        
        if not network_config:
            print(f"❌ Network {args.network} not found in config")
            sys.exit(1)
            
        # Initialize client with network configuration
        client = LibreClient(api_url=network_config['api_url'])
        
        total_successful = 0
        total_failed = 0
        
        while True:
            # Get orders
            print(f"🔍 Fetching orders for {args.account} on {args.pair}...")
            orders = get_orders_to_cancel(client, args.account, args.pair)
            
            if not orders:
                print("✨ No more orders found")
                break
                
            print(f"Found {len(orders)} orders to cancel")
            
            # Cancel orders
            successful = 0
            failed = 0
            
            for order in orders:
                if cancel_order_direct(client, args.account, order['identifier'], args.pair):
                    successful += 1
                else:
                    failed += 1
            
            total_successful += successful
            total_failed += failed
            
            print(f"\n📊 Batch Summary:")
            print(f"✅ Successfully cancelled: {successful}")
            print(f"❌ Failed to cancel: {failed}")
        
        print(f"\n📊 Final Summary:")
        print(f"✅ Total successfully cancelled: {total_successful}")
        print(f"❌ Total failed to cancel: {total_failed}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()