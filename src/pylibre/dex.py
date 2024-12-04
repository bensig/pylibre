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

    def fetch_order_book(self, quote_symbol, base_symbol, table="orderbook2", contract="dex.libre", limit=50):
        """
        Fetch the order book for a specific trading pair on the DEX.

        Args:
            quote_symbol (str): Base token symbol (e.g., USDT, BTC).
            base_symbol (str): Quote token symbol (e.g., BTC, LIBRE).
            table (str): The table to query (default: "orderbook2").
            contract (str): The DEX contract name (default: "dex.libre").
            limit (int): Number of rows to fetch.

        Returns:
            dict: Parsed order book with bids and offers separated.
        """
        # Create scope by combining quote and base symbols in lowercase
        scope = f"{base_symbol.lower()}{quote_symbol.lower()}"
        
        rows = self.client.get_table_rows(
            code=contract,
            table=table,
            scope=scope,
            limit=limit
        )
        bids = [row for row in rows if row["type"] == "buy"]
        offers = [row for row in rows if row["type"] == "sell"]
        
        # Sort bids (highest first) and offers (lowest first)
        bids = sorted(bids, key=lambda x: float(x["price"]), reverse=True)
        offers = sorted(offers, key=lambda x: float(x["price"]))

        return {"bids": bids, "offers": offers}

    def cancel_order(self, account, order_id, quote_symbol, base_symbol, contract="dex.libre"):
        """
        Cancel an existing order on the DEX.

        Args:
            account (str): The account cancelling the order.
            order_id (int): ID of the order to cancel.
            quote_symbol (str): Quote token symbol (e.g., BTC).
            base_symbol (str): Base token symbol (e.g., LIBRE).
            contract (str): The DEX contract name (default: "dex.libre").

        Returns:
            dict: Result of the transaction.
        """
        try:
            # Create pair string by combining base and quote symbols in lowercase
            pair = f"{base_symbol.lower()}{quote_symbol.lower()}"
            
            print(f"🔍 Debug - Cancel Order:")
            print(f"  Pair: {pair}")
            print(f"  Order ID: {order_id}")
            print(f"  Account: {account}")
            
            data = {
                "orderIdentifier": order_id,
                "pair": pair
            }
            
            print(f"  Action Data: {data}")
            
            return self.client.execute_action(
                contract=contract,
                action_name="cancelorder",
                data=data,
                actor=account
            )
        except Exception as e:
            print(f"❌ Error in cancel_order: {str(e)}")
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
