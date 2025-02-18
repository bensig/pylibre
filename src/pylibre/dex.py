import json
from .client import LibreClient
from decimal import Decimal, ROUND_DOWN

class DexClient:
    def __init__(self, client: LibreClient):
        self.client = client
        self.verbose = client.verbose  # Pass through verbose flag from LibreClient

    def place_order(self, account: str, order_type: str, quantity: str, price: str, quote_symbol: str, base_symbol: str) -> dict:
        """Place a new order on the DEX."""
        try:
            if self.client.verbose:
                print(f"\nPlacing {order_type} order: {quantity} {base_symbol} @ {price} {quote_symbol}")

            # Format price to 8 decimal places for BTC pairs, 4 for others
            price_decimal = Decimal(str(price))
            if quote_symbol == "BTC":
                price_str = f"{price_decimal:.8f}"
            else:
                price_str = f"{price_decimal:.4f}"

            # Calculate total cost
            quantity_decimal = Decimal(str(quantity))
            total_cost = quantity_decimal * price_decimal

            # Get contract names
            base_contract = self.get_contract_for_symbol(base_symbol)
            quote_contract = self.get_contract_for_symbol(quote_symbol)

            if not base_contract or not quote_contract:
                return {"success": False, "error": f"Invalid symbol pair {base_symbol}/{quote_symbol}"}

            if self.client.verbose:
                print(f"\nTransfer Details:")
                print(f"From: {account}")
                print(f"To: dex.libre")

            # For buy orders, transfer quote currency (e.g. USDT)
            # For sell orders, transfer base currency (e.g. BTC)
            if order_type == "buy":
                amount = total_cost
                contract = quote_contract
                memo = f"buy:{quantity} {base_symbol}:{price_str} {quote_symbol}"
                
                if self.client.verbose:
                    print(f"Amount: {amount:.8f} {quote_symbol}")
                    print(f"Contract: {contract}")
                    print(f"Memo: {memo}")
                    
            else:  # sell
                amount = quantity_decimal
                contract = base_contract
                memo = f"sell:{quantity} {base_symbol}:{price_str} {quote_symbol}"
                
                if self.client.verbose:
                    print(f"Amount: {amount:.8f} {base_symbol}")
                    print(f"Contract: {contract}")
                    print(f"Memo: {memo}")

            # Execute the transfer
            result = self.client.transfer(
                account,
                "dex.libre",
                str(amount),
                contract,
                memo
            )

            if result.get("success", False):
                return {"success": True}
            else:
                error = result.get("error", "Unknown error")
                if self.client.verbose:
                    print(f"❌ Order failed: {error}")
                return {"success": False, "error": error}

        except Exception as e:
            if self.client.verbose:
                print(f"❌ Error placing order: {str(e)}")
            return {"success": False, "error": str(e)}

    def fetch_order_book(self, quote_symbol: str, base_symbol: str) -> dict:
        """Fetch the complete order book for a trading pair."""
        try:
            pair = f"{base_symbol.lower()}{quote_symbol.lower()}"
            
            if self.client.verbose:
                print(f"Fetching order book for {base_symbol}/{quote_symbol}...")
            
            # Get all orders in one request with a high limit
            response = self.client.get_table_rows(
                code="dex.libre",
                table="orderbook2",
                scope=pair,
                limit=1000  # Maximum limit
            )
            
            if not response.get("success", False):
                error = response.get("error", "Unknown error")
                if self.client.verbose:
                    print(f"❌ Error fetching order book: {error}")
                return {"bids": [], "offers": [], "error": error}
            
            rows = response.get("rows", [])
            bids = []
            offers = []
            
            for row in rows:
                try:
                    # Extract the quantity from baseAsset (e.g. "100.00000000 LIBRE")
                    quantity = row["baseAsset"].split()[0]
                    
                    order = {
                        "identifier": str(row["identifier"]),  # Convert to string to match example
                        "account": row["account"],
                        "price": row["price"],
                        "quantity": quantity,
                        "type": row.get("type", "sell")  # Default to sell if not specified
                    }
                    
                    if order["type"] == "buy":
                        bids.append(order)
                    else:
                        offers.append(order)
                        
                except (KeyError, ValueError, IndexError) as e:
                    if self.client.verbose:
                        print(f"⚠️ Error parsing order row: {e}")
                    continue
            
            # Sort bids and offers by price
            bids.sort(key=lambda x: float(x["price"]), reverse=True)  # Highest price first
            offers.sort(key=lambda x: float(x["price"]))  # Lowest price first
            
            if self.client.verbose:
                print(f"Found {len(bids)} bids and {len(offers)} offers")
            
            return {
                "bids": bids,
                "offers": offers
            }
            
        except Exception as e:
            if self.client.verbose:
                print(f"❌ Error in fetch_order_book: {str(e)}")
            return {"bids": [], "offers": []}

    def cancel_order(self, account: str, order_id: int, quote_symbol: str, base_symbol: str) -> dict:
        """Cancel an order."""
        try:
            pair = f"{base_symbol.lower()}{quote_symbol.lower()}"
            
            result = self.client.execute_action(
                contract="dex.libre",
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

    def get_contract_for_symbol(self, symbol: str) -> str:
        """Get contract name for a given symbol."""
        contract_map = {
            'BTC': 'btc.libre',
            'USDT': 'usdt.libre',
            'LIBRE': 'libre.libre'
            # Add more mappings as needed
        }
        return contract_map.get(symbol, '')
