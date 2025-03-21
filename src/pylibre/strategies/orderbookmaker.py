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
                price = Decimal('84273.28')  # Updated to current BTC price
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
        
        self.logger.debug(f"Sell price range: {min_price} to {max_price} {self.quote_symbol}")
        
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
        
        self.logger.debug(f"Buy price range: {min_price} to {max_price} {self.quote_symbol}")
        
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

    def check_and_cancel_outdated_orders(self):
        """
        Check the orderbook for existing orders that are too far from the current market price and cancel them.
        This should be run before placing new orders to clean up any stale orders.
        
        Returns:
            tuple: A tuple containing (total_orders_found, outdated_orders_cancelled)
        """
        try:
            # Get current market price
            market_price = self.get_market_price()
            if market_price is None or market_price == Decimal('0'):
                self.logger.warning("Cannot check for outdated orders: No market price available")
                return 0, 0
            
            # Set threshold percentage (orders beyond this % from market price are considered outdated)
            # This should be slightly larger than our max spread to allow for normal spread orders
            price_threshold = self.max_spread_percentage * Decimal('1.5')
            
            # Log threshold
            self.logger.info(f"Checking for orders more than {float(price_threshold)*100:.2f}% away from current price {market_price}")
            
            # Fetch current orderbook
            order_book = self.dex.fetch_order_book(
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            # Track our counts
            total_orders = 0
            outdated_orders = 0
            
            # Check bids (buy orders)
            for bid in order_book["bids"]:
                if bid["account"] == self.account:
                    total_orders += 1
                    bid_price = Decimal(str(bid["price"]))
                    # Calculate how far this order is from market price (percentage)
                    price_deviation = abs(bid_price - market_price) / market_price
                    
                    # If it's too far, cancel it
                    if price_deviation > price_threshold:
                        self.logger.info(f"Cancelling outdated BUY order at {bid_price} ({float(price_deviation)*100:.2f}% from market price)")
                        try:
                            self.dex.cancel_order(
                                account=self.account,
                                order_id=bid['identifier'],
                                quote_symbol=self.quote_symbol,
                                base_symbol=self.base_symbol
                            )
                            outdated_orders += 1
                        except Exception as e:
                            self.logger.error(f"Error cancelling outdated buy order: {e}")
            
            # Check offers (sell orders)
            for offer in order_book["offers"]:
                if offer["account"] == self.account:
                    total_orders += 1
                    offer_price = Decimal(str(offer["price"]))
                    # Calculate how far this order is from market price (percentage)
                    price_deviation = abs(offer_price - market_price) / market_price
                    
                    # If it's too far, cancel it
                    if price_deviation > price_threshold:
                        self.logger.info(f"Cancelling outdated SELL order at {offer_price} ({float(price_deviation)*100:.2f}% from market price)")
                        try:
                            self.dex.cancel_order(
                                account=self.account,
                                order_id=offer['identifier'],
                                quote_symbol=self.quote_symbol,
                                base_symbol=self.base_symbol
                            )
                            outdated_orders += 1
                        except Exception as e:
                            self.logger.error(f"Error cancelling outdated sell order: {e}")
            
            # Log summary
            if outdated_orders > 0:
                self.logger.info(f"Cancelled {outdated_orders} outdated orders out of {total_orders} total orders")
            else:
                self.logger.info(f"No outdated orders found among {total_orders} total orders")
            
            return total_orders, outdated_orders
        
        except Exception as e:
            self.logger.error(f"Error checking for outdated orders: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return 0, 0

    def run(self, cancel_existing=None):
        """Run the strategy"""
        # Check balances first
        base_balance, quote_balance = self.check_balances()
        
        # Determine cancel behavior - parameter overrides config
        if cancel_existing is None:
            # Use configuration if parameter not provided
            cancel_existing = self.parameters.get('cancel_existing', True)
        
        # Check for outdated orders and cancel them first
        if not cancel_existing:
            self.logger.info("Checking for outdated orders before running strategy")
            total_orders, cancelled_orders = self.check_and_cancel_outdated_orders()
            self.logger.info(f"Found {total_orders} active orders, cancelled {cancelled_orders} outdated ones")
        else:
            # Cancel all existing orders if requested
            self.logger.info("Cancelling all existing orders as requested")
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
            # For dry run mode, use simulated high balances
            if self.parameters.get('dry_run', False):
                # Use high values to ensure all orders can be placed in simulation
                base_balance = Decimal('1')  # 1 BTC or other base asset
                quote_balance = Decimal('100000')  # 100,000 USDT or other quote asset
                self.logger.info(f"Using simulated balances for dry run: {base_balance} {self.base_symbol}, {quote_balance} {self.quote_symbol}")
                return base_balance, quote_balance
            
            # Get base balance
            base_balance_result = self.client.get_currency_balance(self.account, self.base_symbol)
            base_balance = Decimal('0')
            
            # Handle different return types from get_currency_balance
            if isinstance(base_balance_result, str) and ' ' in base_balance_result:
                base_balance = Decimal(base_balance_result.split()[0])
            elif isinstance(base_balance_result, dict) and 'balance' in base_balance_result:
                # Handle dict return format
                balance_str = base_balance_result.get('balance', '0')
                if isinstance(balance_str, str) and ' ' in balance_str:
                    base_balance = Decimal(balance_str.split()[0])
                else:
                    base_balance = Decimal(str(balance_str))
            elif base_balance_result:
                # Try direct conversion as fallback
                base_balance = Decimal(str(base_balance_result))
            
            # Get quote balance
            quote_balance_result = self.client.get_currency_balance(self.account, self.quote_symbol)
            quote_balance = Decimal('0')
            
            # Handle different return types from get_currency_balance
            if isinstance(quote_balance_result, str) and ' ' in quote_balance_result:
                quote_balance = Decimal(quote_balance_result.split()[0])
            elif isinstance(quote_balance_result, dict) and 'balance' in quote_balance_result:
                # Handle dict return format
                balance_str = quote_balance_result.get('balance', '0')
                if isinstance(balance_str, str) and ' ' in balance_str:
                    quote_balance = Decimal(balance_str.split()[0])
                else:
                    quote_balance = Decimal(str(balance_str))
            elif quote_balance_result:
                # Try direct conversion as fallback
                quote_balance = Decimal(str(quote_balance_result))
            
            self.logger.info(f"Account balances: {base_balance} {self.base_symbol}, {quote_balance} {self.quote_symbol}")
            
            return base_balance, quote_balance
        except Exception as e:
            self.logger.error(f"Error checking balances: {e}")
            
            # If error occurs, return minimum viable balances
            if self.parameters.get('dry_run', False):
                # Use high values for dry run mode
                return Decimal('1'), Decimal('100000')
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
        try:
            if new_price is None:
                self.logger.warning("Received None price update, ignoring")
                return
            
            # Convert to Decimal if needed
            if not isinstance(new_price, Decimal):
                new_price = Decimal(str(new_price))
            
            # Check if the price is reasonable (validation)
            if new_price <= 0:
                self.logger.warning(f"Ignoring invalid price update: {new_price}")
                return
                
            # Check if the price change is significant
            current_price = self.get_market_price()
            if current_price is None or current_price == Decimal('0'):
                self.logger.info(f"Setting initial center price to {new_price}")
            else:
                # Calculate price change percentage
                price_change_percentage = abs(new_price - current_price) / current_price
                change_pct = float(price_change_percentage) * 100
                
                # Only log at INFO level for significant changes
                if change_pct >= 0.5:  # 0.5% threshold for INFO logging
                    self.logger.info(f"Price update: {current_price} -> {new_price} ({change_pct:.2f}%)")
                else:
                    self.logger.debug(f"Minor price update: {current_price} -> {new_price} ({change_pct:.2f}%)")
                
                # Skip if change is too dramatic (safety check)
                if change_pct > 20.0:  # 20% threshold
                    self.logger.warning(f"⚠️ Dramatic price change detected ({change_pct:.2f}%), validating before applying")
                    
                    # Additional validation could be added here
                    confirm_dramatic_change = self.parameters.get('confirm_dramatic_change', False)
                    if not confirm_dramatic_change:
                        self.logger.warning(f"Ignoring dramatic price change. Set 'confirm_dramatic_change: true' to allow.")
                        return
                    
                    self.logger.warning(f"Proceeding with dramatic price change as configured")
            
            # Store the new price
            self._market_price = new_price
            
            # Regenerate orders if needed based on config
            if self.parameters.get('auto_update_on_price_change', True):
                self.logger.debug("Regenerating orders due to price change")
                
                # Determine cancel behavior based on config
                cancel_existing = self.parameters.get('cancel_existing_on_price_change', False)
                
                if cancel_existing:
                    # Cancel all existing orders
                    self.logger.info("Cancelling all existing orders due to price change")
                    self.cancel_orders()
                else:
                    # Only cancel outdated orders
                    self.logger.debug("Checking for outdated orders due to price change")
                    total_orders, cancelled_orders = self.check_and_cancel_outdated_orders()
                    
                    # Only log at INFO level if we actually cancelled orders
                    if cancelled_orders > 0:
                        self.logger.info(f"Price update: Cancelled {cancelled_orders} outdated orders out of {total_orders} active orders")
                
                # Generate new signal with updated price
                signal = self.generate_signal()
                
                # Check balances and adjust orders
                base_balance, quote_balance = self.check_balances()
                adjusted_signal = self.adjust_orders_for_balance(signal, base_balance, quote_balance)
                
                # Place new orders
                self.place_orders(adjusted_signal)
        except Exception as e:
            self.logger.error(f"Error handling price update: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            # Continue running despite error

    def _place_single_order(self, order_type, quantity, price, index=0):
        """Place a single order with formatted parameters."""
        try:
            # Add randomness to price (within 0.01%) to avoid duplicates
            if self.parameters.get('price_randomization', True):
                random_factor = Decimal(str(0.9999 + random.random() * 0.0002))
                price = price * random_factor
                price = self.normalize_price(price)
            
            # Ensure quantity is properly formatted
            if isinstance(quantity, str) and ' ' in quantity:
                quantity_value = Decimal(quantity.split()[0])
            else:
                quantity_value = Decimal(str(quantity))
            
            # Calculate order total value
            total_value = price * quantity_value
            
            # Debug log only for detailed order info
            self.logger.debug(f"Order limits for {self.base_symbol}: min={self.min_base_value}, max={self.max_base_value}")
            
            # Place the order using the dex client (not the base client)
            # Initialize dex client if not already done
            if not hasattr(self, 'dex'):
                from pylibre.dex import DexClient
                self.dex = DexClient(self.client)
            
            # Use the dex client to place the order
            result = self.dex.place_order(
                account=self.account,
                order_type=order_type,
                quantity=quantity_value,
                price=price,
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            # Log result - detailed info at INFO level
            if result:
                # Log at debug level to reduce noise
                if order_type == 'sell':
                    self.logger.debug(f"💰 {self.account}: SELL {quantity_value} {self.base_symbol} at {price} {self.quote_symbol} (Total: {total_value} {self.quote_symbol})")
                else:
                    self.logger.debug(f"💸 {self.account}: BUY {quantity_value} {self.base_symbol} at {price} {self.quote_symbol} (Total: {total_value} {self.quote_symbol})")
                    
                return True
            else:
                self.logger.warning(f"Failed to place {order_type.upper()} order: {quantity_value} {self.base_symbol} at {price} {self.quote_symbol}")
                return False
        except Exception as e:
            self.logger.error(f"Error placing {order_type} order {index}: {e}")
            return False 