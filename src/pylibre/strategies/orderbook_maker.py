from typing import Dict, Any, Tuple
from decimal import Decimal, ROUND_DOWN
import random
import time
from pylibre.strategies.templates.base_strategy import BaseStrategy
from pylibre.utils.shared_data import read_price

class OrderBookMakerStrategy(BaseStrategy):
    """Strategy responsible for maintaining the order book depth."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.orderbook_filled = False
        self.initial_orders_per_side = 15  # Initial fill amount
        self.min_orders_per_side = 11      # Minimum maintenance threshold
        
        # Log the parameters at initialization
        self.logger.info(
            f"Strategy parameters: {self.parameters}\n"
            f"Initial orders per side: {self.initial_orders_per_side}\n"
            f"Minimum orders per side: {self.min_orders_per_side}"
        )
    
    def get_orderbook_status(self) -> Tuple[int, int]:
        """Get number of our orders on each side of the book."""
        try:
            order_book = self.dex.fetch_order_book(
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            our_bids = len([order for order in order_book["bids"] 
                          if order["account"] == self.account])
            our_asks = len([order for order in order_book["offers"] 
                          if order["account"] == self.account])
            
            self.logger.info(f"Current orders - Bids: {our_bids}, Asks: {our_asks}")
            return our_bids, our_asks
            
        except Exception as e:
            self.logger.error(f"Error checking orderbook status: {e}")
            return 0, 0

    def place_orders(self, signal: Dict[str, Any]) -> bool:
        """Place orders using distributed order placement."""
        if signal is None:
            return False
        
        # Check current order book status
        our_bids, our_asks = self.get_orderbook_status()
        total_orders = our_bids + our_asks
        
        # If we have too few orders, reset the order book
        if total_orders < (self.min_orders_per_side * 2):
            self.logger.warning(
                f"Order count too low (total: {total_orders}). "
                f"Resetting order book..."
            )
            # Cancel all existing orders
            self.cancel_orders()
            time.sleep(1)  # Wait for cancellations to process
            
            # Reset orderbook_filled flag to trigger complete refill
            self.orderbook_filled = False
        
        if not self.orderbook_filled:
            # Initial filling of the order book with interleaved buy/sell orders
            success = self.fill_orderbook_gradually(
                base_price=signal['price'],
                min_spread=signal['min_spread'],
                max_spread=signal['max_spread']
            )
            if success:
                self.orderbook_filled = True
                self.logger.info("📚 Order book initially filled")
            return success
        else:
            # Maintain order book with more frequent random changes
            return self.maintain_orderbook(signal)

    def fill_orderbook_gradually(self, base_price: Decimal, min_spread: Decimal, max_spread: Decimal) -> bool:
        """Fill order book gradually, starting from the middle and working outwards."""
        try:
            min_order, max_order = self._get_order_limits()
            total_orders = self.initial_orders_per_side * 2  # 15 on each side
            
            self.logger.info(f"Using spreads: min={min_spread*100}%, max={max_spread*100}%")
            self.logger.info(f"Placing {total_orders} orders between {min_order} and {max_order} LIBRE")
            
            # Calculate price step to ensure unique prices
            spread_range = max_spread - min_spread
            spread_step = spread_range / Decimal('14')  # 14 steps between min and max for 15 orders
            
            # Place 15 buy orders from max_spread to min_spread below market
            placed_prices = set()  # Track prices to avoid duplicates
            for i in range(self.initial_orders_per_side):
                # Calculate exact spread for this step
                spread = max_spread - (spread_step * i)
                price = (base_price * (Decimal('1') - spread)).quantize(Decimal('0.0000000001'))
                
                # Skip if price already used
                if price in placed_prices:
                    self.logger.warning(f"Skipping duplicate price {price}")
                    continue
                    
                placed_prices.add(price)
                
                # Random quantity between min and max order size
                quantity = Decimal(str(random.uniform(
                    float(min_order),
                    float(max_order)
                ))).quantize(Decimal('0.0001'))
                
                success = self._place_single_order("buy", f"{quantity:.4f}", price, i)
                if not success:
                    return False
                time.sleep(random.uniform(0.3, 0.7))
                
            # Place 15 sell orders from min_spread to max_spread above market
            placed_prices.clear()
            for i in range(self.initial_orders_per_side):
                spread = min_spread + (spread_step * i)
                price = (base_price * (Decimal('1') + spread)).quantize(Decimal('0.0000000001'))
                
                if price in placed_prices:
                    self.logger.warning(f"Skipping duplicate price {price}")
                    continue
                    
                placed_prices.add(price)
                
                quantity = Decimal(str(random.uniform(
                    float(min_order),
                    float(max_order)
                ))).quantize(Decimal('0.0001'))
                
                success = self._place_single_order("sell", f"{quantity:.4f}", price, i)
                if not success:
                    return False
                time.sleep(random.uniform(0.3, 0.7))
                
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error filling order book: {e}")
            return False

    def maintain_orderbook(self, signal: Dict[str, Any]) -> bool:
        """Randomly cancel and replace orders throughout the order book."""
        try:
            # Check current order book status
            our_bids, our_asks = self.get_orderbook_status()
            total_orders = our_bids + our_asks
            
            # If we have too few orders, let place_orders handle the reset
            if total_orders < (self.min_orders_per_side * 2):
                self.orderbook_filled = False
                return True
            
            # Continue with normal maintenance if we have enough orders
            min_order, max_order = self._get_order_limits()
            total_balance = self._get_available_balance()
            
            # Calculate base quantity per order
            per_order_quantity = max(
                min_order,
                (total_balance / Decimal('20')).quantize(
                    Decimal('0.00000001'), rounding=ROUND_DOWN
                )
            )
            
            # Cancel fewer orders during maintenance
            num_to_cancel = random.randint(1, 3)  # Reduced from 3-6 to 1-3
            
            order_book = self.dex.fetch_order_book(
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            our_orders = (
                [order for order in order_book["bids"] if order["account"] == self.account] +
                [order for order in order_book["offers"] if order["account"] == self.account]
            )
            
            if our_orders:
                orders_to_cancel = random.sample(our_orders, min(num_to_cancel, len(our_orders)))
                
                for order in orders_to_cancel:
                    self.dex.cancel_order(
                        account=self.account,
                        order_id=order['identifier'],
                        quote_symbol=self.quote_symbol,
                        base_symbol=self.base_symbol
                    )
                    self.logger.info(f"🗑️  Cancelled order at price {order['price']}")
                    time.sleep(random.uniform(0.2, 0.4))
                
                # Place replacement orders
                for _ in range(len(orders_to_cancel)):
                    spread = Decimal(str(random.uniform(
                        float(signal['min_spread']),
                        float(signal['max_spread'])
                    )))
                    
                    order_type = random.choice(['buy', 'sell'])
                    direction = Decimal('-1') if order_type == 'buy' else Decimal('1')
                    
                    price = signal['price'] * (Decimal('1') + (direction * spread))
                    
                    # Calculate quantity with small random variation but never below minimum
                    quantity = per_order_quantity * Decimal(str(random.uniform(0.95, 1.05)))
                    quantity = max(min_order, min(max_order, quantity))
                    quantity_str = f"{quantity:.8f}"
                    
                    success = self._place_single_order(order_type, quantity_str, price, 0)
                    if success:
                        self.logger.info(f"📝 Placed new {order_type} order at {price:.8f}")
                    
                    time.sleep(random.uniform(0.2, 0.4))
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error maintaining order book: {e}")
            return False