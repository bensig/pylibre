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
        
        # Apply center_adjustment_factor if provided to adjust towards binance price
        # This helps move the DEX price closer to external price sources
        adjustment_factor = self.parameters.get('center_adjustment_factor')
        if adjustment_factor is not None:
            # Get external price if available
            external_price = self.coordinator_market_price if hasattr(self, 'coordinator_market_price') else None
            
            # If we have both an external price and our center price differs, adjust it
            if external_price is not None and external_price > Decimal('0'):
                # Convert to decimal if needed
                if not isinstance(external_price, Decimal):
                    external_price = Decimal(str(external_price))
                
                # Calculate the difference and apply adjustment factor
                if external_price != center_price and adjustment_factor > 0:
                    adjustment_factor = Decimal(str(adjustment_factor))
                    price_diff = external_price - center_price
                    adjusted_price = center_price + (price_diff * adjustment_factor)
                    
                    self.logger.info(f"Adjusting center price: {center_price} -> {adjusted_price} " +
                        f"(external: {external_price}, factor: {adjustment_factor})")
                    
                    center_price = adjusted_price
        
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
            
            # Get configurable threshold from parameters, with fallback to default
            # This determines how far from market price an order can be before it's cancelled
            configured_threshold = self.parameters.get('price_deviation_threshold')
            if configured_threshold is not None:
                price_threshold = Decimal(str(configured_threshold))
                self.logger.debug(f"Using configured price deviation threshold: {float(price_threshold)*100:.2f}%")
            else:
                # Default threshold is 1.5x the max spread
                price_threshold = self.max_spread_percentage * Decimal('1.5')
                self.logger.debug(f"Using default price deviation threshold: {float(price_threshold)*100:.2f}%")
            
            # Log threshold
            self.logger.info(f"Checking for orders more than {float(price_threshold)*100:.2f}% away from current price {market_price}")
            
            # Fetch current orderbook
            order_book = self.dex.fetch_order_book(
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            # Track our counts
            total_orders = 0
            outdated_orders_list = []
            
            # Check bids (buy orders)
            for bid in order_book["bids"]:
                if bid["account"] == self.account:
                    total_orders += 1
                    bid_price = Decimal(str(bid["price"]))
                    # Calculate how far this order is from market price (percentage)
                    price_deviation = abs(bid_price - market_price) / market_price
                    
                    # If it's too far, mark for cancellation
                    if price_deviation > price_threshold:
                        self.logger.info(f"Marking outdated BUY order at {bid_price} ({float(price_deviation)*100:.2f}% from market price)")
                        outdated_orders_list.append({
                            "type": "bid",
                            "price": bid_price,
                            "identifier": bid["identifier"],
                            "deviation": price_deviation
                        })
            
            # Check offers (sell orders)
            for offer in order_book["offers"]:
                if offer["account"] == self.account:
                    total_orders += 1
                    offer_price = Decimal(str(offer["price"]))
                    # Calculate how far this order is from market price (percentage)
                    price_deviation = abs(offer_price - market_price) / market_price
                    
                    # If it's too far, mark for cancellation
                    if price_deviation > price_threshold:
                        self.logger.info(f"Marking outdated SELL order at {offer_price} ({float(price_deviation)*100:.2f}% from market price)")
                        outdated_orders_list.append({
                            "type": "offer",
                            "price": offer_price,
                            "identifier": offer["identifier"],
                            "deviation": price_deviation
                        })
            
            # If no outdated orders, return early
            if not outdated_orders_list:
                self.logger.info(f"No outdated orders found among {total_orders} total orders")
                return total_orders, 0
                
            # Sort by deviation to cancel the most outdated orders first
            outdated_orders_list.sort(key=lambda x: x["deviation"], reverse=True)
            
            # Get batch parameters
            batch_size = int(self.parameters.get('cancellation_batch_size', 10))
            delay_ms = int(self.parameters.get('cancellation_delay_ms', 200))
            
            # Log summary before cancellation
            self.logger.info(f"Found {len(outdated_orders_list)} outdated orders to cancel out of {total_orders} total orders")
            
            # Cancel in batches with delay
            cancelled_orders = 0
            failed_orders = 0
            
            # Process in batches with delay between batches
            for i in range(0, len(outdated_orders_list), batch_size):
                batch = outdated_orders_list[i:i+batch_size]
                
                # Log batch progress
                batch_num = (i // batch_size) + 1
                total_batches = (len(outdated_orders_list) + batch_size - 1) // batch_size
                self.logger.info(f"Processing outdated order cancellation batch {batch_num}/{total_batches} ({len(batch)} orders)")
                
                # Process each order in the batch
                for order in batch:
                    try:
                        result = self.dex.cancel_order(
                            account=self.account,
                            order_id=order["identifier"],
                            quote_symbol=self.quote_symbol,
                            base_symbol=self.base_symbol
                        )
                        
                        if result.get("success", False):
                            cancelled_orders += 1
                            self.logger.debug(f"Cancelled outdated {order['type']} order {order['identifier']} at price {order['price']}")
                        else:
                            failed_orders += 1
                            error = result.get("error", "Unknown error")
                            self.logger.warning(f"Failed to cancel outdated {order['type']} order {order['identifier']}: {error}")
                    except Exception as e:
                        failed_orders += 1
                        self.logger.error(f"Error cancelling outdated {order['type']} order {order['identifier']}: {e}")
                
                # Add delay between batches to avoid rate limiting
                if i + batch_size < len(outdated_orders_list) and delay_ms > 0:
                    self.logger.debug(f"Waiting {delay_ms}ms before next cancellation batch")
                    time.sleep(delay_ms / 1000)
            
            # Log summary
            self.logger.info(f"Cancelled {cancelled_orders} outdated orders, {failed_orders} failed")
            
            return total_orders, cancelled_orders
        
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

    def on_price_update(self, new_price: Decimal) -> None:
        """Handle price updates from other strategies."""
        old_price = self._market_price
        
        # Store the coordinator's market price for reference
        self.coordinator_market_price = new_price
        
        # Update our internal price
        self._market_price = new_price
        
        # Calculate price change percentage
        if old_price is not None and old_price > Decimal('0'):
            price_change_pct = abs(new_price - old_price) / old_price
            self.logger.info(f"Price updated from {old_price} to {new_price} {self.quote_symbol} (change: {float(price_change_pct)*100:.2f}%)")
            
            # If price change is significant, run the strategy to update orders
            # The significance threshold can be adjusted based on market volatility
            significance_threshold = Decimal('0.001')  # 0.1% default
            
            # Allow strategy config to override the threshold
            configured_threshold = self.parameters.get('price_update_significance_threshold')
            if configured_threshold is not None:
                significance_threshold = Decimal(str(configured_threshold))
            
            if price_change_pct > significance_threshold:
                self.logger.info(f"Price change of {float(price_change_pct)*100:.2f}% exceeds threshold of {float(significance_threshold)*100:.2f}% - updating orders")
                # Only check and cancel outdated orders, don't cancel all
                self.run(cancel_existing=False)
            else:
                self.logger.debug(f"Price change of {float(price_change_pct)*100:.2f}% below threshold - no immediate order update needed")
        else:
            self.logger.info(f"Initial price set to {new_price} {self.quote_symbol}")

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

    def cancel_orders(self):
        """Cancel all existing orders for the trading pair"""
        try:
            self.logger.info(f"Cancelling all {self.base_symbol}/{self.quote_symbol} orders for {self.account}")
            
            # Get the current orderbook
            order_book = self.dex.fetch_order_book(
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            # Create a list of all orders that need to be cancelled
            orders_to_cancel = []
            
            # Add bids (buy orders)
            for bid in order_book["bids"]:
                if bid["account"] == self.account:
                    orders_to_cancel.append({
                        "type": "bid",
                        "price": bid["price"],
                        "identifier": bid["identifier"]
                    })
            
            # Add offers (sell orders)
            for offer in order_book["offers"]:
                if offer["account"] == self.account:
                    orders_to_cancel.append({
                        "type": "offer",
                        "price": offer["price"],
                        "identifier": offer["identifier"]
                    })
            
            total_orders = len(orders_to_cancel)
            cancelled_orders = 0
            failed_orders = 0
            
            if total_orders == 0:
                self.logger.info("No orders found to cancel")
                return
            
            self.logger.info(f"Found {total_orders} orders to cancel")
            
            # Get batch size and delay from parameters or use defaults
            batch_size = int(self.parameters.get('cancellation_batch_size', 10))
            delay_ms = int(self.parameters.get('cancellation_delay_ms', 200))
            
            # Process in batches with delay between batches
            for i in range(0, len(orders_to_cancel), batch_size):
                batch = orders_to_cancel[i:i+batch_size]
                
                # Log batch progress
                batch_num = (i // batch_size) + 1
                total_batches = (total_orders + batch_size - 1) // batch_size
                self.logger.info(f"Processing cancellation batch {batch_num}/{total_batches} ({len(batch)} orders)")
                
                # Process each order in the batch
                for order in batch:
                    try:
                        result = self.dex.cancel_order(
                            account=self.account,
                            order_id=order["identifier"],
                            quote_symbol=self.quote_symbol,
                            base_symbol=self.base_symbol
                        )
                        
                        if result.get("success", False):
                            cancelled_orders += 1
                            self.logger.debug(f"Cancelled {order['type']} order {order['identifier']} at price {order['price']}")
                        else:
                            failed_orders += 1
                            error = result.get("error", "Unknown error")
                            self.logger.warning(f"Failed to cancel {order['type']} order {order['identifier']}: {error}")
                    except Exception as e:
                        failed_orders += 1
                        self.logger.error(f"Error cancelling {order['type']} order {order['identifier']}: {e}")
                
                # Add delay between batches to avoid rate limiting
                if i + batch_size < len(orders_to_cancel) and delay_ms > 0:
                    self.logger.debug(f"Waiting {delay_ms}ms before next cancellation batch")
                    time.sleep(delay_ms / 1000)
            
            self.logger.info(f"Cancelled {cancelled_orders} orders, {failed_orders} failed")
            
        except Exception as e:
            self.logger.error(f"Error in cancel_orders: {e}")
            import traceback
            self.logger.error(traceback.format_exc()) 