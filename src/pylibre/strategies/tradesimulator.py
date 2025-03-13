from .templates.base_strategy import BaseStrategy
import time
import random
from decimal import Decimal, ROUND_DOWN
from typing import Dict, Any, List, Optional, Tuple
import logging

class TradeSimulatorStrategy(BaseStrategy):
    """
    TradeSimulatorStrategy creates the appearance of market activity by
    simulating trades between accounts. It places orders with one account
    and then fills them with another account to create trade history.
    """
    
    def __init__(self, client, account, base_symbol, quote_symbol, parameters, logger=None):
        """Initialize the strategy with parameters."""
        super().__init__(client, account, base_symbol, quote_symbol, parameters, logger)
        
        # Primary account is the one passed to the constructor
        self.primary_account = account
        
        # Secondary account for the other side of trades
        # First check for counterparty_account (new parameter name)
        # Then fall back to secondary_account (old parameter name)
        # Finally default to the primary account (for backward compatibility)
        self.secondary_account = parameters.get('counterparty_account', 
                                  parameters.get('secondary_account', self.primary_account))
        
        # Strategy parameters with defaults
        self.trade_frequency = parameters.get('trade_frequency', 'medium')
        self.trade_size_variation = parameters.get('trade_size_variation', 'medium')
        self.price_range_percentage = Decimal(str(parameters.get('price_range_percentage', 0.01)))
        self.cycle_interval_ms = int(parameters.get('cycle_interval_ms', 30000))  # 30 seconds default
        self.trades_per_cycle = int(parameters.get('trades_per_cycle', 1))
        self.min_trade_size = Decimal(str(parameters.get('min_trade_size', 0.0)))
        self.max_trade_size = Decimal(str(parameters.get('max_trade_size', 0.0)))
        self.trade_pattern = parameters.get('trade_pattern', 'random')  # random, trend, reversion
        self.trend_direction = parameters.get('trend_direction', 'neutral')  # up, down, neutral
        self.trend_strength = Decimal(str(parameters.get('trend_strength', 0.5)))  # 0.0 to 1.0
        
        # Define frequency factors based on activity level
        self.frequency_factors = {
            'low': {'interval': 60000, 'trades': 1},      # 1 trade per minute
            'medium': {'interval': 30000, 'trades': 1},   # 2 trades per minute
            'high': {'interval': 15000, 'trades': 2}      # 8 trades per minute
        }
        
        # Define size variation factors based on level
        self.size_variation_factors = {
            'low': 0.1,      # 10% variation
            'medium': 0.25,  # 25% variation
            'high': 0.5      # 50% variation
        }
        
        # Override defaults with frequency settings if provided
        if self.trade_frequency in self.frequency_factors:
            factor = self.frequency_factors[self.trade_frequency]
            if 'cycle_interval_ms' not in parameters:
                self.cycle_interval_ms = factor['interval']
            if 'trades_per_cycle' not in parameters:
                self.trades_per_cycle = factor['trades']
        
        # Get size variation factor
        self.size_variation_factor = self.size_variation_factors.get(
            self.trade_size_variation, 0.25
        )
        
        # Initialize trade history for patterns
        self.trade_history = []
        self.last_trade_price = None
        
        # Log initialization
        self.logger.info(f"Initialized TradeSimulatorStrategy with:")
        self.logger.info(f"  Primary Account: {self.primary_account}")
        self.logger.info(f"  Secondary Account: {self.secondary_account}")
        self.logger.info(f"  Trading pair: {base_symbol}/{quote_symbol}")
        self.logger.info(f"  Trade frequency: {self.trade_frequency}")
        self.logger.info(f"  Cycle interval: {self.cycle_interval_ms}ms")
        self.logger.info(f"  Trades per cycle: {self.trades_per_cycle}")
        self.logger.info(f"  Trade pattern: {self.trade_pattern}")
        self.logger.info(f"  Price range: ±{float(self.price_range_percentage*Decimal('100'))}%")
    
    def _get_order_book(self) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch the current order book."""
        try:
            return self.dex.fetch_order_book(
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
        except Exception as e:
            self.logger.error(f"Error fetching order book: {e}")
            return {"bids": [], "offers": []}
    
    def _filter_orders_by_account(self, order_book: Dict[str, List[Dict[str, Any]]], account: str) -> List[Dict[str, Any]]:
        """Filter orders belonging to the specified account."""
        our_orders = []
        
        # Filter bids (buy orders)
        for bid in order_book.get("bids", []):
            if bid.get("account") == account:
                bid["order_type"] = "buy"
                our_orders.append(bid)
        
        # Filter offers (sell orders)
        for offer in order_book.get("offers", []):
            if offer.get("account") == account:
                offer["order_type"] = "sell"
                our_orders.append(offer)
                
        return our_orders
    
    def _select_orders_to_fill(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Select orders to fill based on strategy parameters."""
        if not orders:
            return []
        
        # Sort orders by price (ascending for sells, descending for buys)
        sell_orders = sorted(
            [o for o in orders if o["order_type"] == "sell"],
            key=lambda x: Decimal(str(x["price"]))
        )
        
        buy_orders = sorted(
            [o for o in orders if o["order_type"] == "buy"],
            key=lambda x: Decimal(str(x["price"])),
            reverse=True
        )
        
        # Get market price or estimate from order book
        market_price = self.get_market_price()
        if market_price is None:
            if sell_orders and buy_orders:
                # Use midpoint between best bid and ask
                best_bid = Decimal(str(buy_orders[0]["price"]))
                best_ask = Decimal(str(sell_orders[0]["price"]))
                market_price = (best_bid + best_ask) / Decimal('2')
            elif sell_orders:
                market_price = Decimal(str(sell_orders[0]["price"]))
            elif buy_orders:
                market_price = Decimal(str(buy_orders[0]["price"]))
            else:
                self.logger.warning("No orders in book and no market price available")
                return []
        
        # Filter orders within price range of market price
        price_range = market_price * self.price_range_percentage
        min_price = market_price - price_range
        max_price = market_price + price_range
        
        filtered_orders = []
        
        for order in sell_orders + buy_orders:
            price = Decimal(str(order["price"]))
            if min_price <= price <= max_price:
                filtered_orders.append(order)
        
        # Select orders based on pattern
        if self.trade_pattern == "trend":
            # For trend following, prioritize orders in trend direction
            if self.trend_direction == "up":
                # Prioritize buy orders when trending up
                filtered_orders.sort(
                    key=lambda x: (0 if x["order_type"] == "buy" else 1, 
                                  abs(Decimal(str(x["price"])) - market_price))
                )
            elif self.trend_direction == "down":
                # Prioritize sell orders when trending down
                filtered_orders.sort(
                    key=lambda x: (0 if x["order_type"] == "sell" else 1,
                                  abs(Decimal(str(x["price"])) - market_price))
                )
        elif self.trade_pattern == "reversion":
            # For mean reversion, prioritize orders against recent trend
            if self.last_trade_price and len(self.trade_history) >= 2:
                # Both values are already stored as float in trade_history, so comparison is safe
                # Ensure we're comparing the same types
                last_price = float(self.trade_history[-1])
                prev_price = float(self.trade_history[-2])
                recent_direction = "up" if last_price > prev_price else "down"
                if recent_direction == "up":
                    # Prioritize sell orders to revert the uptrend
                    filtered_orders.sort(
                        key=lambda x: (0 if x["order_type"] == "sell" else 1,
                                      abs(Decimal(str(x["price"])) - market_price))
                    )
                else:
                    # Prioritize buy orders to revert the downtrend
                    filtered_orders.sort(
                        key=lambda x: (0 if x["order_type"] == "buy" else 1,
                                      abs(Decimal(str(x["price"])) - market_price))
                    )
        
        # Randomly select from filtered orders, with bias toward the beginning of the list
        selected_orders = []
        num_to_select = min(self.trades_per_cycle, len(filtered_orders))
        
        if num_to_select > 0:
            # Use weighted random selection favoring orders at the beginning of the list
            # These are just used for selection, so keeping as float is fine
            weights = [1.0/(i+1) for i in range(len(filtered_orders))]
            total_weight = sum(weights)
            normalized_weights = [w/total_weight for w in weights]
            
            # Select orders without replacement
            remaining_orders = filtered_orders.copy()
            remaining_weights = normalized_weights.copy()
            
            for _ in range(num_to_select):
                if not remaining_orders:
                    break
                    
                # Select an order based on weights
                selected_idx = random.choices(
                    range(len(remaining_orders)), 
                    weights=remaining_weights, 
                    k=1
                )[0]
                
                selected_orders.append(remaining_orders[selected_idx])
                
                # Remove the selected order and its weight
                remaining_orders.pop(selected_idx)
                remaining_weights.pop(selected_idx)
                
                # Renormalize weights if any remain
                if remaining_weights:
                    total = sum(remaining_weights)
                    remaining_weights = [w/total for w in remaining_weights]
        
        return selected_orders
    
    def _calculate_fill_quantity(self, order: Dict[str, Any]) -> Decimal:
        """Calculate the quantity to use when filling an order."""
        try:
            # Parse the original quantity - ensure it's a Decimal
            original_quantity = Decimal(str(order["quantity"]))
            
            # Apply size variation
            if self.size_variation_factor > 0:
                # Calculate min and max fill amounts
                size_var_factor = Decimal(str(self.size_variation_factor))  # Ensure Decimal
                min_fill = original_quantity * (Decimal('1') - size_var_factor)
                max_fill = original_quantity
                
                # Ensure we respect min/max trade size if specified
                if isinstance(self.min_trade_size, float):
                    min_trade_size = Decimal(str(self.min_trade_size))
                else:
                    min_trade_size = self.min_trade_size
                    
                if isinstance(self.max_trade_size, float):
                    max_trade_size = Decimal(str(self.max_trade_size))
                else:
                    max_trade_size = self.max_trade_size
                    
                if min_trade_size > Decimal('0'):
                    min_fill = max(min_fill, min_trade_size)
                if max_trade_size > Decimal('0'):
                    max_fill = min(max_fill, max_trade_size)
                
                # Ensure min doesn't exceed max
                min_fill = min(min_fill, max_fill)
                
                # Generate random fill quantity between min and max
                # Convert to float for random.uniform then back to Decimal safely
                min_fill_float = float(min_fill)
                max_fill_float = float(max_fill)
                fill_quantity = Decimal(str(random.uniform(min_fill_float, max_fill_float)))
            else:
                # Use full quantity
                fill_quantity = original_quantity
            
            # Normalize to appropriate precision
            return self.normalize_amount(fill_quantity)
            
        except Exception as e:
            self.logger.error(f"Error calculating fill quantity: {e}")
            return Decimal('0')
    
    def _fill_order(self, order: Dict[str, Any], retry_count: int = 0) -> bool:
        """Fill an order by placing a matching order from the secondary account.
        
        Args:
            order: The order to fill
            retry_count: Current retry attempt (max 3)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            order_id = order.get("identifier")
            order_type = order.get("order_type")
            price = Decimal(str(order.get("price", "0")))
            
            # Validate price
            if price <= Decimal('0'):
                self.logger.warning(f"Invalid price in order {order_id}: {price}")
                return False
            
            # Calculate fill quantity
            fill_quantity = self._calculate_fill_quantity(order)
            if fill_quantity <= Decimal('0'):
                self.logger.warning(f"Invalid fill quantity calculated: {fill_quantity}")
                return False
            
            # Determine the matching order type
            matching_type = "buy" if order_type == "sell" else "sell"
            
            # Format quantity with correct precision
            quantity_str = self._format_quantity(fill_quantity, self.base_symbol)
            
            # Log the fill attempt
            self.logger.info(
                f"Filling {order_type} order {order_id} with {matching_type} order: "
                f"{quantity_str} {self.base_symbol} @ {price} {self.quote_symbol}"
            )
            
            # Check account balances before placing order
            if not self._verify_sufficient_balance(self.secondary_account, matching_type, fill_quantity, price):
                self.logger.warning(f"Insufficient balance for {self.secondary_account} to place {matching_type} order")
                return False
            
            # Place the matching order using the secondary account
            result = self.dex.place_order(
                account=self.secondary_account,
                order_type=matching_type,
                quantity=quantity_str,
                price=str(price),
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            # Check result
            if isinstance(result, dict) and result.get("success") is False:
                error_msg = result.get("error", "Unknown error")
                self.logger.error(f"Failed to fill order {order_id}: {error_msg}")
                
                # Handle specific error conditions
                if "insufficient balance" in str(error_msg).lower():
                    self.logger.warning(f"Insufficient balance detected for {self.secondary_account}")
                    return False
                elif "minimum order" in str(error_msg).lower():
                    self.logger.warning(f"Order size too small: {quantity_str} {self.base_symbol}")
                    return False
                elif retry_count < 3:
                    # Wait briefly and retry with slightly modified parameters
                    time.sleep(1)
                    self.logger.info(f"Retrying fill for order {order_id} (attempt {retry_count + 1}/3)")
                    
                    # Adjust quantity slightly for retry
                    adjusted_order = order.copy()
                    # Convert to Decimal, perform calculation, then convert back to same type as original
                    original_quantity = Decimal(str(order.get("quantity", "0")))
                    adjustment_factor = Decimal('0.95')
                    adjusted_quantity = original_quantity * adjustment_factor
                    # If the original was a float, convert back to float
                    if isinstance(order.get("quantity", 0.0), float):
                        adjusted_order["quantity"] = float(adjusted_quantity)
                    else:
                        adjusted_order["quantity"] = adjusted_quantity
                    return self._fill_order(adjusted_order, retry_count + 1)
                else:
                    self.logger.error(f"Max retries reached for order {order_id}")
                    return False
            elif result:
                self.logger.info(f"Successfully filled order {order_id}")
                
                # Record trade price for pattern analysis
                self.last_trade_price = price
                # Store price as float in trade_history for consistent comparisons
                # Ensure price is converted to float properly
                try:
                    self.trade_history.append(float(price))
                except (ValueError, TypeError):
                    # If conversion fails, convert to string first then to float
                    self.trade_history.append(float(str(price)))
                
                # Keep history limited to last 100 trades
                if len(self.trade_history) > 100:
                    self.trade_history = self.trade_history[-100:]
                
                return True
            else:
                self.logger.error(f"Failed to fill order {order_id} with unknown error")
                return False
                
        except Exception as e:
            self.logger.error(f"Error filling order: {e}")
            return False
            
    def _verify_sufficient_balance(self, account: str, order_type: str, quantity: Decimal, price: Decimal) -> bool:
        """Verify that the account has sufficient balance to place the order.
        
        Args:
            account: Account to check
            order_type: 'buy' or 'sell'
            quantity: Order quantity
            price: Order price
            
        Returns:
            bool: True if sufficient balance, False otherwise
        """
        try:
            # Get account balances
            balances = self.dex.get_account_balances(account)
            if not balances:
                self.logger.warning(f"Could not retrieve balances for account {account}")
                return True  # Assume sufficient balance if we can't check
                
            # For buy orders, check quote currency balance
            if order_type == "buy":
                # Ensure both quantity and price are Decimal for multiplication
                qty_dec = Decimal(str(quantity)) if not isinstance(quantity, Decimal) else quantity
                price_dec = Decimal(str(price)) if not isinstance(price, Decimal) else price
                required_amount = qty_dec * price_dec
                available = Decimal('0')
                
                for balance in balances:
                    if balance.get("symbol") == self.quote_symbol:
                        available = Decimal(str(balance.get("amount", "0")))
                        break
                        
                if available < required_amount:
                    self.logger.warning(
                        f"Insufficient {self.quote_symbol} balance for buy order: "
                        f"required {required_amount}, available {available}"
                    )
                    return False
            
            # For sell orders, check base currency balance
            elif order_type == "sell":
                # Ensure quantity is Decimal
                required_amount = Decimal(str(quantity)) if not isinstance(quantity, Decimal) else quantity
                available = Decimal('0')
                
                for balance in balances:
                    if balance.get("symbol") == self.base_symbol:
                        available = Decimal(str(balance.get("amount", "0")))
                        break
                        
                if available < required_amount:
                    self.logger.warning(
                        f"Insufficient {self.base_symbol} balance for sell order: "
                        f"required {required_amount}, available {available}"
                    )
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking balance: {e}")
            return True  # Assume sufficient balance if check fails
    
    def _place_new_order(self, order_type: str, retry_count: int = 0) -> bool:
        """Place a new order from the primary account.
        
        Args:
            order_type: Type of order ('buy' or 'sell')
            retry_count: Current retry attempt (max 3)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get market price
            market_price = self.get_market_price()
            if market_price is None:
                self.logger.warning("Cannot place new order: No market price available")
                return False
            
            # Calculate price with variation based on pattern
            # Ensure both values are Decimal for calculation
            market_price_dec = Decimal(str(market_price)) if isinstance(market_price, float) else market_price
            price_range_pct = Decimal(str(self.price_range_percentage)) if isinstance(self.price_range_percentage, float) else self.price_range_percentage
            price_variation = market_price_dec * price_range_pct
            
            if self.trade_pattern == "trend":
                # For trend following, bias price in trend direction
                if self.trend_direction == "up":
                    # Higher prices for uptrend
                    min_var = Decimal('0')
                    max_var = price_variation
                elif self.trend_direction == "down":
                    # Lower prices for downtrend
                    min_var = -price_variation
                    max_var = Decimal('0')
                else:
                    # Neutral trend
                    min_var = -price_variation / Decimal('2')
                    max_var = price_variation / Decimal('2')
            elif self.trade_pattern == "reversion":
                # For mean reversion, bias against recent movement
                if self.last_trade_price and len(self.trade_history) >= 2:
                    # Both values are already stored as float in trade_history, so comparison is safe
                    recent_direction = "up" if self.trade_history[-1] > self.trade_history[-2] else "down"
                    if recent_direction == "up":
                        # Lower prices to revert uptrend
                        min_var = -price_variation
                        max_var = Decimal('0')
                    else:
                        # Higher prices to revert downtrend
                        min_var = Decimal('0')
                        max_var = price_variation
                else:
                    # No history, use random variation
                    min_var = -price_variation / Decimal('2')
                    max_var = price_variation / Decimal('2')
            else:
                # Random pattern
                min_var = -price_variation / Decimal('2')
                max_var = price_variation / Decimal('2')
            
            # Ensure min doesn't exceed max
            min_var = min(min_var, max_var)
            
            # Generate random variation
            # Convert to float for random.uniform then back to Decimal safely
            min_var_float = float(min_var)
            max_var_float = float(max_var)
            variation = Decimal(str(random.uniform(min_var_float, max_var_float)))
            # Use market_price_dec (Decimal) instead of market_price (possibly float)
            price = market_price_dec + variation
            
            # Ensure price is positive and has reasonable minimum value
            price = max(price, Decimal('0.00000001'))
            
            # Normalize price
            price = self.normalize_price(price)
            
            # Calculate quantity
            min_order, max_order = self._get_order_limits()
            
            # Apply custom min/max if specified
            # Convert to Decimal if they are float
            min_trade_size = Decimal(str(self.min_trade_size)) if isinstance(self.min_trade_size, float) else self.min_trade_size
            max_trade_size = Decimal(str(self.max_trade_size)) if isinstance(self.max_trade_size, float) else self.max_trade_size
            
            if min_trade_size > Decimal('0'):
                min_order = max(min_order, min_trade_size)
            if max_trade_size > Decimal('0'):
                max_order = min(max_order, max_trade_size)
            
            # Ensure min doesn't exceed max
            min_order = min(min_order, max_order)
            
            # For retry attempts, increase the order size slightly to avoid minimum order issues
            if retry_count > 0:
                min_order = min_order * (Decimal('1') + Decimal('0.1') * Decimal(str(retry_count)))
                max_order = max_order * (Decimal('1') + Decimal('0.1') * Decimal(str(retry_count)))
            
            # Generate random quantity
            # Convert to float for random.uniform then back to Decimal safely
            # Ensure min_order and max_order are properly converted to float
            min_order_float = float(min_order)
            max_order_float = float(max_order)
            quantity = Decimal(str(random.uniform(min_order_float, max_order_float)))
            
            # Normalize quantity
            quantity = self.normalize_amount(quantity)
            
            # Format quantity with correct precision
            quantity_str = self._format_quantity(quantity, self.base_symbol)
            
            # Check account balances before placing order
            if not self._verify_sufficient_balance(self.primary_account, order_type, quantity, price):
                self.logger.warning(f"Insufficient balance for {self.primary_account} to place {order_type} order")
                # Try the opposite order type if balance is insufficient
                if retry_count < 1:
                    opposite_type = "sell" if order_type == "buy" else "buy"
                    self.logger.info(f"Trying opposite order type: {opposite_type}")
                    return self._place_new_order(opposite_type, retry_count + 1)
                return False
            
            # Log the order placement
            self.logger.info(
                f"Placing {order_type} order: "
                f"{quantity_str} {self.base_symbol} @ {price} {self.quote_symbol}"
            )
            
            # Place the order using the primary account
            result = self.dex.place_order(
                account=self.primary_account,
                order_type=order_type,
                quantity=quantity_str,
                price=str(price),
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            # Check result
            if isinstance(result, dict) and result.get("success") is False:
                error_msg = result.get("error", "Unknown error")
                self.logger.error(f"Failed to place {order_type} order: {error_msg}")
                
                # Handle specific error conditions
                if "insufficient balance" in str(error_msg).lower():
                    self.logger.warning(f"Insufficient balance detected for {self.primary_account}")
                    # Try the opposite order type if balance is insufficient
                    if retry_count < 1:
                        opposite_type = "sell" if order_type == "buy" else "buy"
                        self.logger.info(f"Trying opposite order type: {opposite_type}")
                        return self._place_new_order(opposite_type, retry_count + 1)
                    return False
                elif "minimum order" in str(error_msg).lower() and retry_count < 3:
                    # Wait briefly and retry with larger quantity
                    time.sleep(1)
                    self.logger.info(f"Order size too small, retrying with larger size (attempt {retry_count + 1}/3)")
                    return self._place_new_order(order_type, retry_count + 1)
                elif retry_count < 3:
                    # Wait briefly and retry with modified parameters
                    time.sleep(1)
                    self.logger.info(f"Retrying order placement (attempt {retry_count + 1}/3)")
                    return self._place_new_order(order_type, retry_count + 1)
                else:
                    self.logger.error(f"Max retries reached for {order_type} order")
                    return False
            elif result:
                self.logger.info(f"Successfully placed {order_type} order")
                return True
            else:
                self.logger.error(f"Failed to place {order_type} order with unknown error")
                return False
                
        except Exception as e:
            self.logger.error(f"Error placing new order: {e}")
            if retry_count < 3:
                time.sleep(1)
                self.logger.info(f"Retrying after error (attempt {retry_count + 1}/3)")
                return self._place_new_order(order_type, retry_count + 1)
            return False
    
    def simulate_trades(self) -> int:
        """Simulate trades by filling existing orders or creating new ones.
        
        Returns:
            int: Number of trades successfully executed
        """
        try:
            self.logger.info(f"Starting trade simulation cycle for {self.base_symbol}/{self.quote_symbol}")
            trades_executed = 0
            
            # Get current order book
            order_book = self._get_order_book()
            if not order_book or (not order_book.get("bids") and not order_book.get("offers")):
                self.logger.warning("Empty order book, will place new orders only")
                primary_orders = []
                secondary_orders = []
            else:
                # Get orders from primary account
                primary_orders = self._filter_orders_by_account(order_book, self.primary_account)
                self.logger.debug(f"Found {len(primary_orders)} orders from primary account {self.primary_account}")
                
                # Get orders from secondary account
                secondary_orders = self._filter_orders_by_account(order_book, self.secondary_account)
                self.logger.debug(f"Found {len(secondary_orders)} orders from secondary account {self.secondary_account}")
            
            # Select orders to fill
            orders_to_fill = []
            
            # If we have two different accounts, we can fill orders from either account
            if self.primary_account != self.secondary_account and (primary_orders or secondary_orders):
                # Select orders from both accounts to fill
                primary_to_fill = self._select_orders_to_fill(primary_orders)
                secondary_to_fill = self._select_orders_to_fill(secondary_orders)
                
                # Combine and limit to trades_per_cycle
                orders_to_fill = (primary_to_fill + secondary_to_fill)[:self.trades_per_cycle]
                self.logger.info(f"Selected {len(orders_to_fill)} orders to fill from existing orders")
            else:
                if self.primary_account == self.secondary_account:
                    self.logger.info("Using same account for both sides, will place new orders")
                else:
                    self.logger.info("No existing orders to fill, will place new orders")
                orders_to_fill = []
            
            # Fill selected orders with retry mechanism
            filled_orders = 0
            for order in orders_to_fill:
                order_id = order.get("identifier", "unknown")
                order_type = order.get("order_type", "unknown")
                price = order.get("price", "0")
                quantity = order.get("quantity", "0")
                
                self.logger.info(f"Attempting to fill {order_type} order {order_id}: {quantity} @ {price}")
                
                if self._fill_order(order):
                    filled_orders += 1
                    trades_executed += 1
                    self.logger.info(f"Successfully filled order {order_id} ({filled_orders}/{len(orders_to_fill)})")
                else:
                    self.logger.warning(f"Failed to fill order {order_id}")
            
            # If we didn't fill enough orders, place new ones
            remaining_trades = self.trades_per_cycle - trades_executed
            
            if remaining_trades > 0:
                self.logger.info(f"Placing {remaining_trades} new orders to meet target of {self.trades_per_cycle} trades")
                new_orders_placed = 0
                
                # Try to place new orders with alternating buy/sell types
                for i in range(remaining_trades):
                    # Alternate between buy and sell orders
                    order_type = 'buy' if i % 2 == 0 else 'sell'
                    
                    self.logger.info(f"Placing new {order_type} order ({i+1}/{remaining_trades})")
                    if self._place_new_order(order_type):
                        new_orders_placed += 1
                        trades_executed += 1
                        self.logger.info(f"Successfully placed {order_type} order ({new_orders_placed}/{remaining_trades})")
                    else:
                        self.logger.warning(f"Failed to place {order_type} order")
                        # Try the opposite order type if this one failed
                        opposite_type = 'sell' if order_type == 'buy' else 'buy'
                        self.logger.info(f"Trying opposite order type: {opposite_type}")
                        
                        if self._place_new_order(opposite_type):
                            new_orders_placed += 1
                            trades_executed += 1
                            self.logger.info(f"Successfully placed {opposite_type} order as fallback")
            
            # Log summary of trade simulation cycle
            self.logger.info(f"Trade simulation cycle complete: {trades_executed}/{self.trades_per_cycle} trades executed")
            if trades_executed < self.trades_per_cycle:
                self.logger.warning(f"Failed to execute {self.trades_per_cycle - trades_executed} planned trades")
            
            return trades_executed
            
        except Exception as e:
            self.logger.error(f"Error simulating trades: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return 0
    
    def generate_signal(self) -> Dict[str, Any]:
        """Generate trading signal (not used in this strategy)."""
        # This strategy doesn't use traditional signals
        return {
            "action": "simulate_trades",
            "trades_per_cycle": self.trades_per_cycle
        }
    
    def place_orders(self, signal: Dict[str, Any]) -> bool:
        """Place orders based on the generated signal."""
        # This method is required by BaseStrategy but we use simulate_trades instead
        return False
    
    def run(self):
        """Main strategy execution loop."""
        self.running = True
        self.logger.info(f"Starting {self.__class__.__name__} for {self.base_symbol}/{self.quote_symbol}")
        
        try:
            while self.running:
                # Simulate trades
                trades_executed = self.simulate_trades()
                self.logger.info(f"Executed {trades_executed} trades this cycle")
                
                # Wait for next cycle
                time.sleep(self.cycle_interval_ms / 1000)
                
        except KeyboardInterrupt:
            self.logger.info("Strategy stopped by user")
        except Exception as e:
            self.logger.error(f"Strategy error: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up any open orders when the strategy stops."""
        try:
            self.logger.info(f"Cleaning up strategy for {self.primary_account}...")
            
            # Cancel all orders for the primary account
            result = self.dex.cancel_all_orders(
                self.primary_account,
                self.quote_symbol,
                self.base_symbol
            )
            
            if result.get("success"):
                self.logger.info(f"Successfully cancelled all orders for {self.primary_account}")
            else:
                self.logger.error(f"Failed to cancel orders for {self.primary_account}: {result.get('error')}")
            
            # If using a different secondary account, cancel those orders too
            if self.primary_account != self.secondary_account:
                result = self.dex.cancel_all_orders(
                    self.secondary_account,
                    self.quote_symbol,
                    self.base_symbol
                )
                
                if result.get("success"):
                    self.logger.info(f"Successfully cancelled all orders for {self.secondary_account}")
                else:
                    self.logger.error(f"Failed to cancel orders for {self.secondary_account}: {result.get('error')}")
                
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
        finally:
            self.running = False 