import json
from .client import LibreClient
from decimal import Decimal, ROUND_DOWN

class DexClient:
    """Client for interacting with the DEX contract."""
    
    def __init__(self, client, contract="dex.libre"):
        """Initialize the DEX client.
        
        Args:
            client (LibreClient): The LibreClient instance to use for blockchain interactions
            contract (str): The DEX contract account name (default: "dex.libre")
        """
        self.client = client
        self.contract = contract

    def place_order(self, account, order_type, quantity, price, quote_symbol, base_symbol):
        """Place an order on the DEX (bid or offer).
        
        Args:
            account (str): The account placing the order
            order_type (str): Type of order ('buy' or 'sell')
            quantity (str): Amount to trade with precision (e.g. "1.00000000 BTC")
            price (str): Price per unit with precision (e.g. "50000.00000000 USDT")
            quote_symbol (str): Symbol being quoted (e.g. "USDT")
            base_symbol (str): Symbol being traded (e.g. "BTC")
            
        Returns:
            dict: Response containing success status and transaction ID or error
        """
        try:
            # Log full parameters for debugging
            print(f"Placing order with parameters:")
            print(f"Account: {account}")
            print(f"Order Type: {order_type}")
            print(f"Quantity: {quantity}")
            print(f"Price: {price}")
            print(f"Quote Symbol: {quote_symbol}")
            print(f"Base Symbol: {base_symbol}")
            print(f"Contract: {self.contract}")
            
            # Convert inputs to Decimal for precise calculation
            quantity_dec = Decimal(str(quantity))
            price_dec = Decimal(str(price))

            # Format with correct precision
            if order_type == 'buy':
                send_amount = quantity_dec * price_dec
                send_symbol = quote_symbol
                send_quantity = f"{send_amount:.8f}"
            else:  # sell
                send_amount = quantity_dec
                send_symbol = base_symbol
                precision = 4 if base_symbol == 'LIBRE' else 8
                send_quantity = f"{send_amount:.{precision}f}"

            # Define precision for base and quote symbols
            base_precision = 4 if base_symbol == 'LIBRE' else 8
            quote_precision = 8  # USDT and BTC use 8 decimal places

            # Create the action memo with correct precision for both symbols
            action = f"{order_type}:{quantity_dec:.{base_precision}f} {base_symbol}:{price_dec:.{quote_precision}f} {quote_symbol}"
            
            print(f"Placing {order_type} order: {quantity} {base_symbol} @ {price} {quote_symbol}")
            print(f"Transfer details:")
            print(f"  From: {account}")
            print(f"  To: {self.contract}")
            print(f"  Amount: {send_quantity} {send_symbol}")
            print(f"  Memo: {action}")
            
            result = self.client.transfer(
                from_account=account,
                to_account=self.contract,
                quantity=f"{send_quantity} {send_symbol}",
                memo=action
            )

            if result.get("success"):
                print(f"✅ Order placed successfully")
                return result.get("data", {}).get("transaction_id")
            else:
                print(f"❌ Order failed: {result.get('error', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"❌ Error placing order: {str(e)}")
            return None

    def fetch_order_book(self, quote_symbol: str, base_symbol: str) -> dict:
        """Fetch the complete order book for a trading pair."""
        try:
            pair = f"{base_symbol.lower()}{quote_symbol.lower()}"
            
            if self.client.verbose:
                print(f"Fetching order book for {base_symbol}/{quote_symbol}...")
            
            all_rows = []
            more = True
            last_key = ""
            
            while more:
                response = self.client.get_table_rows(
                    code=self.contract,
                    table="orderbook2",
                    scope=pair,
                    limit=1000,
                    lower_bound=last_key
                )
                
                if not response.get("success", False):
                    if self.client.verbose:
                        print(f"❌ Error fetching order book: {response.get('error', 'Unknown error')}")
                    return None
                
                rows = response.get("rows", [])
                all_rows.extend(rows)
                
                more = response.get("more", False)
                if more:
                    last_key = response.get("next_key", "")
            
            # Parse the rows into bids and offers
            bids = []
            offers = []
            
            for row in all_rows:
                try:
                    quantity = row["baseAsset"].split()[0]
                    
                    order = {
                        "identifier": int(row["identifier"]),
                        "account": row["account"],
                        "price": row["price"],
                        "quantity": quantity,
                        "type": row.get("type", "sell")
                    }
                    
                    if order["type"] == "buy":
                        bids.append(order)
                    else:
                        offers.append(order)
                except (KeyError, ValueError, IndexError) as e:
                    if self.client.verbose:
                        print(f"Warning: Skipping malformed order: {row}")
                    continue
            
            return {
                "bids": bids,
                "offers": offers
            }
            
        except Exception as e:
            if self.client.verbose:
                print(f"❌ Error in fetch_order_book: {str(e)}")
            return None

    def cancel_order(self, account: str, order_id: int, quote_symbol: str, base_symbol: str) -> dict:
        """Cancel an order."""
        try:
            pair = f"{base_symbol.lower()}{quote_symbol.lower()}"
            
            result = self.client.execute_action(
                contract=self.contract,
                action_name="cancelorder",
                data={
                    "orderIdentifier": order_id,
                    "pair": pair
                },
                actor=account
            )
            
            # Check the nested response structure
            if isinstance(result, dict):
                if result.get("success") and result.get("data", {}).get("transaction_id"):
                    return {"success": True, "tx_id": result["data"]["transaction_id"]}
                elif result.get("data", {}).get("transaction_id") is None:
                    return {"success": False, "error": "Transaction rejected"}
                else:
                    error = result.get("error", "Unknown error")
                    return {"success": False, "error": error}
            
            return {"success": False, "error": f"Invalid response type: {type(result)}"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cancel_all_orders(self, account, quote_symbol, base_symbol, contract="dex.libre"):
        """
        Cancel all orders for a specific trading pair.

        Args:
            account (str): The account cancelling the orders
            quote_symbol (str): Quote token symbol (e.g., USDT)
            base_symbol (str): Base token symbol (e.g., BTC)
            contract (str): DEX contract name (default: "dex.libre")

        Returns:
            dict: Summary of cancellation results
        """
        print(f"\n🔍 Fetching order book for {base_symbol}/{quote_symbol}...")
        order_book = self.fetch_order_book(quote_symbol=quote_symbol, base_symbol=base_symbol)

        results = []
        
        # Cancel all bids
        print("\nProcessing BIDS:")
        for bid in order_book["bids"]:
            if bid["account"] == account:
                print(f"🚫 Cancelling bid order with identifier: {bid['identifier']}")
                try:
                    cancel_result = self.cancel_order(
                        account=account,
                        order_id=bid['identifier'],
                        quote_symbol=quote_symbol,
                        base_symbol=base_symbol
                    )
                    success = cancel_result.get("success", False)
                    results.append({
                        "order_id": bid['identifier'],
                        "type": "bid",
                        "price": bid.get('price'),
                        "success": success,
                        "error": cancel_result.get("error") if not success else None
                    })
                    print("✅ Bid cancelled" if success else f"❌ Failed to cancel bid: {cancel_result.get('error')}")
                except Exception as e:
                    print(f"❌ Error cancelling bid: {str(e)}")
                    results.append({
                        "order_id": bid['identifier'],
                        "type": "bid",
                        "price": bid.get('price'),
                        "success": False,
                        "error": str(e)
                    })

        # Cancel all offers
        print("\nProcessing OFFERS:")
        for offer in order_book["offers"]:
            if offer["account"] == account:
                print(f"🚫 Cancelling sell order with identifier: {offer['identifier']}")
                try:
                    cancel_result = self.cancel_order(
                        account=account,
                        order_id=offer['identifier'],
                        quote_symbol=quote_symbol,
                        base_symbol=base_symbol
                    )
                    success = cancel_result.get("success", False)
                    results.append({
                        "order_id": offer['identifier'],
                        "type": "offer",
                        "price": offer.get('price'),
                        "success": success,
                        "error": cancel_result.get("error") if not success else None
                    })
                    print("✅ Offer cancelled" if success else f"❌ Failed to cancel offer: {cancel_result.get('error')}")
                except Exception as e:
                    print(f"❌ Error cancelling offer: {str(e)}")
                    results.append({
                        "order_id": offer['identifier'],
                        "type": "offer",
                        "price": offer.get('price'),
                        "success": False,
                        "error": str(e)
                    })

        # Summarize results
        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful
        
        summary = {
            "success": True,
            "summary": f"Cancelled {successful} orders, {failed} failed",
            "total_orders": len(results),
            "successful": successful,
            "failed": failed,
            "details": results
        }
        
        print(f"\n📊 Summary: {summary['summary']}")
        if failed > 0:
            print("\nFailed orders:")
            for result in results:
                if not result["success"]:
                    print(f"- Order {result['order_id']} ({result['type']}): {result['error']}")
        
        return summary
