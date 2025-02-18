from .templates.base_strategy import BaseStrategy
from decimal import Decimal
import time
import random
import threading
from typing import Dict, Any, Optional, List, Tuple
from pylibre.utils.logger import StrategyLogger, LogLevel

class OrderBookAnimatorStrategy(BaseStrategy):
    """
    Creates the appearance of market activity by periodically canceling
    and replacing orders with slight variations.
    """
    
    def __init__(self, client, account, base_symbol, quote_symbol, parameters, logger=None):
        """Initialize the strategy with parameters."""
        super().__init__(client, account, base_symbol, quote_symbol, parameters, logger)
        
        # Strategy parameters
        self.activity_level = parameters.get('activity_level', 'medium')
        self.orders_per_cycle = parameters.get('orders_per_cycle', 3)
        self.cycle_interval_ms = parameters.get('cycle_interval_ms', 5000)  # 5 seconds default
        self.price_variation_percentage = parameters.get('price_variation_percentage', None)
        self.quantity_variation_percentage = parameters.get('quantity_variation_percentage', None)
        
        # Activity level determines the intensity of changes if not explicitly set
        self.activity_factors = {
            'low': {'price': '0.001', 'quantity': '0.05'},    # 0.1% price, 5% quantity
            'medium': {'price': '0.003', 'quantity': '0.10'}, # 0.3% price, 10% quantity
            'high': {'price': '0.005', 'quantity': '0.15'}    # 0.5% price, 15% quantity
        }
        
        # Set price and quantity variation based on activity level if not explicitly provided
        if self.price_variation_percentage is None:
            self.price_variation_percentage = Decimal(self.activity_factors[self.activity_level]['price'])
        else:
            self.price_variation_percentage = Decimal(str(self.price_variation_percentage))
            
        if self.quantity_variation_percentage is None:
            self.quantity_variation_percentage = Decimal(self.activity_factors[self.activity_level]['quantity'])
        else:
            self.quantity_variation_percentage = Decimal(str(self.quantity_variation_percentage))
        
        # Log initialization
        self.logger.info(f"Initialized OrderBookAnimatorStrategy with:")
        self.logger.info(f"  Account: {account}")
        self.logger.info(f"  Trading pair: {base_symbol}/{quote_symbol}")
        self.logger.info(f"  Activity level: {self.activity_level}")
        self.logger.info(f"  Orders per cycle: {self.orders_per_cycle}")
        self.logger.info(f"  Cycle interval: {self.cycle_interval_ms}ms")
        self.logger.info(f"  Price variation: {float(self.price_variation_percentage)*100}%")
        self.logger.info(f"  Quantity variation: {float(self.quantity_variation_percentage)*100}%")
        
    def _filter_our_orders(self, order_book: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Filter orders belonging to our account."""
        our_orders = []
        
        # Filter bids (buy orders)
        for bid in order_book.get("bids", []):
            if bid.get("account") == self.account:
                bid["order_type"] = "buy"
                our_orders.append(bid)
        
        # Filter offers (sell orders)
        for offer in order_book.get("offers", []):
            if offer.get("account") == self.account:
                offer["order_type"] = "sell"
                our_orders.append(offer)
                
        return our_orders
        
    def _select_orders_to_animate(self, our_orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Select orders to cancel and replace based on activity pattern."""
        if not our_orders:
            return []
            
        # Determine how many orders to select
        num_to_select = min(self.orders_per_cycle, len(our_orders))
        
        # Prioritize orders near the center price
        # This creates more activity where it's most visible
        
        # Sort orders by price (ascending for buy, descending for sell)
        buy_orders = sorted(
            [order for order in our_orders if order.get("order_type") == "buy"],
            key=lambda x: Decimal(x.get("price", "0")),
            reverse=True  # Highest buy prices first
        )
        
        sell_orders = sorted(
            [order for order in our_orders if order.get("order_type") == "sell"],
            key=lambda x: Decimal(x.get("price", "0"))
            # Lowest sell prices first
        )
        
        # Select orders from both sides if possible
        selected_orders = []
        
        # Try to select evenly from both sides
        buy_to_select = num_to_select // 2
        sell_to_select = num_to_select - buy_to_select
        
        # Adjust if one side doesn't have enough orders
        if len(buy_orders) < buy_to_select:
            sell_to_select += buy_to_select - len(buy_orders)
            buy_to_select = len(buy_orders)
            
        if len(sell_orders) < sell_to_select:
            buy_to_select += sell_to_select - len(sell_orders)
            sell_to_select = len(sell_orders)
            
        # Select orders from each side
        if buy_to_select > 0:
            selected_orders.extend(buy_orders[:buy_to_select])
            
        if sell_to_select > 0:
            selected_orders.extend(sell_orders[:sell_to_select])
            
        # If we still need more orders, add random ones
        remaining = num_to_select - len(selected_orders)
        if remaining > 0 and our_orders:
            remaining_orders = [order for order in our_orders if order not in selected_orders]
            if remaining_orders:
                selected_orders.extend(random.sample(remaining_orders, min(remaining, len(remaining_orders))))
                
        return selected_orders
        
    def _parse_asset_string(self, asset_string: str) -> Tuple[Decimal, str]:
        """Parse an asset string like '100.0000 LIBRE' into (100.0000, 'LIBRE')."""
        parts = asset_string.split()
        if len(parts) == 2:
            return Decimal(parts[0]), parts[1]
        return Decimal('0'), ""
        
    def _create_replacement_order(self, order: Dict[str, Any]) -> bool:
        """Create a replacement order with slight variation."""
        try:
            order_type = order.get("order_type")
            if not order_type:
                self.logger.error(f"Order type not found in order: {order}")
                return False
                
            # Parse the base and quote assets
            base_amount, base_symbol = self._parse_asset_string(order.get("baseAsset", "0 " + self.base_symbol))
            quote_amount, quote_symbol = self._parse_asset_string(order.get("quoteAsset", "0 " + self.quote_symbol))
            
            # Get the original price
            original_price = Decimal(order.get("price", "0"))
            
            # Calculate new price with variation
            price_variation = original_price * self.price_variation_percentage
            # Random variation between -variation and +variation
            price_delta = Decimal(str(random.uniform(-float(price_variation), float(price_variation))))
            new_price = original_price + price_delta
            
            # Ensure price is positive
            new_price = max(new_price, Decimal('0.00000001'))
            
            # Set minimum quantities based on the trading pair
            min_base_amount = Decimal('100.0000') if self.base_symbol == 'LIBRE' else Decimal('0.0001')
            
            # Calculate new quantity with variation
            if order_type == "buy":
                # For buy orders, we're buying base with quote
                # Keep the quote amount constant and vary the base amount
                
                # If base_amount is 0 or very small, use the minimum amount
                if base_amount < min_base_amount:
                    new_base_amount = min_base_amount
                else:
                    quantity_variation = base_amount * self.quantity_variation_percentage
                    quantity_delta = Decimal(str(random.uniform(-float(quantity_variation), float(quantity_variation))))
                    new_base_amount = base_amount + quantity_delta
                
                # Ensure quantity is positive and meets minimum requirements
                new_base_amount = max(new_base_amount, min_base_amount)
                
                # Format quantity for the order
                quantity_str = self._format_quantity(new_base_amount, self.base_symbol)
                
            else:  # sell order
                # For sell orders, we're selling base for quote
                
                # If base_amount is 0 or very small, use the minimum amount
                if base_amount < min_base_amount:
                    new_base_amount = min_base_amount
                else:
                    quantity_variation = base_amount * self.quantity_variation_percentage
                    quantity_delta = Decimal(str(random.uniform(-float(quantity_variation), float(quantity_variation))))
                    new_base_amount = base_amount + quantity_delta
                
                # Ensure quantity is positive and meets minimum requirements
                new_base_amount = max(new_base_amount, min_base_amount)
                
                # Format quantity for the order
                quantity_str = self._format_quantity(new_base_amount, self.base_symbol)
            
            # Format price with 10 decimal places for BTC
            if self.quote_symbol == 'BTC':
                price_str = f"{new_price:.10f}"
            else:
                price_str = f"{new_price:.8f}"
                
            # Place the new order
            result = self.dex.place_order(
                account=self.account,
                order_type=order_type,
                quantity=quantity_str,
                price=price_str,
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            # Handle both dictionary and string responses
            if isinstance(result, dict) and result.get("success"):
                self.logger.info(f"Replaced {order_type} order: {quantity_str} {self.base_symbol} at {price_str} {self.quote_symbol}")
                return True
            elif isinstance(result, str):  # Transaction ID as string indicates success
                self.logger.info(f"Replaced {order_type} order: {quantity_str} {self.base_symbol} at {price_str} {self.quote_symbol}")
                return True
            else:
                error = result.get('error', 'Unknown error') if isinstance(result, dict) else "Unknown error"
                self.logger.error(f"Failed to replace {order_type} order: {error}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error creating replacement order: {e}")
            return False
            
    def animate_orderbook(self):
        """Create movement in the orderbook."""
        try:
            # 1. Fetch current orderbook
            order_book = self.dex.fetch_order_book(
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            # 2. Filter orders belonging to our account
            our_orders = self._filter_our_orders(order_book)
            
            if not our_orders:
                self.logger.info(f"No orders found for account {self.account}")
                return
                
            # 3. Select orders to cancel based on activity pattern
            orders_to_cancel = self._select_orders_to_animate(our_orders)
            
            if not orders_to_cancel:
                self.logger.info(f"No orders selected for animation")
                return
                
            self.logger.info(f"Selected {len(orders_to_cancel)} orders for animation")
            
            # 4. Cancel selected orders
            for order in orders_to_cancel:
                try:
                    self.dex.cancel_order(
                        account=self.account,
                        order_id=order['identifier'],
                        quote_symbol=self.quote_symbol,
                        base_symbol=self.base_symbol
                    )
                    
                    self.logger.info(f"Cancelled {order.get('order_type')} order at price {order.get('price')}")
                    
                    # 5. Create replacement order with slight variation
                    # Add a small delay to avoid rate limiting and make it look more natural
                    time.sleep(0.5)
                    self._create_replacement_order(order)
                    
                except Exception as e:
                    self.logger.error(f"Error cancelling order {order.get('identifier')}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error animating orderbook: {e}")
            
    def run(self):
        """Main execution loop."""
        self.running = True
        self.logger.info(f"Starting OrderBookAnimatorStrategy for {self.base_symbol}/{self.quote_symbol}")
        
        last_cycle_time = 0
        
        try:
            while self.running:
                current_time = time.time() * 1000
                
                # Check if it's time for a new cycle
                if current_time - last_cycle_time >= self.cycle_interval_ms:
                    self.animate_orderbook()
                    last_cycle_time = current_time
                    
                # Sleep to prevent CPU hogging
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            self.logger.info("Strategy stopped by user")
        except Exception as e:
            self.logger.error(f"Strategy error: {e}")
        finally:
            self.cleanup()
            
    def cleanup(self):
        """Clean up resources."""
        self.logger.info("Cleaning up OrderBookAnimatorStrategy")
        self.running = False

    def place_orders(self, signal: Dict[str, Any]) -> bool:
        """
        Implementation of the abstract method from BaseStrategy.
        
        The OrderBookAnimatorStrategy doesn't place orders directly through this method.
        Instead, it uses the animate_orderbook method to cancel and replace orders.
        
        Args:
            signal: The trading signal (not used in this strategy)
            
        Returns:
            bool: Always returns True as this method is not the primary way this strategy places orders
        """
        self.logger.debug("OrderBookAnimatorStrategy doesn't place orders through the place_orders method")
        return True 