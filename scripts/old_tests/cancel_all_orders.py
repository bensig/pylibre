#!/usr/bin/env python3
import sys
from pathlib import Path
import argparse
import time
from pylibre.dex import DexClient
from pylibre.client import LibreClient
from pylibre.manager.config_manager import ConfigManager

def cancel_order_direct(client: LibreClient, account: str, order_id: int, base_symbol: str, quote_symbol: str):
    """Cancel an order using DexClient."""
    try:
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

def parse_trading_pair(pair: str) -> tuple:
    """Parse trading pair string into base and quote symbols."""
    if '/' in pair:
        # Format: LIBRE/BTC
        return pair.split('/')
    elif len(pair) >= 7:  
        # Format: LIBREBTC - assume LIBRE is base and BTC is quote
        if pair.startswith('LIBRE'):
            return 'LIBRE', pair[5:]
        elif pair.endswith('LIBRE'):
            return 'LIBRE', pair[:-5]
        else:
            # Try to identify common symbols
            for symbol in ['BTC', 'ETH', 'USDT', 'USDC']:
                if pair.startswith(symbol):
                    return symbol, pair[len(symbol):]
                elif pair.endswith(symbol):
                    return pair[:-len(symbol)], symbol
    
    # If we can't parse it, raise an error
    raise ValueError(f"Could not parse trading pair: {pair}. Use format like 'LIBRE/BTC' or 'LIBREBTC'")

def get_orders_to_cancel(client: LibreClient, account: str, base_symbol: str, quote_symbol: str) -> list:
    """Get list of orders that need to be cancelled."""
    try:
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
    parser.add_argument('--pair', required=True, help='Trading pair (e.g., LIBRE/BTC or LIBREBTC)')
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
        
        # Parse the trading pair
        try:
            base_symbol, quote_symbol = parse_trading_pair(args.pair)
            print(f"🔍 Using trading pair: {base_symbol}/{quote_symbol}")
        except ValueError as e:
            print(f"❌ {str(e)}")
            sys.exit(1)
        
        total_successful = 0
        total_failed = 0
        
        while True:
            # Get orders
            print(f"🔍 Fetching orders for {args.account} on {base_symbol}/{quote_symbol}...")
            orders = get_orders_to_cancel(client, args.account, base_symbol, quote_symbol)
            
            if not orders:
                print("✨ No more orders found")
                break
                
            print(f"Found {len(orders)} orders to cancel")
            
            # Cancel orders
            successful = 0
            failed = 0
            
            for order in orders:
                if cancel_order_direct(client, args.account, order['identifier'], base_symbol, quote_symbol):
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