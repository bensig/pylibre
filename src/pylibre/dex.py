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
            quantity (str): Quantity of the asset to trade.
            price (str): Price per unit.
            base_symbol (str): Base token symbol (e.g., USDT).
            quote_symbol (str): Quote token symbol (e.g., BTC).
            contract (str): DEX contract name (default: "dex.libre").

        Returns:
            dict: Result of the transaction.
        """
        action = f"{order_type}:{quantity} {quote_symbol}:{price} {base_symbol}"
        data = {
            "from": account,
            "to": contract,
            "quantity": f"{quantity} {base_symbol if order_type == 'buy' else quote_symbol}",
            "memo": action
        }
        return self.client.execute_action(contract=base_symbol if order_type == "buy" else quote_symbol, 
                                          action_name="transfer", data=data, actor=account)

    def fetch_order_book(self, scope, table="orderbook2", contract="dex.libre", limit=50):
        """
        Fetch the order book for a specific scope on the DEX.

        Args:
            scope (str): The scope to query (e.g., "usdtbtc").
            table (str): The table to query (default: "orderbook2").
            contract (str): The DEX contract name (default: "dex.libre").
            limit (int): Number of rows to fetch.

        Returns:
            dict: Parsed order book with bids and offers separated.
        """
        rows = self.client.get_table_rows(
            code=contract,
            table=table,
            scope=scope,
            limit=limit
        )
        bids = [row for row in rows if row["order_type"] == "bid"]
        offers = [row for row in rows if row["order_type"] == "offer"]
        
        # Sort bids (highest first) and offers (lowest first)
        bids = sorted(bids, key=lambda x: float(x["price"]), reverse=True)
        offers = sorted(offers, key=lambda x: float(x["price"]))

        return {"bids": bids, "offers": offers}

    def cancel_order(self, account, order_id, contract="dex.libre"):
        """
        Cancel an existing order on the DEX.

        Args:
            account (str): The account cancelling the order.
            order_id (int): ID of the order to cancel.
            contract (str): The DEX contract name (default: "dex.libre").

        Returns:
            dict: Result of the transaction.
        """
        data = {
            "owner": account,
            "order_id": order_id
        }
        return self.client.execute_action(contract=contract, action_name="cancelorder", data=data, actor=account)
