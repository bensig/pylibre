from .templates.base_strategy import BaseStrategy, DEFAULT_COIN_LIMITS
import time
from decimal import Decimal, ROUND_DOWN
from typing import List, Dict, Optional, Any
import random
import logging

class OrderBookMakerStrategy(BaseStrategy):
    """
    OrderBookMakerStrategy creates a spread of orders around a center price,
    respecting minimum and maximum values from the config.
    """
    
    def __init__(self, client, account, base_symbol, quote_symbol, parameters, logger=None):
        super().__init__(client, account, base_symbol, quote_symbol, parameters, logger)
        
        # Strategy parameters
        self.total_orders = parameters.get('num_orders', 30)
        self.orders_per_side = self.total_orders // 2
        self.min_spread_percentage = Decimal(str(parameters.get('min_spread_percentage', 0.01)))
        self.max_spread_percentage = Decimal(str(parameters.get('max_spread_percentage', 0.05)))
        self.order_spacing = parameters.get('order_spacing', 'linear')
        self.quantity_distribution = parameters.get('quantity_distribution', 'equal')
        
        # Get min/max order values from config or defaults
        base_min, base_max = self._get_coin_limits(base_symbol)
        quote_min, quote_max = self._get_coin_limits(quote_symbol)
        
        self.min_base_value = base_min
        self.max_base_value = base_max
        self.min_quote_value = quote_min
        self.max_quote_value = quote_max
        
        # Store the market price
        self._market_price = None
        
        # Log configuration
        self.logger.info(f"Initialized OrderBookMakerStrategy with:")
        self.logger.info(f"  Account: {account}")
        self.logger.info(f"  Trading pair: {base_symbol}/{quote_symbol}")
        self.logger.info(f"  Total orders: {self.total_orders} ({self.orders_per_side} per side)")
        self.logger.info(f"  Spread range: {float(self.min_spread_percentage)*100}% to {float(self.max_spread_percentage)*100}%")
        self.logger.info(f"  Min {base_symbol} order value: {float(self.min_base_value)}")
        self.logger.info(f"  Max {base_symbol} order value: {float(self.max_base_value)}")
        self.logger.info(f"  Min {quote_symbol} order value: {float(self.min_quote_value)}")
        self.logger.info(f"  Max {quote_symbol} order value: {float(self.max_quote_value)}")

    def _get_coin_limits(self, symbol):
        """Get minimum and maximum order values for a symbol."""
        # Get default limits for the symbol
        default_limits = DEFAULT_COIN_LIMITS.get(symbol, {
            'min_order_value': 10.0,
            'max_order_value': 100.0,
        })
        
        # Get limits from parameters, falling back to defaults
        min_order = Decimal(str(self.parameters.get(
            f'min_{symbol.lower()}_order_value',
            default_limits['min_order_value']
        )))
        max_order = Decimal(str(self.parameters.get(
            f'max_{symbol.lower()}_order_value',
            default_limits['max_order_value']
        )))
        
        return min_order, max_order

    def get_market_price(self) -> Optional[Decimal]:
        """Get the current market price for the trading pair."""
        # If we have a stored price, use it
        if self._market_price is not None:
            return self._market_price
        
        # Try to get price from parent method
        price = super().get_market_price()
        
        # If price is not available, use our default prices
        if price is None or price == Decimal('0'):
            # Default prices for common trading pairs
            if self.base_symbol == 'BTC' and self.quote_symbol == 'USDT':
                price = Decimal('50000')
            elif self.base_symbol == 'LIBRE' and self.quote_symbol == 'BTC':
                # Try to get the price from the price tracker's fallback price
                fallback_price = self.parameters.get('fallback_price')
                if fallback_price:
                    price = Decimal(str(fallback_price))
                else:
                    # Use a reasonable default if no fallback price is provided
                    price = Decimal('0.0000000084')  # 0.84 sats
            elif self.base_symbol == 'LIBRE' and self.quote_symbol == 'USDT':
                price = Decimal('0.005')
            elif self.base_symbol == 'ETH' and self.quote_symbol == 'USDT':
                price = Decimal('3000')
            elif self.base_symbol == 'ETH' and self.quote_symbol == 'BTC':
                price = Decimal('0.06')
            else:
                price = Decimal('1.0')
        
        # Store the price
        self._market_price = price
            
        return price

    def generate_signal(self) -> Dict[str, Any]:
        """Generate trading signal with order prices and quantities"""
        center_price = self.get_market_price()
        
        self.logger.info(f"Using center price: {center_price} {self.quote_symbol}")
            
        # Generate price levels for buy and sell orders
        sell_prices = self.generate_sell_prices(center_price)
        buy_prices = self.generate_buy_prices(center_price)
        
        # Generate quantities for each price level
        sell_orders = self.generate_order_quantities(sell_prices, "sell")
        buy_orders = self.generate_order_quantities(buy_prices, "buy")
        
        return {
            "center_price": center_price,
            "sell_orders": sell_orders,
            "buy_orders": buy_orders
        }
        
    def generate_sell_prices(self, center_price: Decimal) -> List[Decimal]:
        """Generate price levels for sell orders"""
        prices = []
        
        # Calculate price range
        min_price = center_price * (Decimal('1') + self.min_spread_percentage)
        max_price = center_price * (Decimal('1') + self.max_spread_percentage)
        
        self.logger.info(f"Sell price range: {min_price} to {max_price} {self.quote_symbol}")
        
        # Generate prices based on spacing method
        if self.order_spacing == 'linear':
            # Linear spacing between min and max price
            if self.orders_per_side > 1:
                step = (max_price - min_price) / (self.orders_per_side - 1)
                prices = [min_price + step * i for i in range(self.orders_per_side)]
            else:
                prices = [min_price]
        elif self.order_spacing == 'exponential':
            # Exponential spacing
            if self.orders_per_side > 1:
                factor = (max_price / min_price) ** (1 / (self.orders_per_side - 1))
                prices = [min_price * (factor ** i) for i in range(self.orders_per_side)]
            else:
                prices = [min_price]
        else:
            # Default to linear
            if self.orders_per_side > 1:
                step = (max_price - min_price) / (self.orders_per_side - 1)
                prices = [min_price + step * i for i in range(self.orders_per_side)]
            else:
                prices = [min_price]
                
        # Normalize prices to correct precision
        return [self.normalize_price(price) for price in prices]
        
    def generate_buy_prices(self, center_price: Decimal) -> List[Decimal]:
        """Generate price levels for buy orders"""
        prices = []
        
        # Calculate price range
        min_price = center_price * (Decimal('1') - self.max_spread_percentage)
        max_price = center_price * (Decimal('1') - self.min_spread_percentage)
        
        self.logger.info(f"Buy price range: {min_price} to {max_price} {self.quote_symbol}")
        
        # Generate prices based on spacing method
        if self.order_spacing == 'linear':
            # Linear spacing between min and max price
            if self.orders_per_side > 1:
                step = (max_price - min_price) / (self.orders_per_side - 1)
                prices = [min_price + step * i for i in range(self.orders_per_side)]
            else:
                prices = [min_price]
        elif self.order_spacing == 'exponential':
            # Exponential spacing
            if self.orders_per_side > 1:
                factor = (max_price / min_price) ** (1 / (self.orders_per_side - 1))
                prices = [min_price * (factor ** i) for i in range(self.orders_per_side)]
            else:
                prices = [min_price]
        else:
            # Default to linear
            if self.orders_per_side > 1:
                step = (max_price - min_price) / (self.orders_per_side - 1)
                prices = [min_price + step * i for i in range(self.orders_per_side)]
            else:
                prices = [min_price]
                
        # Normalize prices to correct precision
        return [self.normalize_price(price) for price in prices]
        
    def generate_order_quantities(self, prices: List[Decimal], order_type: str) -> List[Dict[str, Any]]:
        """Generate quantities for each price level"""
        orders = []
        
        # Special handling for LIBRE/BTC pair
        is_libre_btc = self.base_symbol == 'LIBRE' and self.quote_symbol == 'BTC'
        
        for i, price in enumerate(prices):
            # Skip if price is zero to avoid division by zero
            if price == Decimal('0'):
                self.logger.warning(f"Skipping {order_type} order with zero price")
                continue
                
            # Calculate quantity based on min/max constraints
            if order_type == "sell":
                # For sell orders, we're selling base for quote
                if is_libre_btc:
                    # For LIBRE/BTC, ensure we meet the minimum BTC value
                    # Calculate quantity to achieve at least 0.0001 BTC value
                    min_quantity = (self.min_quote_value * Decimal('1.01')) / price
                    max_quantity = self.max_base_value
                else:
                    # Ensure order value meets minimum quote value
                    # Add a small buffer (1.001) to ensure we're above the minimum after rounding
                    min_quantity = (self.min_quote_value * Decimal('1.001')) / price
                    # Ensure order doesn't exceed maximum base value
                    max_quantity = self.max_base_value
            else:
                # For buy orders, we're buying base with quote
                if is_libre_btc:
                    # For LIBRE/BTC, ensure we meet the minimum BTC value
                    min_quantity = (self.min_quote_value * Decimal('1.01')) / price
                    max_quantity = self.max_quote_value / price
                else:
                    # Ensure order value meets minimum quote value
                    # Add a small buffer (1.001) to ensure we're above the minimum after rounding
                    min_quantity = (self.min_quote_value * Decimal('1.001')) / price
                    # Ensure order doesn't exceed maximum quote value
                    max_quantity = self.max_quote_value / price
                
            # Apply quantity distribution with added randomness
            if self.quantity_distribution == 'equal':
                # Add some randomness even for equal distribution (±10%)
                random_factor = Decimal(str(0.9 + random.random() * 0.2))  # 0.9 to 1.1
                quantity = min_quantity * random_factor
            elif self.quantity_distribution == 'random':
                # Fully random between min and max
                random_value = Decimal(str(random.random()))
                quantity = min_quantity + (random_value * (max_quantity - min_quantity))
            elif self.quantity_distribution == 'descending':
                # Larger quantities for orders closer to the center with randomness
                factor = Decimal(str(1 - (i / self.orders_per_side)))
                random_factor = Decimal(str(0.9 + random.random() * 0.2))  # 0.9 to 1.1
                quantity = (min_quantity + factor * (max_quantity - min_quantity)) * random_factor
            elif self.quantity_distribution == 'ascending':
                # Larger quantities for orders further from the center with randomness
                factor = Decimal(str(i / self.orders_per_side))
                random_factor = Decimal(str(0.9 + random.random() * 0.2))  # 0.9 to 1.1
                quantity = (min_quantity + factor * (max_quantity - min_quantity)) * random_factor
            else:
                # Default to equal with randomness
                random_factor = Decimal(str(0.9 + random.random() * 0.2))  # 0.9 to 1.1
                quantity = min_quantity * random_factor
                
            # Check if quantity is valid
            if quantity > max_quantity:
                self.logger.warning(f"Calculated quantity {quantity} exceeds maximum {max_quantity} for {order_type} order at price {price}")
                quantity = max_quantity
            
            # Normalize quantity to correct precision
            quantity = self.normalize_amount(quantity)
            
            # Calculate order value
            order_value = quantity * price
            
            # Double-check if order value meets minimum requirements
            if order_value < self.min_quote_value:
                # If we're very close to the minimum (within 1%), just adjust the quantity slightly
                if order_value >= self.min_quote_value * Decimal('0.99'):
                    # Adjust quantity to meet minimum value
                    adjusted_quantity = self.normalize_amount((self.min_quote_value * Decimal('1.01')) / price)
                    self.logger.info(f"Adjusting quantity from {quantity} to {adjusted_quantity} to meet minimum order value")
                    quantity = adjusted_quantity
                    order_value = quantity * price
                else:
                    self.logger.warning(f"Order value {order_value} is below minimum {self.min_quote_value} for {order_type} order at price {price}")
                    continue
                
            orders.append({
                "price": price,
                "quantity": quantity,
                "order_value": order_value
            })
            
        return orders
        
    def place_orders(self, signal: Dict[str, Any]) -> bool:
        """Place orders based on the generated signal"""
        if not signal:
            self.logger.error("No signal to place orders")
            return False
            
        sell_orders = signal.get("sell_orders", [])
        buy_orders = signal.get("buy_orders", [])
        
        # Place sell orders
        sell_success_count = 0
        for i, order in enumerate(sell_orders):
            price = order["price"]
            quantity = order["quantity"]
            
            # Format quantity for the order
            quantity_str = self._format_quantity(quantity, self.base_symbol)
            
            # Place the order
            result = self._place_single_order("sell", quantity_str, price, i+1)
            if result:
                sell_success_count += 1
                
        # Place buy orders
        buy_success_count = 0
        for i, order in enumerate(buy_orders):
            price = order["price"]
            quantity = order["quantity"]
            
            # Format quantity for the order
            quantity_str = self._format_quantity(quantity, self.base_symbol)
            
            # Place the order
            result = self._place_single_order("buy", quantity_str, price, i+1)
            if result:
                buy_success_count += 1
                
        self.logger.info(f"Order placement summary:")
        self.logger.info(f"  Sell orders: {sell_success_count}/{len(sell_orders)} placed successfully")
        self.logger.info(f"  Buy orders: {buy_success_count}/{len(buy_orders)} placed successfully")
        
        return sell_success_count > 0 or buy_success_count > 0 

    def run(self, cancel_existing=True):
        """Run the strategy"""
        # Check balances first
        base_balance, quote_balance = self.check_balances()
        
        # Cancel existing orders if requested
        if cancel_existing:
            self.cancel_orders()
        
        # Generate signal
        signal = self.generate_signal()
        
        # Adjust orders based on available balances
        adjusted_signal = self.adjust_orders_for_balance(signal, base_balance, quote_balance)
        
        # Place orders
        self.place_orders(adjusted_signal)
        
    def check_balances(self):
        """Check account balances"""
        try:
            # Get base balance
            base_balance_str = self.client.get_currency_balance(self.account, self.base_symbol)
            base_balance = Decimal(base_balance_str.split()[0]) if base_balance_str else Decimal('0')
            
            # Get quote balance
            quote_balance_str = self.client.get_currency_balance(self.account, self.quote_symbol)
            quote_balance = Decimal(quote_balance_str.split()[0]) if quote_balance_str else Decimal('0')
            
            self.logger.info(f"Account balances: {base_balance} {self.base_symbol}, {quote_balance} {self.quote_symbol}")
            
            return base_balance, quote_balance
        except Exception as e:
            self.logger.error(f"Error checking balances: {e}")
            return Decimal('0'), Decimal('0')
            
    def adjust_orders_for_balance(self, signal, base_balance, quote_balance):
        """Adjust orders to fit within available balances"""
        if not signal:
            return signal
            
        sell_orders = signal.get("sell_orders", [])
        buy_orders = signal.get("buy_orders", [])
        
        # Calculate total required for all orders
        total_base_for_sell = sum(order["quantity"] for order in sell_orders)
        total_quote_for_buy = sum(order["order_value"] for order in buy_orders)
        
        self.logger.info(f"Required for orders: {total_base_for_sell} {self.base_symbol} for sell, {total_quote_for_buy} {self.quote_symbol} for buy")
        
        # Check if we have enough balance
        base_sufficient = base_balance >= total_base_for_sell
        quote_sufficient = quote_balance >= total_quote_for_buy
        
        if base_sufficient and quote_sufficient:
            self.logger.info("Sufficient balance for all orders")
            return signal
            
        adjusted_sell_orders = sell_orders
        adjusted_buy_orders = buy_orders
        
        # Adjust sell orders if needed
        if not base_sufficient and sell_orders:
            self.logger.warning(f"Insufficient {self.base_symbol} balance. Adjusting sell orders.")
            
            # Calculate scaling factor
            scale_factor = base_balance / total_base_for_sell
            
            # Apply a safety margin of 99% to avoid rounding issues
            scale_factor = scale_factor * Decimal('0.99')
            
            # Adjust each order
            adjusted_sell_orders = []
            for order in sell_orders:
                adjusted_quantity = order["quantity"] * scale_factor
                
                # Skip if below minimum
                if adjusted_quantity * order["price"] < self.min_quote_value:
                    continue
                    
                adjusted_sell_orders.append({
                    "price": order["price"],
                    "quantity": self.normalize_amount(adjusted_quantity),
                    "order_value": self.normalize_amount(adjusted_quantity * order["price"])
                })
                
            self.logger.info(f"Adjusted sell orders from {len(sell_orders)} to {len(adjusted_sell_orders)}")
            
        # Adjust buy orders if needed
        if not quote_sufficient and buy_orders:
            self.logger.warning(f"Insufficient {self.quote_symbol} balance. Adjusting buy orders.")
            
            # Calculate scaling factor
            scale_factor = quote_balance / total_quote_for_buy
            
            # Apply a safety margin of 99% to avoid rounding issues
            scale_factor = scale_factor * Decimal('0.99')
            
            # Adjust each order
            adjusted_buy_orders = []
            for order in buy_orders:
                adjusted_quantity = order["quantity"] * scale_factor
                
                # Skip if below minimum
                if adjusted_quantity * order["price"] < self.min_quote_value:
                    continue
                    
                adjusted_buy_orders.append({
                    "price": order["price"],
                    "quantity": self.normalize_amount(adjusted_quantity),
                    "order_value": self.normalize_amount(adjusted_quantity * order["price"])
                })
                
            self.logger.info(f"Adjusted buy orders from {len(buy_orders)} to {len(adjusted_buy_orders)}")
            
        return {
            "center_price": signal["center_price"],
            "sell_orders": adjusted_sell_orders,
            "buy_orders": adjusted_buy_orders
        }

    def on_price_update(self, new_price):
        """Handle price updates from the MarketPriceTrackerStrategy."""
        if new_price is None:
            self.logger.warning("Received None price update")
            return
        
        # Convert to Decimal if needed
        if not isinstance(new_price, Decimal):
            new_price = Decimal(str(new_price))
        
        # Check if the price change is significant
        current_price = self.get_market_price()
        if current_price is None:
            self.logger.info(f"Updating center price from None to {new_price}")
        else:
            price_change_percentage = abs(new_price - current_price) / current_price
            self.logger.info(f"Price update: {current_price} -> {new_price} ({float(price_change_percentage)*100:.2f}%)")
        
        # Store the new price
        self._market_price = new_price
        
        # Regenerate orders if needed
        # This could be controlled by a parameter
        if self.parameters.get('auto_update_on_price_change', True):
            self.logger.info("Regenerating orders due to price change")
            
            # Cancel existing orders
            self.cancel_orders()
            
            # Generate new signal
            signal = self.generate_signal()
            
            # Check balances and adjust orders
            base_balance, quote_balance = self.check_balances()
            adjusted_signal = self.adjust_orders_for_balance(signal, base_balance, quote_balance)
            
            # Place new orders
            self.place_orders(adjusted_signal) 