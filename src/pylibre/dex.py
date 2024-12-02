import json
from .client import LibreClient

class DexClient:
    def __init__(self, client: LibreClient):
        self.client = client

    def place_order(self, account, order_type, quantity, price, base_symbol, quote_symbol, contract="dex.libre"):
        """
        Place an order on the DEX (bid or offer).

        Args:
            account (str): The account placing the order.
            order_type (str): Either "buy" or "sell".
            quantity (str): Quantity of the quote token (e.g., BTC) to trade.
            price (str): Price per unit in base token (e.g., USDT).
            base_symbol (str): Base token symbol (e.g., USDT).
            quote_symbol (str): Quote token symbol (e.g., BTC).
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

        # For buy orders, we need to send base_quantity = quantity * price
        # For sell orders, we send the quote_quantity directly
        if order_type == 'buy':
            send_quantity = format_amount(float(quantity) * float(price), base_symbol)
            send_symbol = base_symbol
        else:  # sell
            send_quantity = format_amount(float(quantity), quote_symbol)
            send_symbol = quote_symbol

        action = f"{order_type}:{format_amount(float(quantity), quote_symbol)} {quote_symbol}:{format_amount(float(price), base_symbol, is_price=True)} {base_symbol}"
        
        print("\n🔍 Debug Information:")
        print(f"Send Amount: {send_quantity} {send_symbol}")
        print(f"Action Memo: {action}")
        
        return self.client.transfer(
            from_account=account,
            to_account=contract,
            quantity=f"{send_quantity} {send_symbol}",
            memo=action
        )

    def fetch_order_book(self, base_symbol, quote_symbol, table="orderbook2", contract="dex.libre", limit=50):
        """
        Fetch the order book for a specific trading pair on the DEX.

        Args:
            base_symbol (str): Base token symbol (e.g., USDT, BTC).
            quote_symbol (str): Quote token symbol (e.g., BTC, LIBRE).
            table (str): The table to query (default: "orderbook2").
            contract (str): The DEX contract name (default: "dex.libre").
            limit (int): Number of rows to fetch.

        Returns:
            dict: Parsed order book with bids and offers separated.
        """
        # Create scope by combining quote and base symbols in lowercase
        scope = f"{quote_symbol.lower()}{base_symbol.lower()}"
        
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

    def cancel_order(self, account, order_id, base_symbol, quote_symbol, contract="dex.libre"):
        """
        Cancel an existing order on the DEX.

        Args:
            account (str): The account cancelling the order.
            order_id (int): ID of the order to cancel.
            base_symbol (str): Base token symbol (e.g., BTC).
            quote_symbol (str): Quote token symbol (e.g., LIBRE).
            contract (str): The DEX contract name (default: "dex.libre").

        Returns:
            dict: Result of the transaction.
        """
        # Create pair string by combining quote and base symbols in lowercase
        pair = f"{quote_symbol.lower()}{base_symbol.lower()}"
        
        data = {
            "orderIdentifier": order_id,
            "pair": pair
        }
        
        return self.client.execute_action(
            contract=contract,
            action_name="cancelorder",
            data=data,
            actor=account
        )
