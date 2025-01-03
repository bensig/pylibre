import json
from .client import LibreClient

class DexClient:
    def __init__(self, client: LibreClient):
        self.client = client

    def place_order(self, account, order_type, quantity, price, quote_symbol, base_symbol, contract="dex.libre"):
        """
        Place an order on the DEX (bid or offer).

        Args:
            account (str): The account placing the order.
            order_type (str): Either "buy" or "sell".
            quantity (str): Quantity of the base token to trade.
            price (str): Price per unit in quote token.
            quote_symbol (str): Quote token symbol (e.g., BTC).
            base_symbol (str): Base token symbol (e.g., LIBRE).
            contract (str): DEX contract name (default: "dex.libre").

        Returns:
            dict: Result of the transaction.
        """
        def format_amount(amount, symbol, is_price=False):
            """Format amount with correct precision
            
            Args:
                amount (float|str): Amount to format
                symbol (str): Token symbol
                is_price (bool): If True, uses price precision (10), otherwise uses token precision
            """
            if is_price:
                precision = 10
            else:
                precision = 4 if symbol == "LIBRE" else 8
            return f"{float(amount):.{precision}f}"

        # For buy orders, we need to send quote_quantity = quantity * price
        # For sell orders, we send the base_quantity directly
        if order_type == 'buy':
            send_quantity = format_amount(float(quantity) * float(price), quote_symbol)
            send_symbol = quote_symbol
        else:  # sell
            send_quantity = format_amount(float(quantity), base_symbol)
            send_symbol = base_symbol

        action = f"{order_type}:{format_amount(float(quantity), base_symbol)} {base_symbol}:{format_amount(float(price), quote_symbol, is_price=True)} {quote_symbol}"
        
        print("\n🔍 Debug Information:")
        print(f"Send Amount: {send_quantity} {send_symbol}")
        print(f"Action Memo: {action}")
        
        return self.client.transfer(
            from_account=account,
            to_account=contract,
            quantity=f"{send_quantity} {send_symbol}",
            memo=action
        )

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
                    code="dex.libre",
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
