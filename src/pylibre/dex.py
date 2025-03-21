import json
import logging
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
        self.logger = logging.getLogger("pylibre.DexClient")

    def place_order(self, account, order_type, quantity, price, quote_symbol, base_symbol):
        import re
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
            # Get logger
            logger = logging.getLogger("pylibre.DexClient")
            
            # Log full parameters for debugging (DEBUG level only)
            logger.debug(f"Placing order with parameters:")
            logger.debug(f"Account: {account}")
            logger.debug(f"Order Type: {order_type}")
            logger.debug(f"Quantity: {quantity}")
            logger.debug(f"Price: {price}")
            logger.debug(f"Quote Symbol: {quote_symbol}")
            logger.debug(f"Base Symbol: {base_symbol}")
            logger.debug(f"Contract: {self.contract}")
            
            # Define token specifications
            TOKEN_SPECS = {
                "BTC": {"contract": "btc.libre", "precision": 8},  # Standard satoshi precision when used as base
                "USDT": {"contract": "usdt.libre", "precision": 8},
                "LIBRE": {"contract": "eosio.token", "precision": 4}
            }
            
            # Get precision for base and quote symbols
            base_precision = TOKEN_SPECS.get(base_symbol, {}).get("precision", 8)
            quote_precision = TOKEN_SPECS.get(quote_symbol, {}).get("precision", 8)
            
            # Special case: If BTC is the quote currency, use 10 decimal places
            if quote_symbol == "BTC":
                quote_precision = 10
            
            # Convert inputs to Decimal for precise calculation
            # Remove any existing symbol part if present in the input
            if isinstance(quantity, str) and " " in quantity:
                quantity = quantity.split()[0]
            if isinstance(price, str) and " " in price:
                price = price.split()[0]
            
            # Set higher precision for decimal calculations
            from decimal import getcontext
            getcontext().prec = 28
                
            quantity_dec = Decimal(str(quantity))
            price_dec = Decimal(str(price))

            # Format with correct precision
            if order_type == 'buy':
                send_amount = quantity_dec * price_dec
                send_symbol = quote_symbol
                send_precision = TOKEN_SPECS.get(quote_symbol, {}).get("precision", 8)
                send_quantity = f"{send_amount:.{send_precision}f}"
            else:  # sell
                send_amount = quantity_dec
                send_symbol = base_symbol
                send_precision = TOKEN_SPECS.get(base_symbol, {}).get("precision", 8)
                
                # Special handling for BTC sell orders
                if base_symbol == "BTC":
                    # Use standard satoshi precision (8 decimal places) when BTC is the base currency
                    formatted_amount = f"{send_amount:.8f}"
                    
                    # Ensure the formatted amount has exactly 8 decimal places
                    parts = formatted_amount.split('.')
                    if len(parts) == 2:
                        integer_part, decimal_part = parts
                        # Pad with zeros if needed
                        decimal_part = decimal_part.ljust(8, '0')[:8]
                        send_quantity = f"{integer_part}.{decimal_part}"
                    else:
                        send_quantity = f"{formatted_amount}.00000000"
                    
                    # Ensure we're not sending scientific notation
                    if 'e' in send_quantity.lower():
                        # Convert from scientific notation
                        decimal_amount_str = format(send_amount, '.8f')
                        send_quantity = decimal_amount_str
                    
                    # Check if the amount is too small (below minimum precision)
                    min_btc_amount = Decimal('0.00000001')  # Minimum BTC amount (8 decimal places)
                    if send_amount < min_btc_amount:
                        logger.error(f"❌ Error: BTC amount {send_amount} is below minimum precision of {min_btc_amount}")
                        return None
                    
                    # Validate the final format to ensure it's exactly what the blockchain expects
                    if not re.match(r'^\d+\.\d{8}$', send_quantity):
                        # Force the correct format
                        try:
                            decimal_val = Decimal(send_quantity)
                            send_quantity = f"{decimal_val:.8f}"
                        except Exception as e:
                            logger.error(f"❌ Error formatting BTC amount: {e}")
                            return None
                    
                    # Ensure the send_quantity exactly matches what's in the memo
                    # This is critical for BTC sell orders to be accepted
                    if order_type == 'sell':
                        # Match the quantity in the memo exactly
                        quantity_dec = Decimal(send_quantity)
                else:
                    send_quantity = f"{send_amount:.{send_precision}f}"

            # Create the action memo with correct precision for both symbols
            # For BTC, ensure exact formatting in the memo as well
            if base_symbol == "BTC":
                # Format quantity with exact 8 decimal places
                formatted_quantity = f"{quantity_dec:.8f}"
                parts = formatted_quantity.split('.')
                if len(parts) == 2:
                    integer_part, decimal_part = parts
                    decimal_part = decimal_part.ljust(8, '0')[:8]
                    formatted_quantity = f"{integer_part}.{decimal_part}"
                
                # Ensure price is also formatted correctly
                formatted_price = f"{price_dec:.{quote_precision}f}"
                price_parts = formatted_price.split('.')
                if len(price_parts) == 2:
                    price_integer, price_decimal = price_parts
                    price_decimal = price_decimal.ljust(quote_precision, '0')[:quote_precision]
                    formatted_price = f"{price_integer}.{price_decimal}"
                
                # Exactly match the format from successful CLI commands
                action = f"{order_type}:{formatted_quantity} {base_symbol}:{formatted_price} {quote_symbol}"
                
                # For sell orders, ensure the send_quantity and memo quantity match exactly
                if order_type == 'sell' and formatted_quantity != send_quantity:
                    logger.debug(f"Adjusting send quantity to match memo quantity for BTC sell order")
                    logger.debug(f"  Original: {send_quantity}")
                    logger.debug(f"  Adjusted: {formatted_quantity}")
                    send_quantity = formatted_quantity
            elif quote_symbol == "BTC":
                # Special handling for when BTC is the quote currency (sub-satoshi precision)
                # Format base quantity with standard precision
                formatted_quantity = f"{quantity_dec:.{base_precision}f}"
                parts = formatted_quantity.split('.')
                if len(parts) == 2:
                    integer_part, decimal_part = parts
                    decimal_part = decimal_part.ljust(base_precision, '0')[:base_precision]
                    formatted_quantity = f"{integer_part}.{decimal_part}"
                
                # Format price with 10 decimal places for sub-satoshi precision
                formatted_price = f"{price_dec:.10f}"
                price_parts = formatted_price.split('.')
                if len(price_parts) == 2:
                    price_integer, price_decimal = price_parts
                    price_decimal = price_decimal.ljust(10, '0')[:10]
                    formatted_price = f"{price_integer}.{price_decimal}"
                
                # Exactly match the format from successful CLI commands
                action = f"{order_type}:{formatted_quantity} {base_symbol}:{formatted_price} {quote_symbol}"
            else:
                action = f"{order_type}:{quantity_dec:.{base_precision}f} {base_symbol}:{price_dec:.{quote_precision}f} {quote_symbol}"
            
            # Concise INFO level log for the order placement
            logger.info(f"Order: {order_type.upper()} {quantity_dec:.{base_precision}f} {base_symbol} @ {price_dec:.{quote_precision}f} {quote_symbol}")
            
            # Detailed DEBUG level log for transfer details
            logger.debug(f"Transfer details:")
            logger.debug(f"  From: {account}")
            logger.debug(f"  To: {self.contract}")
            logger.debug(f"  Amount: {send_quantity} {send_symbol}")
            logger.debug(f"  Memo: {action}")
            
            # For BTC sell orders, ensure the contract is explicitly specified
            if order_type == 'sell' and base_symbol == 'BTC':
                contract = "btc.libre"
                
                # Match exactly the format used in the successful CLI command
                # Ensure quantity has exactly 8 decimal places
                exact_quantity = f"{Decimal(send_quantity):.8f}"
                
                # Ensure the memo format exactly matches the CLI format
                exact_price = f"{Decimal(price):.8f}"
                exact_memo = f"{order_type}:{exact_quantity} {base_symbol}:{exact_price} {quote_symbol}"
                
                # Log detailed BTC info at DEBUG level
                logger.debug(f"DETAILED BTC SELL ORDER INFO:")
                logger.debug(f"Exact quantity: {exact_quantity}")
                logger.debug(f"Exact price: {exact_price}")
                logger.debug(f"Exact memo: {exact_memo}")
                logger.debug(f"Contract: {contract}")
                
                # Try with the exact format that worked in CLI
                result = self.client.transfer(
                    from_account=account,
                    to_account=self.contract,
                    quantity=f"{exact_quantity} {send_symbol}",
                    memo=exact_memo,
                    contract=contract
                )
            # Special handling for when BTC is the quote currency (buy orders)
            elif order_type == 'buy' and quote_symbol == 'BTC':
                # For buy orders with BTC as quote, we need to ensure the price has 10 decimal places
                # Match exactly the format used in the successful CLI command
                exact_price = f"{Decimal(price):.10f}"
                exact_quantity = f"{Decimal(quantity):.{base_precision}f}"
                exact_memo = f"{order_type}:{exact_quantity} {base_symbol}:{exact_price} {quote_symbol}"
                
                # Log detailed BTC info at DEBUG level
                logger.debug(f"DETAILED BTC QUOTE BUY ORDER INFO:")
                logger.debug(f"Exact quantity: {exact_quantity}")
                logger.debug(f"Exact price: {exact_price}")
                logger.debug(f"Exact memo: {exact_memo}")
                
                result = self.client.transfer(
                    from_account=account,
                    to_account=self.contract,
                    quantity=f"{send_quantity} {send_symbol}",
                    memo=exact_memo
                )
            else:
                result = self.client.transfer(
                    from_account=account,
                    to_account=self.contract,
                    quantity=f"{send_quantity} {send_symbol}",
                    memo=action
                )

            if result.get("success"):
                tx_id = result.get("data", {}).get("transaction_id", "unknown")
                logger.info(f"✅ Order confirmed (tx: {tx_id[:8]}...)")
                
                # Log detailed response at DEBUG level
                logger.debug(f"Full transaction response: {result}")
                
                return tx_id
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"❌ Order failed: {error_msg}")
                
                # Log detailed error info at DEBUG level
                logger.debug(f"DETAILED ERROR INFO:")
                logger.debug(f"Error message: {error_msg}")
                
                return None
                
        except Exception as e:
            logger = logging.getLogger("pylibre.DexClient")
            logger.error(f"❌ Error placing order: {str(e)}")
            
            # Add stack trace at DEBUG level
            import traceback
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            
            return None

    def fetch_order_book(self, quote_symbol: str, base_symbol: str) -> dict:
        """Fetch the complete order book for a trading pair."""
        try:
            pair = f"{base_symbol.lower()}{quote_symbol.lower()}"
            
            if self.client.verbose:
                print(f"Fetching order book for {base_symbol}/{quote_symbol}...")
                print(f"Fetching rows... (found 0 so far)")
            
            all_rows = []
            more = True
            last_key = ""
            
            while more:
                response = self.client.get_table_rows(
                    code=self.contract,
                    table="orderbook2",
                    scope=pair,
                    limit=1000,  # Use a high limit to get more rows at once
                    lower_bound=last_key if last_key else None
                )
                
                if not response.get("success", False):
                    if self.client.verbose:
                        print(f"❌ Error fetching order book: {response.get('error', 'Unknown error')}")
                    return {"bids": [], "offers": []}
                
                rows = response.get("rows", [])
                all_rows.extend(rows)
                
                if self.client.verbose:
                    print(f"Fetching rows... (found {len(all_rows)} so far)")
                
                more = response.get("more", False)
                if more and len(rows) > 0:
                    # Get the last identifier for pagination
                    last_key = str(rows[-1].get("identifier", ""))
                else:
                    more = False
            
            if self.client.verbose:
                print(f"Fetched {len(all_rows)} rows total")
            
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
            return {"bids": [], "offers": []}

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

    def get_account_balances(self, account: str) -> list:
        """Get all token balances for an account.
        
        Args:
            account (str): The account to check balances for
            
        Returns:
            list: List of balance objects with symbol and amount
        """
        try:
            if self.client.verbose:
                print(f"Fetching balances for account {account}...")
            
            # Define token contracts to check
            token_contracts = [
                {"symbol": "LIBRE", "contract": "eosio.token"},
                {"symbol": "BTC", "contract": "btc.libre"},
                {"symbol": "USDT", "contract": "usdt.libre"}
            ]
            
            balances = []
            
            # Fetch balances for each token contract
            for token in token_contracts:
                try:
                    # Use get_currency_balance instead of get_table_rows
                    balance = self.client.get_currency_balance(
                        account=account,
                        symbol=token["symbol"],
                        contract=token["contract"]
                    )
                    
                    # Parse the balance string (e.g., "10.00000000 BTC")
                    if balance:
                        balance_parts = balance.split()
                        if len(balance_parts) == 2:
                            amount, symbol = balance_parts
                            balances.append({
                                "symbol": symbol,
                                "amount": amount
                            })
                except Exception as e:
                    if self.client.verbose:
                        print(f"Warning: Could not get balance for {token['symbol']}: {e}")
            
            if self.client.verbose:
                print(f"Found {len(balances)} token balances for {account}")
                for balance in balances:
                    print(f"  {balance['amount']} {balance['symbol']}")
            
            return balances
            
        except Exception as e:
            if self.client.verbose:
                print(f"❌ Error in get_account_balances: {str(e)}")
            return []
