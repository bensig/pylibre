#!/usr/bin/env python3
import sys
from decimal import Decimal
from pylibre.dex import DexClient
from pylibre.client import LibreClient
from pyntelope import Net, Transaction, Action, Authorization, Data, types
import argparse
import time

def cancel_order_direct(client: LibreClient, account: str, order_id: int, pair: str):
    """Cancel an order using DexClient."""
    try:
        dex = DexClient(client)
        result = dex.cancel_order(
            account=account,
            order_id=order_id,
            quote_symbol="USDT",
            base_symbol="BTC"
        )
        
        if not result.get("success"):
            if client.verbose:
                print(f"❌ Failed to cancel order {order_id}: {result.get('error')}")
            return False
            
        # Wait longer for the transaction to be processed
        time.sleep(2)  # Increased delay between cancellations
        return True
            
    except Exception as e:
        if client.verbose:
            print(f"❌ Error cancelling order {order_id}: {e}")
        return False

def get_orders_to_cancel(client: LibreClient, account: str, pair: str) -> list:
    """Get list of orders that need to be cancelled."""
    try:
        dex = DexClient(client)
        base_symbol = "BTC"
        quote_symbol = "USDT"
        
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
        if client.verbose:
            print(f"❌ Error fetching orders: {e}")
        return []

def cancel_all_orders(client: LibreClient, account: str, pair: str):
    """Cancel all orders for an account in a given pair."""
    orders_to_cancel = get_orders_to_cancel(client, account, pair)
    total = len(orders_to_cancel)
    
    if total == 0:
        print("✨ No orders found to cancel")
        return
    
    print(f"Found {total} orders to cancel")
    cancelled = 0
    failed = 0
    
    for order in orders_to_cancel:
        order_id = order["identifier"]
        max_retries = 3
        retry_count = 0
        success = False
        
        while retry_count < max_retries and not success:
            if retry_count > 0:
                print(f"\nRetry {retry_count} for order {order_id}...")
                time.sleep(2 * retry_count)  # Increase wait time with each retry
                
            success = cancel_order_direct(client, account, order_id, pair)
            retry_count += 1
            
        if success:
            cancelled += 1
        else:
            failed += 1
            
        if not client.verbose:
            print(f"\rCancelling orders: {cancelled}/{total} (Failed: {failed})", end="")
    
    print()  # New line after progress
        
    # Double-check remaining orders with a longer delay
    time.sleep(3)  # Wait for last transactions to process
    remaining_orders = get_orders_to_cancel(client, account, pair)
    remaining = len(remaining_orders)
    if remaining > 0:
        print(f"\n⚠️  {remaining} orders still remain:")
        print("Remaining order IDs:", [order["identifier"] for order in remaining_orders])
    else:
        print(f"\n✅ Successfully cancelled all {cancelled} orders")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument('account', help='Account name')
    parser.add_argument('pair', help='Trading pair (e.g., btcusdt)')
    parser.add_argument('api_url', help='API URL')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    args = parser.parse_args()
    
    client = LibreClient(args.api_url, verbose=args.verbose)
    cancel_all_orders(client, args.account, args.pair)

if __name__ == "__main__":
    main()