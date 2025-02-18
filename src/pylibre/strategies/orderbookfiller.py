from .templates.base_strategy import BaseStrategy
import time
from decimal import Decimal
from typing import List, Dict, Optional, Any
import random

class OrderBookFillerStrategy(BaseStrategy):
    def __init__(self, client, account, base_symbol, quote_symbol, parameters, logger=None):
        super().__init__(client, account, base_symbol, quote_symbol, parameters, logger)
        self.update_interval_ms = parameters['update_interval_ms']
        self.min_spread_percentage = Decimal(str(parameters['min_spread_percentage']))
        self.max_spread_percentage = Decimal(str(parameters['max_spread_percentage']))
        self.num_orders = parameters['num_orders']
        self.quantity_distribution = parameters['quantity_distribution']
        self.order_spacing = parameters['order_spacing']
        self.price_source_config = parameters['price_source_config']
        self.price_threshold = Decimal('0.01')  # 1% threshold for order adjustment
        self.orders = {}  # Track our active orders by ID

    def run(self):
        while True:
            try:
                # Get current market price
                market_price = self.get_market_price()
                self.logger.info(f"BTC/USDT price is: {market_price}")

                # Get account balances
                base_balance_str = self.client.get_currency_balance(self.account, self.base_symbol)
                quote_balance_str = self.client.get_currency_balance(self.account, self.quote_symbol)
                base_balance = Decimal(base_balance_str.split()[0])
                quote_balance = Decimal(quote_balance_str.split()[0])
                self.logger.info(f"Account balances are: {base_balance} {self.base_symbol}, {quote_balance} {self.quote_symbol}")

                # Get current order book
                order_book = self.dex.fetch_order_book(
                    quote_symbol=self.quote_symbol,
                    base_symbol=self.base_symbol
                )
                
                if order_book is None:
                    self.logger.error("Failed to fetch order book")
                    time.sleep(self.update_interval_ms / 1000.0)
                    continue

                # Count our current orders
                our_bids = [bid for bid in order_book.get("bids", []) if bid["account"] == self.account]
                our_offers = [offer for offer in order_book.get("offers", []) if offer["account"] == self.account]
                
                half_orders = self.num_orders // 2
                min_price = market_price * (Decimal('1') - self.min_spread_percentage)
                max_price = market_price * (Decimal('1') + self.max_spread_percentage)

                # Check and maintain buy orders
                if len(our_bids) < half_orders:
                    self.logger.info(f"Need to place {half_orders - len(our_bids)} more buy orders")
                    self.place_buy_orders(market_price, min_price, half_orders - len(our_bids))
                else:
                    # Check if any buy orders need adjustment
                    for bid in our_bids:
                        bid_price = Decimal(str(bid["price"]))
                        if abs(bid_price - market_price) / market_price > self.price_threshold:
                            self.logger.info(f"Cancelling buy order at {bid_price} (too far from market price)")
                            try:
                                self.dex.cancel_order(
                                    account=self.account,
                                    order_id=bid["identifier"],
                                    quote_symbol=self.quote_symbol,
                                    base_symbol=self.base_symbol
                                )
                            except Exception as e:
                                self.logger.error(f"Failed to cancel buy order: {str(e)}")

                # Check and maintain sell orders
                if len(our_offers) < half_orders:
                    self.logger.info(f"Need to place {half_orders - len(our_offers)} more sell orders")
                    self.place_sell_orders(market_price, max_price, half_orders - len(our_offers))
                else:
                    # Check if any sell orders need adjustment
                    for offer in our_offers:
                        offer_price = Decimal(str(offer["price"]))
                        if abs(offer_price - market_price) / market_price > self.price_threshold:
                            self.logger.info(f"Cancelling sell order at {offer_price} (too far from market price)")
                            try:
                                self.dex.cancel_order(
                                    account=self.account,
                                    order_id=offer["identifier"],
                                    quote_symbol=self.quote_symbol,
                                    base_symbol=self.base_symbol
                                )
                            except Exception as e:
                                self.logger.error(f"Failed to cancel sell order: {str(e)}")

                # Wait for next iteration
                time.sleep(self.update_interval_ms / 1000.0)

            except Exception as e:
                self.logger.error(f"Error in strategy execution: {str(e)}")
                time.sleep(self.update_interval_ms / 1000.0)

    def place_order(self, order_type: str, amount: Decimal, price: Decimal) -> Optional[str]:
        """Place a single order and return the order ID if successful."""
        try:
            order_id = self.dex.place_order(
                self.account,
                order_type,
                amount,
                price,
                self.quote_symbol,
                self.base_symbol
            )
            
            # Log result
            self.log_order_result(order_type, amount, price, order_id)
            return order_id
                
        except Exception as e:
            self.logger.error("Order failed: " + str(e))
            if hasattr(e, 'response'):
                self.logger.debug(f"Full error response:")
                self.logger.debug(f"  Status code: {e.response.status_code if hasattr(e.response, 'status_code') else 'N/A'}")
                self.logger.debug(f"  Response text: {e.response.text if hasattr(e.response, 'text') else str(e.response)}")
                if hasattr(e.response, 'json'):
                    try:
                        json_resp = e.response.json()
                        self.logger.debug(f"  JSON response: {json_resp}")
                    except:
                        pass
            return None

    def calculate_sell_prices(self, market_price: Decimal, num_orders: int) -> List[Decimal]:
        """Calculate prices for sell orders above market price"""
        price_step = (market_price * self.max_spread_percentage) / Decimal(str(num_orders))
        return [
            market_price + (price_step * Decimal(str(i)))
            for i in range(num_orders)
        ]

    def calculate_buy_prices(self, market_price: Decimal, num_orders: int) -> List[Decimal]:
        """Calculate prices for buy orders below market price"""
        price_step = (market_price * self.min_spread_percentage) / Decimal(str(num_orders))
        return [
            market_price - (price_step * Decimal(str(num_orders - i)))
            for i in range(num_orders)
        ]

    def place_buy_orders(self, market_price: Decimal, min_price: Decimal, num_orders: int):
        """Place the specified number of buy orders."""
        # Get available quote balance (USDT)
        balance_str = self.client.get_currency_balance(self.account, self.quote_symbol)
        quote_balance = Decimal(balance_str.split()[0])  # Split "0.00000000 USDT" and take first part
        
        if quote_balance <= Decimal('0'):
            self.logger.error(f"Insufficient {self.quote_symbol} balance for buy orders")
            return

        # Calculate max amount per order to ensure we don't exceed quote balance
        max_amount_per_order = quote_balance / (market_price * Decimal(str(num_orders)))
        
        prices = self.calculate_buy_prices(market_price, num_orders)
        for i, price in enumerate(prices):
            # Randomize amount between 10% and 100% of max amount
            max_amount = self.normalize_amount(max_amount_per_order)
            min_amount = self.normalize_amount(max_amount * Decimal('0.1'))
            amount = self.normalize_amount(
                Decimal(str(random.uniform(float(min_amount), float(max_amount))))
            )
            
            order_id = self.place_order("buy", amount, price)
            if order_id:
                self.log_order_result("buy", amount, price, order_id, i+1)
                self.orders[order_id] = {"type": "buy", "price": price, "amount": amount}

    def place_sell_orders(self, market_price: Decimal, max_price: Decimal, num_orders: int):
        """Place the specified number of sell orders."""
        # Get available base balance (BTC)
        balance_str = self.client.get_currency_balance(self.account, self.base_symbol)
        base_balance = Decimal(balance_str.split()[0])  # Split "0.00000000 BTC" and take first part
        
        if base_balance <= Decimal('0'):
            self.logger.error(f"Insufficient {self.base_symbol} balance for sell orders")
            return

        # Calculate max amount per order to ensure we don't exceed base balance
        max_amount_per_order = base_balance / Decimal(str(num_orders))
        
        prices = self.calculate_sell_prices(market_price, num_orders)
        for i, price in enumerate(prices):
            # Randomize amount between 10% and 100% of max amount
            max_amount = self.normalize_amount(max_amount_per_order)
            min_amount = self.normalize_amount(max_amount * Decimal('0.1'))
            amount = self.normalize_amount(
                Decimal(str(random.uniform(float(min_amount), float(max_amount))))
            )
            
            order_id = self.place_order("sell", amount, price)
            if order_id:
                self.log_order_result("sell", amount, price, order_id, i+1)
                self.orders[order_id] = {"type": "sell", "price": price, "amount": amount}

    def get_market_price(self):
        if self.price_source_config['source'] == 'binance':
            return self.get_binance_price(self.price_source_config['reference_symbol'])
        return self.get_fixed_price()

    def get_binance_price(self, symbol):
        # In a real implementation, this would fetch from Binance
        # For now, using the price from shared data
        return Decimal('95382.75')

    def get_fixed_price(self):
        return Decimal('95382.75')

    def place_orders(self, signal: Dict[str, Any]) -> bool:
        """
        Required implementation of abstract method from BaseStrategy.
        This strategy doesn't use signals, it maintains the order book continuously.
        
        Args:
            signal: The trading signal (unused in this strategy)
        Returns:
            bool: Always returns True as orders are handled in run()
        """
        return True

    def log_order_result(self, order_type: str, amount: Decimal, price: Decimal, order_id: Optional[str], order_number: Optional[int] = None):
        # Log result
        if order_id:
            if order_number:
                self.logger.info(f"{order_type.capitalize()} order {order_number}: {amount} {self.base_symbol} @ {price:.2f} {self.quote_symbol}... Order succeeded (ID: {order_id})")
            else:
                self.logger.info(f"{order_type.capitalize()} order: {amount} {self.base_symbol} @ {price:.2f} {self.quote_symbol}... Order succeeded (ID: {order_id})")
        else:
            if order_number:
                self.logger.error(f"{order_type.capitalize()} order {order_number}: {amount} {self.base_symbol} @ {price:.2f} {self.quote_symbol}... Order failed")
            else:
                self.logger.error(f"{order_type.capitalize()} order: {amount} {self.base_symbol} @ {price:.2f} {self.quote_symbol}... Order failed")
