from pylibre import LibreClient
from pylibre.dex import DexClient
import json

# Initialize clients
client = LibreClient("https://testnet.libre.org")
dex = DexClient(client)

# Parameters for the bid
from_account = "bentester"  # Account placing the bid
quantity = "10.00000000"  # Amount of USDT to spend (without symbol)
price = "30000.00000000"  # Price willing to pay per BTC
base_symbol = "USDT"
quote_symbol = "BTC"

print(f"\n💸 Placing bid order for {quantity} {base_symbol} at {price} USDT per BTC")
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