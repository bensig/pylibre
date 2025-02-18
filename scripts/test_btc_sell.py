#!/usr/bin/env python
"""
Test script for BTC sell orders
"""
from pylibre.client import LibreClient
from pylibre.dex import DexClient

def test_btc_sell_order():
    """Test placing a BTC sell order"""
    print("Initializing LibreClient...")
    client = LibreClient(verbose=True)
    
    print("Initializing DexClient...")
    dex = DexClient(client)
    
    print("\n=== Testing BTC sell order ===")
    
    # Use the exact same parameters as the successful CLI command
    account = "dextrader"
    order_type = "sell"
    quantity = "0.00010000"
    price = "80000.00000000"
    quote_symbol = "USDT"
    base_symbol = "BTC"
    
    print(f"Placing {order_type} order: {quantity} {base_symbol} @ {price} {quote_symbol}")
    
    result = dex.place_order(
        account=account,
        order_type=order_type,
        quantity=quantity,
        price=price,
        quote_symbol=quote_symbol,
        base_symbol=base_symbol
    )
    
    if result:
        print(f"✅ Success! Transaction ID: {result}")
    else:
        print("❌ Failed to place order")

if __name__ == "__main__":
    test_btc_sell_order()
