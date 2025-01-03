#!/usr/bin/env python3
import sys
from decimal import Decimal
from pylibre.dex import DexClient
from pylibre.client import LibreClient
from pyntelope import Net, Transaction, Action, Authorization, Data, types

def cancel_order_direct(api_url: str, account: str, order_id: int, pair: str):
    """Cancel an order using LibreClient."""
    try:
        # Initialize LibreClient
        client = LibreClient(api_url)
        client.load_account_keys()  # This will load keys from .env.testnet by default
        
        # Prepare action data
        action_data = {
            "orderIdentifier": order_id,
            "pair": pair
        }
        
        # Execute the transaction
        result = client.push_action(
            contract="dex.libre",
            action="cancelorder",
            data=action_data,
            account=account
        )
        
        if result["success"]:
            print(f"✅ Successfully cancelled order {order_id}")
            return True
        else:
            print(f"❌ Error cancelling order {order_id}: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Error cancelling order {order_id}: {str(e)}")
        return False

def cancel_all_orders(account: str, trading_pair: str, api_url: str = "https://testnet.libre.org"):
    """Cancel all orders for a specific account and trading pair."""
    try:
        # Initialize LibreClient
        client = LibreClient(api_url=api_url)
        
        # Initialize DexClient
        dex = DexClient(client)
        
        # Get the order book
        pair = trading_pair.lower()
        print(f"\n🔍 Fetching orders for {pair}...")
        
        # Get table rows directly
        rows = client.get_table_rows(
            code="dex.libre",
            table="orderbook2",
            scope=pair,
            limit=1000
        )
        
        # Filter orders for our account
        our_orders = [row for row in rows if row["account"] == account]
        
        if not our_orders:
            print(f"No active orders found for {account} in {pair}")
            return
        
        print(f"\nFound {len(our_orders)} orders to cancel")
        
        # Cancel each order
        successful = 0
        failed = 0
        
        for order in our_orders:
            order_id = order["identifier"]
            if cancel_order_direct(api_url, account, order_id, pair):
                successful += 1
            else:
                failed += 1
                
        # Print summary
        print(f"\n📊 Summary:")
        print(f"Successfully cancelled: {successful}")
        print(f"Failed to cancel: {failed}")
        print(f"Total orders processed: {len(our_orders)}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) not in [3, 4]:
        print("Usage: python cancel_all_orders.py <account> <trading_pair> [api_url]")
        print("Example: python cancel_all_orders.py bentester btcusdt")
        print("Example with custom API: python cancel_all_orders.py bentester btcusdt https://lb.libre.org")
        sys.exit(1)
    
    account = sys.argv[1]
    trading_pair = sys.argv[2]
    api_url = sys.argv[3] if len(sys.argv) > 3 else "https://testnet.libre.org"
    
    cancel_all_orders(account, trading_pair, api_url)