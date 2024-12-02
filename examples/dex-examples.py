from pylibre import LibreClient
from pylibre.dex import DexClient
import json
import time

# Initialize clients
client = LibreClient("https://testnet.libre.org")
dex = DexClient(client)
from_account = "bentester"
base_symbol = "BTC"
quote_symbol = "LIBRE"

# Cancel all existing orders for the account
print("\n🧹 Cancelling all existing orders for account:", from_account)
order_book = dex.fetch_order_book(base_symbol=base_symbol, quote_symbol=quote_symbol)

# Cancel all bids
for bid in order_book["bids"]:
    if bid["account"] == from_account:
        print(f"🚫 Cancelling bid order with identifier: {bid['identifier']}")
        cancel_result = dex.cancel_order(
            account=from_account,
            order_id=bid['identifier'],
            base_symbol=base_symbol,
            quote_symbol=quote_symbol
        )
        print("✅ Bid cancelled" if cancel_result["success"] else "❌ Failed to cancel bid")

# Cancel all offers
for offer in order_book["offers"]:
    if offer["account"] == from_account:
        print(f"🚫 Cancelling sell order with identifier: {offer['identifier']}")
        cancel_result = dex.cancel_order(
            account=from_account,
            order_id=offer['identifier'],
            base_symbol=base_symbol,
            quote_symbol=quote_symbol
        )
        print("✅ Offer cancelled" if cancel_result["success"] else "❌ Failed to cancel offer")

# Parameters for the bid
from_account = "bentester"  # Account placing the bid
quantity = "100.00000000"  # Amount of LIBRE to buy
price = "0.0000000100"    # Price willing to pay in BTC per LIBRE
base_symbol = "BTC"       # What you're paying with
quote_symbol = "LIBRE"    # What you're buying

print(f"\n💸 Placing bid order for {quantity} {quote_symbol} at {price} {base_symbol} per {quote_symbol}")
result = dex.place_order(
    account=from_account,
    order_type="buy",
    quantity=quantity,
    price=price,
    base_symbol=base_symbol,
    quote_symbol=quote_symbol
)

print("Bid placement result:", json.dumps(result, indent=2))

if result["success"]:
    print("✅ Bid order placed successfully")
else:
    print("❌ Failed to place bid order:", result.get("error"))

print("\n🔍 Examining bid result structure:")
print(f"Result type: {type(result)}")
print("Result contents:")
print(json.dumps(result, indent=2))

# Parameters for the sell order
print("\n🔄 Now placing sell order...")
quantity_sell = "100.00000000"  # Amount of LIBRE to sell
price_sell = "0.0000000122"    # Price asking in BTC per LIBRE (1.22 SATS)

print(f"\n💰 Placing sell order for {quantity_sell} {quote_symbol} at {price_sell} {base_symbol} per {quote_symbol}")
result_sell = dex.place_order(
    account=from_account,
    order_type="sell",
    quantity=quantity_sell,
    price=price_sell,
    base_symbol=base_symbol,
    quote_symbol=quote_symbol
)

print("Sell order placement result:", json.dumps(result_sell, indent=2))

if result_sell["success"]:
    print("✅ Sell order placed successfully")
else:
    print("❌ Failed to place sell order:", result_sell.get("error"))

print("\n🔍 Examining sell result structure:")
print(f"Result type: {type(result_sell)}")
print("Result contents:")
print(json.dumps(result_sell, indent=2))

# Fetch the order book
print("\n📚 Fetching fresh order book...")
time.sleep(2)  # Add a 2-second delay to allow orders to propagate
order_book = dex.fetch_order_book(base_symbol=base_symbol, quote_symbol=quote_symbol)
print("Order book:", json.dumps(order_book, indent=2))

# Find and cancel the bid order
print("\n🔍 Looking for matching bid order...")
for bid in order_book["bids"]:
    # Convert prices to float for comparison
    order_price = float(bid["price"])
    our_price = float(price)
    if (bid["account"] == from_account and 
        abs(order_price - our_price) < 0.0000000001 and  # Using small epsilon for float comparison
        bid["type"] == "buy"):
        print(f"🚫 Cancelling bid order with identifier: {bid['identifier']}")
        cancel_result = dex.cancel_order(
            account=from_account,
            order_id=bid['identifier'],
            base_symbol=base_symbol,
            quote_symbol=quote_symbol
        )
        
        print("Cancel bid result:", json.dumps(cancel_result, indent=2))
        if cancel_result["success"]:
            print("✅ Bid order cancelled successfully")
        else:
            print("❌ Failed to cancel bid order:", cancel_result.get("error"))
        break
else:
    print("⚠️ No matching bid order found")

# Find and cancel the sell order
print("\n🔍 Looking for matching sell order...")
for offer in order_book["offers"]:
    # Convert prices to float for comparison
    order_price = float(offer["price"])
    our_price = float(price_sell)
    if (offer["account"] == from_account and 
        abs(order_price - our_price) < 0.0000000001 and  # Using small epsilon for float comparison
        offer["type"] == "sell"):
        print(f"🚫 Cancelling sell order with identifier: {offer['identifier']}")
        cancel_result = dex.cancel_order(
            account=from_account,
            order_id=offer['identifier'],
            base_symbol=base_symbol,
            quote_symbol=quote_symbol
        )
        
        print("Cancel sell result:", json.dumps(cancel_result, indent=2))
        if cancel_result["success"]:
            print("✅ Sell order cancelled successfully")
        else:
            print("❌ Failed to cancel sell order:", cancel_result.get("error"))
        break
else:
    print("⚠️ No matching sell order found")